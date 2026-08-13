"""Build the abstract social graph and run opinion diffusion (SPEC §14).

Dynamics: **Friedkin–Johnsen** — each round every node moves toward a weighted
average of the nodes it listens to, but stays partially anchored to its own
round-0 conviction::

    x_i(t+1) = λ_i · Σ_j W_ij · x_j(t)  +  (1 − λ_i) · x_i(0)

``W`` is row-stochastic (each node's incoming weights sum to 1) and ``λ_i`` is the
node's susceptibility. The process is deterministic and convergent — no LLM, no
randomness (SPEC §34). Opinions are bipolar in ``[-1, +1]``.

Citizen round-0 opinions are seeded from the deterministic cohort-opinion model
(``compute_public_opinion``); institutional/actor priors are transparent,
documented constants derived from the policy's own structure (who proposes it,
who it costs, how the burden falls).
"""

from __future__ import annotations

from typing import Optional

from ..opinion.model import _LOW_BANDS, compute_public_opinion
from ..policy.dsl import PolicyDSL
from ..simulation.shocks import Shocks, apply_shocks
from .schema import (
    Coalition,
    DiffusionEdge,
    DiffusionNode,
    DiffusionResult,
    InfoShock,
    OpinionTrajectory,
)

# Income-band ordering (low → high) for the citizen-cohort nodes.
_BAND_ORDER = ["low", "lower-middle", "middle", "upper-middle", "upper"]

# Friedkin–Johnsen susceptibility (openness to persuasion) per node type.
_SUSCEPTIBILITY = {
    "cohort": 0.5,
    "journalist": 0.6,
    "influencer": 0.5,
    "community_group": 0.4,
    "business": 0.25,
    "politician": 0.15,  # entrenched — anchored to their launch stance
    "institution": 0.25,
}


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _band_tier(band: str) -> str:
    if band in _LOW_BANDS:
        return "low"
    if band in ("upper", "upper-middle"):
        return "high"
    return "mid"


def _citizen_nodes(policy: PolicyDSL, params) -> tuple[list[DiffusionNode], dict]:
    """Aggregate the cohort-opinion model into one node per income band."""
    op = compute_public_opinion(policy, params=params)
    agg: dict[str, dict] = {}
    for c in op.cohorts:
        a = agg.setdefault(c.income_band, {"w": 0.0, "size": 0})
        a["w"] += c.mean_support * c.size
        a["size"] += c.size
    nodes: list[DiffusionNode] = []
    for band in _BAND_ORDER:
        if band not in agg:
            continue
        a = agg[band]
        init = _clamp(a["w"] / max(1, a["size"]))
        nodes.append(
            DiffusionNode(
                id=f"citizen_{band.replace('-', '_')}",
                type="cohort",
                label=f"{band} income commuters",
                size=a["size"],
                susceptibility=_SUSCEPTIBILITY["cohort"],
                initial_opinion=round(init, 4),
                final_opinion=round(init, 4),
                opinion_prior_source="Cohort opinion model (size-weighted mean support).",
            )
        )
    return nodes, {"overall_net_support": op.overall.net_support}


def _actor_nodes(policy: PolicyDSL, citizens: list[DiffusionNode], overall_net: float) -> list[DiffusionNode]:
    """Institutional / media / influence actors with documented opinion priors."""
    # Citizen-population-weighted average opinion (for influencer / opposition priors).
    tot = sum(n.size for n in citizens) or 1
    cit_avg = sum(n.initial_opinion * n.size for n in citizens) / tot
    # Advocacy for the worst-off tracks the low-income bands' opinion.
    low = [n for n in citizens if n.id in ("citizen_low", "citizen_lower_middle")]
    low_avg = (
        sum(n.initial_opinion * n.size for n in low) / (sum(n.size for n in low) or 1)
        if low
        else cit_avg
    )

    def node(id_, type_, label, init, src):
        return DiffusionNode(
            id=id_,
            type=type_,
            label=label,
            size=0,
            susceptibility=_SUSCEPTIBILITY[type_],
            initial_opinion=round(_clamp(init), 4),
            final_opinion=round(_clamp(init), 4),
            opinion_prior_source=src,
        )

    return [
        node("government", "politician", "Government (proposer)", 0.7,
             "Prior: the proposing government backs its own policy (+0.7)."),
        node("opposition", "politician", "Opposition", -0.6,
             "Prior: opposition role stance (−0.6)."),
        node("business", "business", "Business / commerce lobby", -0.5,
             "Prior: a charge raises trip costs for drivers/customers (−0.5)."),
        node("journalists", "journalist", "Press / media", 0.0,
             "Prior: neutral framing at launch (0.0); moves with its sources."),
        node("influencers", "influencer", "Social-media influencers", cit_avg,
             "Prior: seeded at the citizen-average opinion; amplifies the loudest bloc."),
        node("community_groups", "community_group", "Community / equity groups", low_avg,
             "Prior: advocates track the lowest-income cohorts' opinion."),
        node("institutions", "institution", "Public institutions / experts", 0.3 * overall_net + 0.15,
             "Prior: evidence-led, mildly toward the net public balance."),
    ]


# Directed influence topology: for each target node, who it listens to and how
# (kind, base weight). "citizens" expands to every citizen node split by size.
# Weights are relative; each target row is normalised to sum to 1 (row-stochastic).
def _incoming_spec(node: DiffusionNode) -> dict:
    t = node.type
    if t == "cohort":
        tier = _band_tier(node.label.split()[0])
        spec = {
            "__self__": ("social_influence", 0.30),
            "journalists": ("media_exposure", 0.15),
            "influencers": ("social_influence", 0.15),
            "__other_citizens__": ("social_influence", 0.15),
            "government": ("political_affinity", 0.08),
            "opposition": ("political_affinity", 0.08),
        }
        if tier == "low":
            spec["community_groups"] = ("geography", 0.18)
            spec["opposition"] = ("political_affinity", 0.11)
        elif tier == "high":
            spec["business"] = ("workplace", 0.14)
            spec["government"] = ("political_affinity", 0.11)
        else:
            spec["community_groups"] = ("geography", 0.09)
        return spec
    if t == "journalist":
        return {
            "__self__": ("institutional", 0.10),
            "government": ("institutional", 0.25),
            "opposition": ("institutional", 0.25),
            "institutions": ("institutional", 0.20),
            "influencers": ("social_influence", 0.10),
            "__citizens__": ("social_influence", 0.10),
        }
    if t == "influencer":
        return {
            "__self__": ("social_influence", 0.20),
            "__citizens__": ("social_influence", 0.40),
            "journalists": ("media_exposure", 0.20),
            "opposition": ("political_affinity", 0.10),
            "government": ("political_affinity", 0.10),
        }
    if t == "community_group":
        return {
            "__self__": ("social_influence", 0.30),
            "__citizens_low__": ("geography", 0.40),
            "institutions": ("institutional", 0.20),
            "journalists": ("media_exposure", 0.10),
        }
    if t == "business":
        return {
            "__self__": ("workplace", 0.50),
            "government": ("institutional", 0.15),
            "institutions": ("institutional", 0.15),
            "journalists": ("media_exposure", 0.20),
        }
    if t == "politician":
        if node.id == "government":
            return {
                "__self__": ("political_affinity", 0.70),
                "institutions": ("institutional", 0.15),
                "journalists": ("media_exposure", 0.15),
            }
        return {  # opposition
            "__self__": ("political_affinity", 0.70),
            "__citizens__": ("social_influence", 0.15),
            "journalists": ("media_exposure", 0.15),
        }
    # institution
    return {
        "__self__": ("institutional", 0.50),
        "journalists": ("media_exposure", 0.20),
        "government": ("institutional", 0.15),
        "opposition": ("institutional", 0.15),
    }


def _build_matrix(nodes: list[DiffusionNode]) -> tuple[dict, list[DiffusionEdge]]:
    """Row-stochastic influence matrix W[target][source] + edge list for viz."""
    ids = [n.id for n in nodes]
    citizens = [n.id for n in nodes if n.type == "cohort"]
    citizen_size = {n.id: n.size for n in nodes if n.type == "cohort"}
    low_ids = [i for i in citizens if i in ("citizen_low", "citizen_lower_middle")]
    W: dict[str, dict[str, float]] = {}
    edges: list[DiffusionEdge] = []

    for node in nodes:
        spec = _incoming_spec(node)
        row: dict[str, tuple[str, float]] = {}  # source -> (kind, weight)

        def add(src: str, kind: str, w: float):
            if src not in row:
                row[src] = (kind, 0.0)
            row[src] = (kind, row[src][1] + w)

        for key, (kind, w) in spec.items():
            if key == "__self__":
                add(node.id, kind, w)
            elif key == "__citizens__":
                tot = sum(citizen_size[c] for c in citizens) or 1
                for c in citizens:
                    add(c, kind, w * citizen_size[c] / tot)
            elif key == "__citizens_low__":
                tot = sum(citizen_size[c] for c in low_ids) or 1
                for c in low_ids:
                    add(c, kind, w * citizen_size[c] / tot)
            elif key == "__other_citizens__":
                others = [c for c in citizens if c != node.id]
                tot = sum(citizen_size[c] for c in others) or 1
                for c in others:
                    add(c, kind, w * citizen_size[c] / tot)
            elif key in ids:
                add(key, kind, w)

        total = sum(w for _, w in row.values()) or 1.0
        W[node.id] = {src: w / total for src, (_, w) in row.items()}
        for src, (kind, w) in row.items():
            edges.append(
                DiffusionEdge(
                    source=src, target=node.id, weight=round(w / total, 4), kind=kind
                )
            )
    return W, edges


def _polarisation(opinions: list[float], sizes: list[float]) -> float:
    """Population-weighted opinion dispersion, normalised to [0,1] (max σ = 1)."""
    tot = sum(sizes) or 1.0
    mean = sum(o * s for o, s in zip(opinions, sizes)) / tot
    var = sum(s * (o - mean) ** 2 for o, s in zip(opinions, sizes)) / tot
    return round(min(1.0, var ** 0.5), 4)


def run_diffusion(
    policy: PolicyDSL,
    *,
    shocks: Optional[Shocks] = None,
    rounds: int = 12,
    info_shocks: Optional[list[InfoShock]] = None,
) -> DiffusionResult:
    """Run the opinion-diffusion process for a compiled policy (SPEC §14)."""
    rounds = max(1, min(60, rounds))
    params, _ = apply_shocks(shocks)

    citizens, meta = _citizen_nodes(policy, params)
    actors = _actor_nodes(policy, citizens, meta["overall_net_support"])
    nodes = citizens + actors
    node_by_id = {n.id: n for n in nodes}
    W, edges = _build_matrix(nodes)

    x0 = {n.id: n.initial_opinion for n in nodes}
    x = dict(x0)
    lam = {n.id: n.susceptibility for n in nodes}

    shock_by_round: dict[int, list[InfoShock]] = {}
    for s in info_shocks or []:
        shock_by_round.setdefault(s.round, []).append(s)

    traj = {n.id: [x[n.id]] for n in nodes}
    cit_ids = [n.id for n in citizens]
    cit_sizes = [node_by_id[i].size for i in cit_ids]

    def citizen_mean(state: dict) -> float:
        tot = sum(cit_sizes) or 1.0
        return sum(state[i] * node_by_id[i].size for i in cit_ids) / tot

    salience = [_engagement(x, cit_ids)]
    polar = [_polarisation([x[i] for i in cit_ids], cit_sizes)]

    # Apply a round-0 shock before the first update, if any.
    for s in shock_by_round.get(0, []):
        if s.node in x:
            x[s.node] = _clamp(x[s.node] + s.delta)
            x0_locked = x[s.node]  # a round-0 shock also moves the FJ anchor
            x0[s.node] = x0_locked
            traj[s.node][0] = x[s.node]

    for r in range(1, rounds + 1):
        nxt = {}
        for nid in x:
            agg = sum(W[nid].get(src, 0.0) * x[src] for src in W[nid])
            nxt[nid] = _clamp(lam[nid] * agg + (1.0 - lam[nid]) * x0[nid])
        # Information shocks landing this round: a narrative shock durably shifts
        # the actor's conviction, so it also moves the FJ anchor (x0) — otherwise
        # a one-round bump on a fast-reverting node simply washes out.
        for s in shock_by_round.get(r, []):
            if s.node in nxt:
                nxt[s.node] = _clamp(nxt[s.node] + s.delta)
                x0[s.node] = _clamp(x0[s.node] + s.delta)
        x = nxt
        for nid in x:
            traj[nid].append(round(x[nid], 4))
        salience.append(_engagement(x, cit_ids))
        polar.append(_polarisation([x[i] for i in cit_ids], cit_sizes))

    for n in nodes:
        n.final_opinion = round(x[n.id], 4)

    coalitions = _coalitions(nodes, x)
    init_net = round(citizen_mean(x0), 4)
    final_net = round(citizen_mean(x), 4)
    dominant = _dominant_narrative(final_net, polar[-1])

    return DiffusionResult(
        policy_id=policy.id,
        rounds=rounds,
        nodes=nodes,
        edges=edges,
        trajectories=[OpinionTrajectory(node_id=k, opinions=v) for k, v in traj.items()],
        salience=salience,
        polarisation=polar,
        coalitions=coalitions,
        initial_net_support=init_net,
        final_net_support=final_net,
        dominant_narrative=dominant,
        shocks_applied=info_shocks or [],
        assumptions={
            "dynamics": "Friedkin-Johnsen (row-stochastic influence, opinion anchoring)",
            "susceptibility_by_type": _SUSCEPTIBILITY,
            "opinion_scale": "[-1 strong oppose, +1 strong support]",
            "rounds_meaning": "information-diffusion rounds, not physical horizon",
            "coalition_threshold": 0.15,
        },
    )


def _engagement(x: dict, cit_ids: list[str]) -> float:
    """Salience proxy: mean absolute strength of feeling among citizens (0–1)."""
    if not cit_ids:
        return 0.0
    return round(sum(abs(x[i]) for i in cit_ids) / len(cit_ids), 4)


def _coalitions(nodes: list[DiffusionNode], x: dict) -> list[Coalition]:
    thr = 0.15
    cit_total = sum(n.size for n in nodes if n.type == "cohort") or 1
    buckets: dict[str, list[DiffusionNode]] = {"support": [], "oppose": [], "contested": []}
    for n in nodes:
        v = x[n.id]
        stance = "support" if v > thr else "oppose" if v < -thr else "contested"
        buckets[stance].append(n)
    out: list[Coalition] = []
    for stance in ("support", "oppose", "contested"):
        members = buckets[stance]
        if not members:
            continue
        share = sum(m.size for m in members) / cit_total
        wsum = sum(x[m.id] * max(m.size, 1) for m in members)
        wtot = sum(max(m.size, 1) for m in members)
        out.append(
            Coalition(
                stance=stance,
                members=[m.id for m in members],
                citizen_share=round(share, 4),
                mean_opinion=round(wsum / wtot, 4),
            )
        )
    return out


def _dominant_narrative(final_net: float, final_polar: float) -> str:
    thr = 0.05
    if final_net > thr:
        frame = "the pro-policy framing prevails among citizens"
    elif final_net < -thr:
        frame = "the opposition framing prevails among citizens"
    else:
        frame = "no framing dominates — citizens remain split"
    if final_polar >= 0.4:
        frame += " (highly polarised)"
    elif final_polar >= 0.2:
        frame += " (moderately polarised)"
    else:
        frame += " (broad consensus)"
    return frame
