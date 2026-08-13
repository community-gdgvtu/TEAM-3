"""Directed road-network graph + shortest paths for the spatial layer (SPEC §7.7).

Builds a directed graph from the shared ``data/city/roads.geojson`` network (an
undirected grid of links, each carrying a per-direction capacity, free-flow speed
and length) and provides the primitives the traffic-assignment engine needs:

* a BPR (Bureau of Public Roads) volume-delay function, and
* a Dijkstra shortest-path tree by current (congested) arc time.

Every undirected road link becomes **two** directed arcs (one per direction), each
inheriting the link's per-direction ``capacity_veh_per_hr``. Nothing here is an
LLM output; the graph is a deterministic read of the dataset (SPEC §34).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from .. import dataset


@dataclass
class Arc:
    """One directed road arc (a single travel direction of a road link)."""

    arc_id: str
    link_id: str
    u: str  # from zone
    v: str  # to zone
    length_km: float
    capacity_veh_per_hr: float
    free_flow_speed_kmh: float
    road_class: str
    crosses_cordon: bool
    interior_cbd: bool
    #: Free-flow travel time (minutes) — the uncongested lower bound.
    t0_min: float = 0.0

    def __post_init__(self) -> None:
        speed = max(1.0, self.free_flow_speed_kmh)
        self.t0_min = self.length_km / speed * 60.0


@dataclass
class Network:
    """Directed graph over city zones with per-arc capacity + free-flow time."""

    arcs: list[Arc]
    #: node -> list of outgoing arc indices
    out_arcs: dict[str, list[int]] = field(default_factory=dict)
    nodes: list[str] = field(default_factory=list)

    @classmethod
    def from_dataset(cls) -> "Network":
        """Build the directed grid network from ``roads.geojson``."""
        roads = dataset.load_roads()["features"]
        arcs: list[Arc] = []
        for f in roads:
            p = f["properties"]
            base = dict(
                link_id=p["link_id"],
                length_km=float(p["length_km"]),
                capacity_veh_per_hr=float(p["capacity_veh_per_hr"]),
                free_flow_speed_kmh=float(p["free_flow_speed_kmh"]),
                road_class=p.get("road_class", "local"),
                crosses_cordon=bool(p.get("crosses_cordon", False)),
                interior_cbd=bool(p.get("interior_cbd", False)),
            )
            # Two directed arcs per undirected link (grid roads are bidirectional).
            arcs.append(Arc(arc_id=f"{p['link_id']}+", u=p["from_zone"], v=p["to_zone"], **base))
            arcs.append(Arc(arc_id=f"{p['link_id']}-", u=p["to_zone"], v=p["from_zone"], **base))

        out_arcs: dict[str, list[int]] = {}
        node_set: set[str] = set()
        for i, a in enumerate(arcs):
            out_arcs.setdefault(a.u, []).append(i)
            out_arcs.setdefault(a.v, [])  # ensure sink appears as a node
            node_set.update((a.u, a.v))
        return cls(arcs=arcs, out_arcs=out_arcs, nodes=sorted(node_set))

    def bpr_time(self, arc: Arc, volume: float, alpha: float, beta: float) -> float:
        """Congested travel time for ``arc`` at ``volume`` veh/hr (BPR)."""
        cap = max(1.0, arc.capacity_veh_per_hr)
        return arc.t0_min * (1.0 + alpha * (volume / cap) ** beta)

    def shortest_paths(
        self, origin: str, arc_times: list[float]
    ) -> tuple[dict[str, float], dict[str, int]]:
        """Dijkstra from ``origin`` over ``arc_times``.

        Returns ``(dist, pred_arc)`` where ``dist[node]`` is the least travel time
        (minutes) and ``pred_arc[node]`` is the index of the arc used to reach it
        (for path reconstruction / all-or-nothing loading).
        """
        dist: dict[str, float] = {origin: 0.0}
        pred_arc: dict[str, int] = {}
        pq: list[tuple[float, str]] = [(0.0, origin)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, float("inf")):
                continue
            for ai in self.out_arcs.get(u, ()):  # noqa: F841
                arc = self.arcs[ai]
                nd = d + arc_times[ai]
                if nd < dist.get(arc.v, float("inf")):
                    dist[arc.v] = nd
                    pred_arc[arc.v] = ai
                    heapq.heappush(pq, (nd, arc.v))
        return dist, pred_arc
