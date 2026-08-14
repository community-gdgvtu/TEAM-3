"""Static traffic assignment via Method of Successive Averages (SPEC §7.7).

Given a peak-hour origin→destination vehicle-demand table and a
:class:`~app.spatial.network.Network`, this loads the demand onto the network and
solves for an approximate static **user equilibrium** — the state where drivers
have re-routed until no one can find a faster path — using MSA over all-or-nothing
assignments with a BPR volume-delay function.

MSA is a classic, provably-convergent averaging scheme:

    x_k = x_{k-1} + (1/k) · (y_k − x_{k-1})

where ``y_k`` is the all-or-nothing loading on shortest paths computed from the
congested times implied by ``x_{k-1}``. It is fully deterministic (SPEC §34): the
same demand + network + parameters give identical link flows every run.
"""

from __future__ import annotations

from dataclasses import dataclass

from .network import Network
from .params import DEFAULT_SPATIAL_PARAMS, SpatialParams


@dataclass
class AssignmentResult:
    """Equilibrium link flows + derived congested times/speeds."""

    #: veh/hr on each arc (aligned with ``network.arcs``).
    flow: list[float]
    #: congested travel time (minutes) on each arc at equilibrium.
    time_min: list[float]
    #: volume/capacity ratio on each arc.
    vc: list[float]
    #: congested speed (km/h) on each arc.
    speed_kmh: list[float]
    #: least congested travel time from every origin to every node (minutes).
    #: Keyed origin -> {node -> minutes}. Used for accessibility (SPEC §7.7).
    skims: dict[str, dict[str, float]]
    iterations: int


def _all_or_nothing(
    net: Network,
    demand: dict[tuple[str, str], float],
    arc_times: list[float],
    origins: list[str],
) -> tuple[list[float], dict[str, dict[str, float]]]:
    """Load all demand onto current shortest paths; also return origin skims."""
    y = [0.0] * len(net.arcs)
    skims: dict[str, dict[str, float]] = {}
    # Group destinations by origin so we run one Dijkstra per origin.
    dests_by_origin: dict[str, list[str]] = {}
    for (o, d), _ in demand.items():
        dests_by_origin.setdefault(o, []).append(d)
    for o in origins:
        dist, pred_arc = net.shortest_paths(o, arc_times)
        skims[o] = dist
        for d in dests_by_origin.get(o, ()):
            vol = demand[(o, d)]
            if vol <= 0.0:
                continue
            # Walk back along predecessor arcs, loading the trip volume.
            node = d
            while node != o and node in pred_arc:
                ai = pred_arc[node]
                y[ai] += vol
                node = net.arcs[ai].u
    return y, skims


def assign(
    net: Network,
    demand: dict[tuple[str, str], float],
    params: SpatialParams = DEFAULT_SPATIAL_PARAMS,
) -> AssignmentResult:
    """Solve an approximate static user equilibrium by MSA (SPEC §7.7)."""
    n = len(net.arcs)
    flow = [0.0] * n
    # Free-flow times seed the first shortest-path computation.
    times = [net.arcs[i].t0_min for i in range(n)]
    origins = sorted({o for (o, _d) in demand})
    skims: dict[str, dict[str, float]] = {}

    iters = max(1, params.assignment_iterations)
    for k in range(1, iters + 1):
        y, skims = _all_or_nothing(net, demand, times, origins)
        step = 1.0 / k
        for i in range(n):
            flow[i] += step * (y[i] - flow[i])
            times[i] = net.bpr_time(net.arcs[i], flow[i], params.bpr_alpha, params.bpr_beta)

    vc = [flow[i] / max(1.0, net.arcs[i].capacity_veh_per_hr) for i in range(n)]
    speed = [
        (net.arcs[i].length_km / (times[i] / 60.0)) if times[i] > 0 else net.arcs[i].free_flow_speed_kmh
        for i in range(n)
    ]
    return AssignmentResult(
        flow=flow, time_min=times, vc=vc, speed_kmh=speed, skims=skims, iterations=iters
    )
