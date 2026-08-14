"""Transparent firm-translation assumptions for the Business View (SPEC §17).

These are the documented coefficients that turn a firm's *physical* attributes
(floor area, allocated jobs) and the *Simulated* mode-shift / charge quantities
into a firm-level footfall / deliveries / cost / revenue-proxy picture. They are
few, auditable and never LLM-tuned (SPEC §34); because they are approximate
behavioural / input-output ratios layered on the Simulated core, every monetary
or footfall figure they produce is tagged **Estimated** (SPEC §8), not Simulated.

The Business View reuses the economic layer's coefficients where they already
exist (:mod:`app.economy.params`) — footfall spend, freight share, avoidance
fraction, pedestrianisation uplift — so the micro firm view can never disagree
with the aggregate ``/economy`` numbers beside it. Only the strictly firm-level
allocation coefficients (customer multiplier per sector, deliveries per unit
floor area, storey height) live here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BusinessParams:
    """Firm-level allocation / translation assumptions (SPEC §17 Business View)."""

    #: Nominal storey height (m) used to turn a building footprint + height into
    #: gross floor area (footprint × floors). Only affects the *relative* jobs /
    #: floor-space allocation across firms in a zone, so the absolute value is a
    #: weak assumption.
    storey_height_m: float = 3.5

    #: Daily customer/visitor footfall generated per worker, by sector. Retail and
    #: hospitality draw many outside visitors per employee; offices draw few;
    #: industrial/logistics essentially none. Documented Estimated ratios — no
    #: shopper agents exist in the synthetic population (SPEC §6/§34).
    customer_per_worker: tuple[tuple[str, float], ...] = (
        ("retail & hospitality", 6.0),
        ("retail / commercial podium", 4.0),
        ("mixed-use commercial", 3.0),
        ("office / professional services", 0.6),
        ("industrial / logistics", 0.1),
    )

    #: Share of a firm's customers who arrive by private car into the central
    #: district (only these are exposed to a cordon charge / ban). Estimated.
    customer_car_share_cbd: float = 0.35
    customer_car_share_outer: float = 0.55

    #: Daily delivery/freight vehicle trips generated per 1,000 m² of gross floor
    #: area, by sector. Retail and logistics are delivery-intensive; offices much
    #: less so. Estimated input-output ratios (freight is not agent-modelled).
    deliveries_per_1000sqm: tuple[tuple[str, float], ...] = (
        ("retail & hospitality", 3.5),
        ("retail / commercial podium", 3.0),
        ("mixed-use commercial", 2.0),
        ("industrial / logistics", 4.0),
        ("office / professional services", 0.8),
    )

    #: Average customer spend per visit (currency units) — the revenue-proxy
    #: scaling. A deliberately coarse Estimated figure; the revenue *proxy* is only
    #: meaningful as a before/after ratio, never as an absolute turnover claim.
    spend_per_customer_visit: float = 18.0
    spend_per_customer_visit_range: tuple[float, float] = (10.0, 30.0)

    #: Share of a per-vehicle cordon delivery charge passed through as a real firm
    #: operating cost (mirrors the economy layer's freight pass-through so the two
    #: layers agree). Estimated.
    delivery_cost_pass_through: float = 0.70

    #: Relative net-revenue-proxy drop (vs baseline) beyond which the firm is
    #: flagged with a relocation / downsizing adaptation risk. A transparent
    #: decision threshold, not a prediction.
    relocation_risk_revenue_drop: float = 0.08

    def customer_multiplier(self, sector: str) -> float:
        return dict(self.customer_per_worker).get(sector, 1.0)

    def deliveries_rate(self, sector: str) -> float:
        return dict(self.deliveries_per_1000sqm).get(sector, 1.0)

    def as_dict(self) -> dict:
        d = asdict(self)
        # tuples-of-tuples → plain dicts for a clean JSON assumptions echo
        d["customer_per_worker"] = dict(self.customer_per_worker)
        d["deliveries_per_1000sqm"] = dict(self.deliveries_per_1000sqm)
        return d


#: The default firm-translation assumption set.
DEFAULT_BUSINESS_PARAMS = BusinessParams()


#: Map raw building "kind" codes (data/city/buildings.geojson property ``k``) to
#: the Business-View firm sectors. Non-commercial kinds (residential, park) are
#: NOT firms and are excluded from the Business View entirely.
BUILDING_KIND_TO_SECTOR: dict[str, str] = {
    "office": "office / professional services",
    "tower": "office / professional services",
    "podium": "retail / commercial podium",
    "lowrise": "retail & hospitality",
    "mixed": "mixed-use commercial",
    "industrial": "industrial / logistics",
}
