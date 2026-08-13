/**
 * Tiny typed client for the URBAN backend.
 *
 * The base URL comes from `NEXT_PUBLIC_API_BASE_URL` so the same build can point
 * at local dev or a deployed backend. All values returned by the twin are tagged
 * Observed/Estimated/Simulated/Generated per SPEC §34; this module only carries
 * the liveness probe for now.
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface Health {
  status: string;
  service: string;
  version: string;
  environment: string;
  llm_enabled: boolean;
}

/** Fetch the backend liveness probe. Throws on network/HTTP error. */
export async function getHealth(signal?: AbortSignal): Promise<Health> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    signal,
    // Always hit the live backend; never serve a stale cached health status.
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as Health;
}

// ---------------------------------------------------------------------------
// Policy compiler (SPEC §3) — POST /policy/compile
// ---------------------------------------------------------------------------

/**
 * The structured Policy DSL is deliberately typed loosely on the client: the
 * backend (`app/policy/dsl.py`) owns the authoritative schema, and the editable
 * assumptions panel reads/writes fields by dotted path rather than by a fixed
 * shape. Keeping it as a nested record avoids the two schemas drifting.
 */
export type PolicyDSL = Record<string, unknown>;

/**
 * One extracted/inferred field surfaced for human correction. Per SPEC §3 the
 * compiler must "display every extracted assumption … never bury assumptions
 * inside prompts", so each carries where it came from and how sure we are.
 */
export interface Assumption {
  /** Dotted path into the DSL, e.g. `intervention.amount`. */
  field: string;
  /** The value the compiler chose (scalar, array, or nested object). */
  value: unknown;
  /** `stated` (verbatim), `inferred` (derived), or `default` (not in text). */
  source: "stated" | "inferred" | "default" | string;
  /** 0..1 confidence. */
  confidence: number;
  /** Short human-readable justification. */
  rationale: string;
}

export interface CompileResponse {
  policy: PolicyDSL;
  assumptions: Assumption[];
  /** `"llm"` or `"rule_based"`. */
  method: string;
  /** Always `"Generated"` — the DSL is machine-produced (SPEC §34). */
  provenance: string;
  warnings: string[];
}

export interface CompileRequest {
  text: string;
  jurisdiction?: string;
}

/** Compile natural-language policy text into a Policy DSL. Throws on error. */
export async function compilePolicy(
  req: CompileRequest,
  signal?: AbortSignal,
): Promise<CompileResponse> {
  const res = await fetch(`${API_BASE_URL}/policy/compile`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = `Backend returned HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON error body; keep the generic message.
    }
    throw new Error(detail);
  }
  return (await res.json()) as CompileResponse;
}

// ---------------------------------------------------------------------------
// Baseline (World A) — GET /baseline (SPEC §5/§9)
// ---------------------------------------------------------------------------

/** Provenance class for a single number (SPEC §8). */
export type MetricTag = "Observed" | "Estimated" | "Simulated" | "Generated";

export interface Checkpoint {
  label: string;
  t_months: number;
  t_years: number;
}

/** A metric's central value + uncertainty band at one checkpoint (SPEC §8/§9). */
export interface MetricPoint {
  t_months: number;
  value: number;
  low: number;
  high: number;
}

export interface MetricSeries {
  key: string;
  label: string;
  unit: string;
  tag: MetricTag;
  method: string;
  assumptions: string[];
  points: MetricPoint[];
}

export interface BaselineTimeSeries {
  provenance: MetricTag;
  note: string;
  checkpoints: Checkpoint[];
  series: MetricSeries[];
  trend: Record<string, unknown>;
}

export interface ModeShare {
  car: number;
  public_transit: number;
  walk: number;
  car_pct: number;
  public_transit_pct: number;
  walk_pct: number;
}

export interface BaselineSnapshot {
  world: string;
  provenance: MetricTag;
  note: string;
  population_agents: number;
  commuters: number;
  mode_share: ModeShare;
  traffic: Record<string, number>;
  emissions: Record<string, number>;
  transit: Record<string, number>;
  metrics: Array<{
    key: string;
    label: string;
    value: number;
    unit: string;
    tag: MetricTag;
    method: string;
    assumptions: string[];
  }>;
  params: Record<string, unknown>;
}

export interface BaselineResponse {
  world: string;
  provenance: MetricTag;
  snapshot: BaselineSnapshot;
  timeseries: BaselineTimeSeries;
}

/** Fetch the World-A baseline snapshot + time series. Throws on error. */
export async function getBaseline(
  signal?: AbortSignal,
): Promise<BaselineResponse> {
  const res = await fetch(`${API_BASE_URL}/baseline`, {
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as BaselineResponse;
}

// ---------------------------------------------------------------------------
// Simulation (World B) — POST /simulate (SPEC §5/§7.7/§21)
// ---------------------------------------------------------------------------

/** One metric's Δ(B−A) point at a checkpoint, with a combined band. */
export interface DeltaPoint {
  t_months: number;
  world_a: number;
  world_b: number;
  delta: number;
  delta_pct: number | null;
  low: number;
  high: number;
}

export interface DeltaSeries {
  key: string;
  label: string;
  unit: string;
  tag: MetricTag;
  method: string;
  points: DeltaPoint[];
}

export interface DeltaTimeSeries {
  provenance: MetricTag;
  note: string;
  checkpoints: Checkpoint[];
  series: DeltaSeries[];
}

export interface LedgerEvent {
  id: string;
  type: string;
  scenario_month: number;
  scenario_year: number;
  timestamp: string | null;
  description: string;
  cause: string[];
  affected_agents: number;
  confidence: number;
  downstream: string[];
  severity: string;
  evidence: Record<string, unknown>;
  provenance: MetricTag;
}

export interface EventLedger {
  provenance: MetricTag;
  note: string;
  policy_id: string;
  events: LedgerEvent[];
  thresholds: Record<string, unknown>;
}

export interface SimulateResponse {
  provenance: MetricTag;
  policy_id: string;
  note: string;
  world_a: { snapshot: BaselineSnapshot; timeseries: BaselineTimeSeries };
  world_b: { snapshot: Record<string, unknown>; timeseries: BaselineTimeSeries };
  delta: DeltaTimeSeries;
  event_ledger: EventLedger;
  shocks_applied: Record<string, unknown>;
  seed: number | null;
}

/** Run the deterministic policy simulation for a compiled DSL. Throws on error. */
export async function simulate(
  policy: PolicyDSL,
  signal?: AbortSignal,
): Promise<SimulateResponse> {
  const res = await fetch(`${API_BASE_URL}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as SimulateResponse;
}

// ---------------------------------------------------------------------------
// Model Parliament — POST /parliament/debate + /parliament/failure-modes
// ---------------------------------------------------------------------------

export type Stance = "support" | "oppose" | "conditional" | "challenge";

export interface EvidenceCitation {
  kind: string;
  ref: string;
  detail: string;
  tag: MetricTag;
}

export interface Argument {
  persona: string;
  role: string;
  stance: Stance;
  headline: string;
  points: string[];
  speech: string;
  citations: EvidenceCitation[];
  confidence: number;
}

export interface DebateResponse {
  provenance: MetricTag;
  note: string;
  policy_id: string;
  motion: string;
  method: string;
  arguments: Argument[];
  tally: Record<string, number>;
  summary: string;
}

/** Convene the Model Parliament to debate a compiled policy. Throws on error. */
export async function runDebate(
  policy: PolicyDSL,
  signal?: AbortSignal,
): Promise<DebateResponse> {
  const res = await fetch(`${API_BASE_URL}/parliament/debate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as DebateResponse;
}

export type Severity = "low" | "medium" | "high" | "critical";

export interface FailureMode {
  id: string;
  risk: string;
  mechanism: string;
  severity: Severity;
  probability: number;
  risk_score: number;
  evidence: EvidenceCitation[];
  mitigation: string;
  affected_agents: number;
}

export interface FailureModeRegister {
  provenance: MetricTag;
  note: string;
  policy_id: string;
  failure_modes: FailureMode[];
}

/** Devil's Advocate → ranked Failure Mode Register for a policy. Throws on error. */
export async function runFailureModes(
  policy: PolicyDSL,
  signal?: AbortSignal,
): Promise<FailureModeRegister> {
  const res = await fetch(`${API_BASE_URL}/parliament/failure-modes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as FailureModeRegister;
}

// ---------------------------------------------------------------------------
// Public reaction — POST /public (SPEC §13)
// ---------------------------------------------------------------------------

/** Support distribution over the six SPEC §13 buckets (fractions sum to ~1). */
export interface OpinionDistribution {
  strong_support: number;
  support: number;
  neutral: number;
  oppose: number;
  strong_oppose: number;
  uncertain: number;
  /** (strong_support + support) − (oppose + strong_oppose), in [-1, 1]. */
  net_support: number;
}

export interface CohortOpinion {
  key: string;
  income_band: string;
  /** `"inbound"` (commutes into CBD) or `"local"`. */
  geography: string;
  travel_mode: string;
  size: number;
  mean_material_impact: number;
  mean_fairness: number;
  mean_support: number;
  distribution: OpinionDistribution;
}

export interface PublicOpinion {
  /** Always `"Simulated"` — deterministic structural model, no poll (SPEC §34). */
  provenance: MetricTag;
  note: string;
  policy_id: string;
  population: number;
  overall: OpinionDistribution;
  cohorts: CohortOpinion[];
  params: Record<string, unknown>;
}

/** Gauge the deterministic cohort public reaction to a policy. Throws on error. */
export async function runPublicOpinion(
  policy: PolicyDSL,
  signal?: AbortSignal,
): Promise<PublicOpinion> {
  const res = await fetch(`${API_BASE_URL}/public`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as PublicOpinion;
}

// ---------------------------------------------------------------------------
// Evidence drawer — POST /evidence (SPEC §26)
// ---------------------------------------------------------------------------

/** One behavioural lever the policy applies to the mode-choice model (SPEC §7.5). */
export interface BehaviouralRule {
  name: string;
  label: string;
  parameter: string;
  value: number;
  unit: string;
  plausible_range: number[];
  sensitivity: string;
  source: string;
}

/** One node on the causal trace (input-data → … → result). */
export interface TraceStep {
  stage: "input-data" | "transform" | "model" | "assumption" | "result" | string;
  label: string;
  detail: string;
  tag: MetricTag;
  value: number | null;
  unit: string;
  refs: string[];
}

export interface TraceAssumption {
  name: string;
  value: number | string;
  unit: string;
  detail: string;
  tag: MetricTag;
}

export interface HistoricalAnalogue {
  scheme: string;
  city: string;
  year: number;
  mechanism: string;
  relevance: string;
  tag: MetricTag;
  note: string;
}

export interface TraceConfidence {
  value: number;
  band_half_width: number;
  band_rel_pct: number | null;
  horizon_months: number;
  note: string;
}

export interface TraceResult {
  world_a: number;
  world_b: number;
  delta: number;
  delta_pct: number | null;
  low: number;
  high: number;
}

export interface ProvenanceTrace {
  provenance: MetricTag;
  note: string;
  policy_id: string;
  metric_key: string;
  metric_label: string;
  unit: string;
  tag: MetricTag;
  horizon: Checkpoint;
  available_horizons_months: number[];
  result: TraceResult;
  confidence: TraceConfidence;
  ascii_trace: string;
  chain: TraceStep[];
  rules: BehaviouralRule[];
  assumptions: TraceAssumption[];
  historical_analogues: HistoricalAnalogue[];
  citations: string[];
}

/** Fetch the causal provenance trace for one metric under a policy. Throws on error. */
export async function runEvidence(
  policy: PolicyDSL,
  metricKey: string,
  horizonMonths?: number,
  signal?: AbortSignal,
): Promise<ProvenanceTrace> {
  const res = await fetch(`${API_BASE_URL}/evidence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy,
      metric_key: metricKey,
      horizon_months: horizonMonths ?? null,
    }),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = `Backend returned HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail && typeof body.detail === "object") {
        const d = body.detail as { error?: string };
        if (d.error) detail = d.error;
      }
    } catch {
      // keep generic message
    }
    throw new Error(detail);
  }
  return (await res.json()) as ProvenanceTrace;
}

// ---------------------------------------------------------------------------
// Simulated media — POST /media (SPEC §15)
// ---------------------------------------------------------------------------

export type MediaArchetype =
  | "public_broadcaster"
  | "business_press"
  | "local_news"
  | "tabloid"
  | "environmental"
  | "industry";

export type MediaSentiment = "positive" | "critical" | "mixed" | string;

export interface Headline {
  archetype: MediaArchetype;
  /** Fictional generic outlet name — never a real outlet. */
  outlet_label: string;
  headline: string;
  standfirst: string;
  angle: string;
  sentiment: MediaSentiment;
  /** Event ids / metric keys the story is built on. */
  cited_refs: string[];
  /** Mandatory SIMULATED banner (SPEC §15). */
  label: string;
  /** Always `"Generated"`. */
  provenance: MetricTag;
}

export interface MediaScenario {
  /** Horizon label, e.g. "Month 5". */
  label: string;
  scenario_month: number;
  headlines: Headline[];
}

export interface MediaResponse {
  /** `"Generated"` — media prose is generated; cited figures are Simulated. */
  provenance: MetricTag;
  disclaimer: string;
  note: string;
  policy_id: string;
  /** `"llm"` or `"template"`. */
  method: string;
  scenarios: MediaScenario[];
}

/** Generate clearly-labelled SIMULATED media coverage for a policy. Throws on error. */
export async function runMedia(
  policy: PolicyDSL,
  signal?: AbortSignal,
): Promise<MediaResponse> {
  const res = await fetch(`${API_BASE_URL}/media`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policy }),
    signal,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Backend returned HTTP ${res.status}`);
  }
  return (await res.json()) as MediaResponse;
}

// ---------------------------------------------------------------------------
// Amendment loop — a structured DSL mutation re-run through /simulate (SPEC §12)
// ---------------------------------------------------------------------------

export interface Amendment {
  label: string;
  exempt_low_income?: boolean;
  exempt_residents?: boolean;
  set_charge_amount?: number | null;
  charge_multiplier?: number | null;
  set_public_transport_share?: number | null;
}

/**
 * Apply an amendment to a compiled DSL client-side, mirroring the backend's
 * `apply_amendment` (backend/app/simulation/amendment.py). The amended DSL is
 * then re-run through `POST /simulate` — the killer interaction (SPEC §29): the
 * change is a transparent structured edit, all numbers still come from the model.
 */
export function applyAmendment(policy: PolicyDSL, a: Amendment): PolicyDSL {
  const amended = JSON.parse(JSON.stringify(policy)) as Record<string, unknown>;
  const id = String((policy as Record<string, unknown>).id ?? "policy");
  amended.id = `${id}__${a.label.replace(/ /g, "_")}`;

  const exemptions = Array.isArray(amended.exemptions)
    ? [...(amended.exemptions as string[])]
    : [];
  if (a.exempt_low_income && !exemptions.some((e) => e.toLowerCase().includes("income"))) {
    exemptions.push("low-income");
  }
  if (a.exempt_residents && !exemptions.some((e) => e.toLowerCase().includes("resident"))) {
    exemptions.push("residents");
  }
  amended.exemptions = exemptions;

  const intervention = (amended.intervention as Record<string, unknown>) ?? {};
  if (a.set_charge_amount != null) {
    intervention.amount = a.set_charge_amount;
  }
  if (a.charge_multiplier != null && typeof intervention.amount === "number") {
    intervention.amount = Math.round(intervention.amount * a.charge_multiplier * 1e4) / 1e4;
  }
  amended.intervention = intervention;

  if (a.set_public_transport_share != null) {
    const pt = a.set_public_transport_share;
    amended.revenue_allocation = {
      public_transport: pt,
      general_fund: Math.round((1 - pt) * 1e4) / 1e4,
    };
  }
  return amended as PolicyDSL;
}
