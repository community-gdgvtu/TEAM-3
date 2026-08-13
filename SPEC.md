# URBAN — Policy Digital Twin / Society Simulation Engine

## Master Build Instruction

> **Product thesis:** URBAN is a policy simulation environment that lets governments test, stress-test, debate, amend, and explore policies before they are deployed in the real world.
>
> **One-line pitch:** **Run the policy before you run the country.**
>
> **Core analogy:** Software has staging environments. Aircraft have simulators. Financial strategies are backtested. Public policy should have a simulation environment too.

---

# 0. The Product We Are Building

Build **URBAN**, an interactive government policy digital twin.

A policymaker should be able to:

1. **Write or upload a proposed policy** in ordinary language.
2. Have URBAN convert it into explicit, editable policy parameters.
3. Pull historical/legacy datasets relevant to the policy and geography.
4. Reconstruct a calibrated **baseline model of society** before the intervention.
5. Create a **counterfactual world** in which the policy is introduced.
6. Simulate direct, indirect, distributional, behavioural, spatial, political, environmental, and economic effects.
7. Move a **draggable timeline from implementation through 10 years** and watch the simulated world evolve.
8. Enter different 3D views:
   - City / country map
   - Parliament chamber
   - Press room
   - Household / citizen view
   - Business view
9. Run a **Model Parliament** in which government, opposition, independents, committees, experts, and affected constituencies challenge the policy.
10. Run a **Devil's Advocate / Red Team** whose only job is to find failure modes, unintended consequences, exploit paths, inequities, and second-order effects.
11. Simulate **public reaction** across heterogeneous population cohorts.
12. Generate **clearly labelled simulated media coverage** showing plausible narratives that could emerge under each scenario.
13. Compare the proposed policy with:
    - no intervention,
    - alternative policies,
    - amended versions,
    - different assumptions.
14. Ask URBAN to **search policy space** for a better intervention under explicit constraints.
15. Show uncertainty, evidence, assumptions, provenance, and model limitations for every important output.

URBAN is **not** an LLM that guesses the future.

It is a **hybrid policy-modelling system** in which statistical, causal, economic, spatial, microsimulation and agent-based models produce quantitative outcomes, while LLM agents perform interpretation, deliberation, argument generation, scenario narration, document parsing and red-teaming.

---

# 1. First-Principles Problem

Public policy is an intervention into a complex adaptive system.

Conceptually:

```text
Current society
    ↓
Policy intervention
    ↓
Immediate behavioural response
    ↓
Market / institutional response
    ↓
Second-order effects
    ↓
Political + public response
    ↓
Policy adaptation / circumvention
    ↓
Long-run equilibrium / path dependence
```

A policy rarely has a single effect.

Example:

```text
Congestion charge
→ driving cost rises
→ some commuters change mode
→ bus demand rises
→ crowding changes
→ retail footfall changes
→ delivery routes change
→ traffic shifts into neighbouring streets
→ emissions change
→ household transport burden changes
→ political support changes
→ enforcement changes
→ firms and households adapt
```

The product must therefore model the **system**, not merely generate a textual impact assessment.

---

# 2. Epistemic Rule: Forecast vs Scenario

This is a non-negotiable product principle.

URBAN must never present a synthetic future as certain fact.

Every output belongs to one of four classes:

| Class | Meaning | UI treatment |
|---|---|---|
| **Observed** | Directly present in sourced historical data | Solid line / factual |
| **Estimated** | Inferred from statistical or causal estimation | Estimate + confidence interval |
| **Simulated** | Produced by structural/agent/system model | Scenario distribution |
| **Generated** | LLM-created narrative, speech, headline or reaction | Clearly marked `SIMULATED` |

Examples:

- Historical unemployment = **Observed**
- Estimated elasticity = **Estimated**
- 18% traffic reduction = **Simulated**
- Future newspaper front page = **Generated scenario**

Never label generated headlines as "the news that will happen."

Label them:

> **SIMULATED MEDIA SCENARIO — generated from Scenario B outcomes**

Long-horizon outputs must widen uncertainty rather than create false precision.

---

# 3. Product Flow

## Step 1 — Policy Input

User can:

- type a policy,
- paste legislation,
- upload a PDF,
- upload a budget document,
- import a draft regulation,
- choose an existing policy template.

Example:

> Introduce a $10 congestion charge for private vehicles entering the central business district between 7:00 AM and 7:00 PM, beginning 1 January 2027. Exempt emergency vehicles and disability permit holders. Spend 70% of net proceeds on buses.

---

## Step 2 — Policy Compiler

Convert natural language into an explicit **Policy DSL**.

Example:

```yaml
policy:
  id: congestion_charge_v1
  jurisdiction: example_city
  domain:
    - transport
    - climate
    - taxation

  intervention:
    type: road_pricing
    amount: 10
    currency: local
    geographic_zone: cbd_polygon
    active_hours:
      start: "07:00"
      end: "19:00"
    implementation_date: "2027-01-01"

  exemptions:
    - emergency_vehicle
    - disability_permit

  revenue_allocation:
    public_transport: 0.70
    general_fund: 0.30

  stated_objectives:
    congestion_reduction: true
    emissions_reduction: true
    public_transport_improvement: true

  constraints:
    max_low_income_burden_increase_pct: 5
```

Display every extracted assumption for human correction.

Never bury assumptions inside prompts.

---

# 4. Data Fabric — Legacy + Live Data

URBAN needs a **data ingestion and provenance layer**.

Support:

- CSV
- XLSX
- JSON
- government APIs
- open-data portals
- geospatial files
- GTFS transit feeds
- historical census tables
- economic time series
- public budget data
- parliamentary records / Hansard
- election results
- public consultation data
- historical policy evaluations
- survey data
- environmental measurements
- anonymised administrative datasets where legally available

For every dataset store:

```yaml
dataset:
  title:
  publisher:
  source_url:
  retrieved_at:
  geographic_scope:
  spatial_resolution:
  time_start:
  time_end:
  frequency:
  units:
  variables:
  license:
  missingness:
  revision:
  confidence:
  transformation_history:
```

## Data Harmonisation

Build pipelines for:

- geographic joins,
- time alignment,
- unit normalisation,
- inflation adjustment,
- population weighting,
- missing-data treatment,
- schema mapping,
- outlier detection,
- deduplication,
- provenance tracking.

No model output should exist without a traceable path back to:

```text
input data → transformation → model → assumptions → result
```

---

# 5. Baseline World Model

Before simulating policy, reconstruct **World A: no intervention**.

The baseline should contain only layers relevant to the selected policy.

Potential layers:

### Population
- age
- household structure
- income
- employment
- education
- mobility
- disability/access needs
- tenure / housing status

### Economy
- sectors
- firms
- employment
- wages
- household expenditure
- prices
- tax flows
- government spending

### Geography
- roads
- buildings
- parcels
- land use
- transit
- schools
- hospitals
- public services
- business locations

### Environment
- emissions
- air quality
- energy
- temperature
- flooding
- land use

### Institutions
- government
- parliament
- agencies
- local councils
- enforcement bodies

### Society
- public opinion
- political affiliation distributions where lawful and aggregate
- media environment
- civic organisations
- industry groups
- unions / associations where relevant

The system should build the **smallest sufficient world model** required by the policy rather than attempting to simulate everything every time.

---

# 6. Synthetic Population

Create a statistically calibrated synthetic population from aggregate or microdata.

Example citizen:

```json
{
  "agent_id": "CIT-18493",
  "age": 46,
  "household_size": 4,
  "income_band": "lower-middle",
  "occupation": "retail_worker",
  "home_zone": "Z142",
  "work_zone": "Z008",
  "car_access": true,
  "public_transit_access": true,
  "baseline_commute_minutes": 31,
  "risk_aversion": 0.62,
  "price_sensitivity": 0.73,
  "policy_salience": 0.45
}
```

## Critical Scaling Architecture

Do **not** run an expensive LLM call for every simulated citizen on every timestep.

Use hierarchical simulation:

```text
100,000+ numerical micro-agents
        ↓
1,000 behavioural cohorts
        ↓
100 representative deliberative agents
        ↓
20 high-detail LLM agents
```

Numerical agents handle:

- probability of mode switching,
- spending changes,
- labour responses,
- migration,
- consumption,
- service use.

LLM representative agents handle:

- open-ended reasoning,
- political reaction,
- complaints,
- support,
- social discussion,
- argument formation,
- narrative response.

This keeps the simulation computationally tractable while preserving heterogeneous social reasoning.

---

# 7. Hybrid Forecast Engine

URBAN should select models by causal mechanism.

Do not use one universal forecasting model.

## 7.1 Historical Analogue / Causal Layer

When comparable past policy interventions exist, estimate effects using appropriate methods such as:

- difference-in-differences,
- event studies,
- synthetic controls,
- matching / weighting,
- regression discontinuity where valid,
- instrumental variables where justified,
- Bayesian causal models.

Outputs:

```text
Estimated policy effect
Confidence interval
Historical analogue quality
Parallel-trend / identification diagnostics
Transferability score
```

---

## 7.2 Time-Series Layer

For variables whose temporal structure is informative:

- dynamic regression,
- state-space models,
- Bayesian structural time series,
- vector autoregression where appropriate,
- hierarchical forecasting.

Forecast **World A** first.

Then policy models alter the baseline trajectory.

---

## 7.3 Microsimulation Layer

Use household/person/firm-level microsimulation for:

- tax changes,
- benefits,
- subsidies,
- eligibility,
- household income,
- distributional impacts.

Compute:

```text
Who gains?
Who loses?
By how much?
Which decile?
Which neighbourhood?
Which household type?
```

---

## 7.4 Economic Spillover Layer

For an MVP, use transparent:

- input-output relationships,
- elasticities,
- sector exposure,
- labour / consumption responses.

For a more advanced system, support:

- computable general equilibrium models,
- heterogeneous-agent macro models,
- regional economic models.

---

## 7.5 Agent-Based Layer

Use ABM for behaviours not adequately captured by aggregate equations:

- commuting decisions,
- compliance,
- firm relocation,
- household adaptation,
- social influence,
- protest / support mobilisation,
- information diffusion.

Each behavioural rule must have:

```text
source/calibration
parameter
range
sensitivity
```

---

## 7.6 System Dynamics Layer

Use stocks and flows for domains such as:

- housing supply,
- hospital capacity,
- energy infrastructure,
- public debt,
- workforce pipelines,
- emissions accumulation.

---

## 7.7 Spatial Layer

Model geography explicitly.

Examples:

- traffic assignment,
- accessibility,
- travel time,
- service catchments,
- business footfall,
- pollution dispersion proxies,
- land-use effects,
- infrastructure bottlenecks.

---

# 8. Ensemble Forecasting

Every policy scenario should be evaluated by multiple relevant engines.

Conceptually:

```text
Historical evidence
       +
Causal estimates
       +
Time-series baseline
       +
Microsimulation
       +
Agent behaviour
       +
Spatial model
       +
Economic model
       ↓
Model ensemble
       ↓
Outcome distributions
```

Weight models by:

- backtest performance,
- relevance,
- identification strength,
- geographic similarity,
- temporal recency,
- calibration quality.

Do not average incompatible models blindly.

---

# 9. Time Machine

The central interface is a **draggable timeline**.

Default milestones:

```text
T0       Implementation
1 month
3 months
5 months
1 year
2 years
5 years
10 years
```

Allow continuous scrubbing between checkpoints.

## Time Horizons

### Immediate — days/weeks
- compliance
- traffic
- queues
- service demand
- enforcement
- media attention

### Short term — 1–6 months
- behaviour substitution
- household spending
- business adaptation
- public opinion
- political reaction

### Medium term — 6 months–2 years
- hiring
- investment
- relocation
- market adaptation
- budget effects
- infrastructure response

### Long term — 2–10 years
- structural change
- demographic movement
- capital investment
- land use
- path dependence
- institutional adaptation

The confidence band must visibly widen as the user moves into the future.

---

# 10. Event Ledger

Every meaningful change in the simulation becomes an event.

Example:

```yaml
event:
  timestamp: 2027-02-18
  scenario_month: 2
  type: transit_capacity
  cause:
    - congestion_charge
    - mode_shift
  description: "Peak bus demand exceeds baseline capacity."
  affected_agents: 18420
  confidence: 0.71
  downstream:
    - crowding
    - commute_delay
    - public_sentiment
```

The event ledger becomes the shared truth used by:

- map,
- dashboard,
- parliament,
- public-opinion model,
- press simulation,
- red team.

Generated narratives must not invent quantitative events absent from this ledger.

---

# 11. Model Parliament

Create a 3D parliamentary chamber.

The purpose is not theatre alone. It is an **adversarial policy stress test**.

## Participants

- Government / sponsor
- Main opposition
- Minor parties
- Independents
- Committee chair
- Treasury / finance analyst
- Domain expert
- Implementation agency
- Equity advocate
- Industry representative
- Community representative
- Devil's Advocate

For real jurisdictions, initialise positions from:

- public party manifestos,
- parliamentary speeches,
- voting records,
- committee reports,
- official submissions.

Do not claim to predict the exact future words of a named politician.

Generate **plausible arguments derived from sourced positions**.

---

## Parliamentary Simulation Cycle

```text
Policy introduced
      ↓
First reading
      ↓
Opposition critique
      ↓
Expert evidence
      ↓
Public submissions
      ↓
Committee review
      ↓
Amendments proposed
      ↓
Simulation reruns amended policy
      ↓
Second debate
      ↓
Support coalition changes
      ↓
Final vote scenario
```

At any point, the user can click:

> **Apply amendment and re-simulate**

Example:

```text
OPPOSITION AMENDMENT

Exempt households below the 30th income percentile.

[SIMULATE AMENDMENT]
```

URBAN then recomputes economic, distributional, traffic and political outcomes.

This creates a powerful closed loop:

```text
debate → amendment → simulation → new evidence → debate
```

---

# 12. Devil's Advocate Engine

The Devil's Advocate is deliberately hostile to the proposal.

Its job is to discover:

- Goodhart's-law failures
- loopholes
- avoidance behaviour
- enforcement problems
- perverse incentives
- displacement effects
- distributional harms
- black markets
- administrative burden
- capacity bottlenecks
- behavioural adaptation
- political backlash
- legal conflicts
- budget overruns
- unintended environmental consequences
- edge cases

Prompt logic:

```text
Do not attempt to make the policy look good.
Search for the strongest plausible mechanisms by which the policy:
1. fails to achieve its stated goal,
2. creates a new problem,
3. shifts harm elsewhere,
4. creates inequitable outcomes,
5. can be gamed,
6. becomes politically or operationally unsustainable.

Every quantitative claim must reference a simulation result or source.
Distinguish evidence from hypothesis.
```

Output a ranked **Failure Mode Register**:

| Risk | Mechanism | Severity | Probability range | Evidence | Mitigation |
|---|---|---:|---:|---|---|

---

# 13. Public Reaction Simulation

Do not represent "the public" as one agent.

Segment by relevant characteristics.

Possible cohorts:

- income decile
- age
- geography
- occupation
- transport mode
- renter/homeowner
- business owner
- student
- parent
- retiree
- industry exposure

Each cohort has:

```text
material impact
perceived fairness
policy understanding
trust
ideological prior
social influence
media exposure
personal salience
```

Model:

```text
Material experience
      +
Prior attitude
      +
Social network exposure
      +
Media narratives
      +
Elite cues
      ↓
Opinion update
```

Outputs:

```text
Strong support
Support
Neutral
Oppose
Strong oppose
Uncertain
```

Show distribution by geography and cohort.

---

# 14. Social Network / Opinion Diffusion

Build an abstract social graph.

Nodes:
- citizen cohorts
- journalists
- politicians
- institutions
- influencers
- community groups

Edges:
- social influence
- media exposure
- geography
- workplace
- political affinity

Simulate:

- issue salience,
- narrative spread,
- opinion polarisation,
- coalition formation,
- information shocks.

LLM opinion agents must be calibrated against empirical survey/discourse data where possible because unconstrained LLM agents can exhibit systematic consensus and truth-seeking biases that do not necessarily reflect real populations.

---

# 15. Simulated Press Room + Media Future

Create a 3D **Press Room**.

At any timeline point, the user can open:

### News Feed
### Press Conference
### Editorial Spectrum
### Public Questions

The media engine reads only:

- event ledger,
- outcome metrics,
- public-opinion state,
- parliamentary state,
- scenario assumptions.

Generate plausible coverage from **media archetypes**:

- public-service broadcaster
- financial/business press
- local newspaper
- tabloid/populist outlet
- environmental publication
- industry publication

Example:

```text
SIMULATED MEDIA SCENARIO
Month 5 — Scenario B

BUSINESS PRESS
CBD traffic falls, but logistics operators warn of rising delivery costs

LOCAL NEWS
Bus crowding emerges as central complaint five months into transport reforms

PUBLIC BROADCASTER
Government considers targeted exemption after distributional review
```

The system may also produce a simulated front page.

Every artifact must visibly state:

> **SIMULATED — NOT A REAL ARTICLE OR FORECAST OF A SPECIFIC OUTLET**

Do not fabricate real journalist bylines.

---

# 16. Press Conference Simulation

Allow the policymaker to stand in a virtual press room.

Journalist agents ask questions based on the actual model results.

Example:

> Your own simulation estimates that the lowest-income commuters experience the largest increase in travel time. Why was this not mitigated in the original proposal?

The policymaker can answer manually or ask URBAN to draft an answer.

Journalists can ask follow-ups.

This is both:

- a policy stress test,
- a communications rehearsal,
- a way to discover unresolved weaknesses.

---

# 17. 3D Microcosm of Society

The 3D interface should make abstract policy consequences tangible.

## World View

Map displays:

- people flows
- traffic
- transit
- businesses
- pollution
- service access
- fiscal flows
- support/opposition heatmaps

## Parliament View

3D chamber:
- government benches
- opposition
- committees
- amendment queue
- live support meter

## Press View

3D briefing room:
- journalists
- generated questions
- simulated stories
- narrative trends

## Citizen View

Click a household.

Example:

```text
Household 18,493

Income: $48,200
2 adults / 2 children
Home: Zone 142
Work: CBD

BEFORE POLICY
Commute: 31 min
Transport cost: $182/month

MONTH 5
Commute: 43 min
Transport cost: $156/month

YEAR 2
Commute: 34 min
Transport cost: $149/month

Why?
Bus capacity initially lags demand.
Additional service funded from policy revenue enters operation in month 11.
```

## Business View

Click a firm.

Show:

- footfall
- labour accessibility
- deliveries
- costs
- revenue proxy
- adaptation decisions.

This makes the model explainable at both **macro** and **micro** levels.

---

# 18. Multi-Agent Institutional Layer

Create specialist agents.

## Economist Agent
Tests:
- growth
- prices
- productivity
- employment
- fiscal effects
- market substitution

## Equity Agent
Tests:
- distribution by income
- geography
- protected/vulnerable groups where legally and ethically appropriate
- accessibility
- burden incidence

## Climate Agent
Tests:
- emissions
- energy
- resilience
- environmental externalities

## Implementation Agent
Tests:
- staffing
- technology
- enforcement
- administrative burden
- procurement
- rollout timing

## Legal/Constitutional Research Agent
Flags issues requiring human legal review.
It does not present itself as providing authoritative legal advice.

## Opposition Agent
Constructs the strongest evidence-grounded case against the policy.

## Government Agent
Constructs the strongest evidence-grounded case for it.

## Devil's Advocate
Searches for mechanisms both sides missed.

## Auditor
Checks:
- unsupported claims
- missing data
- inconsistent assumptions
- model disagreement
- suspicious precision.

---

# 19. Feedback Loops

The world must evolve recursively.

For each simulation step:

```python
for t in timeline:
    apply_policy_rules(t)
    update_external_conditions(t)
    update_agent_constraints(t)
    update_agent_behaviour(t)
    update_network_flows(t)
    update_markets(t)
    update_public_services(t)
    update_environment(t)
    update_government_budget(t)
    update_public_opinion(t)
    update_political_response(t)
    generate_event_ledger(t)
    propagate_second_order_effects(t)
```

Political response can itself alter policy.

Example:

```text
Policy
→ negative public reaction
→ amendment
→ lower charge
→ weaker traffic effect
→ reduced revenue
→ slower bus expansion
→ renewed crowding
```

That recursive feedback is central to the concept.

---

# 20. External Shocks

Separate policy effects from exogenous scenarios.

Provide toggles:

- recession
- fuel-price spike
- flood
- heatwave
- population growth
- migration change
- technology adoption
- interest-rate shock

Default simulation should use a transparent baseline.

Shocks are scenario assumptions, not secretly random events.

Allow:

```text
Policy performs well under baseline
but fails under:
[✓] recession
[✓] fuel shock
[ ] population shock
```

This turns URBAN into a genuine **stress-testing environment**.

---

# 21. Counterfactual Comparison

Always preserve at least two worlds:

### World A — Baseline
Policy is not implemented.

### World B — Intervention
Policy is implemented.

Then allow:

### World C — Opposition Amendment

### World D — URBAN Optimised Policy

Display:

```text
Δ outcome = World B − World A
```

Never show intervention metrics without the baseline.

---

# 22. Policy Optimiser

Eventually URBAN should work backwards.

Input:

```yaml
objective:
  reduce_transport_emissions_pct: 20
constraints:
  max_average_commute_increase_pct: 5
  max_low_income_burden_increase_pct: 2
  max_budget: 100000000
```

Search candidate policy configurations.

Examples:

- congestion charge
- bus frequency increase
- parking levy
- pedestrianisation
- transit subsidy
- delivery time windows
- combinations

Run simulations and build a **Pareto frontier**.

Output:

```text
Policy A — cheapest
Policy B — most equitable
Policy C — largest emissions reduction
Policy D — best balanced outcome
```

The long-term vision is not merely:

> Policy → forecast

It is:

> Objective → search policy space → simulate → red-team → optimise

---

# 23. SDG Layer

Map outcomes onto explicit SDG targets and indicators.

Core URBAN alignment:

## SDG 11 — Sustainable Cities and Communities
Urban planning, transport, accessibility, housing, resilience and public services.

## SDG 16 — Peace, Justice and Strong Institutions
More effective, accountable, transparent and evidence-informed institutions.

Secondary:

## SDG 10 — Reduced Inequalities
Distributional impacts and unequal burdens.

## SDG 13 — Climate Action
Emissions and climate-policy impacts.

Do not create arbitrary "SDG scores."

Where possible, map to actual measurable indicators or transparent proxy metrics.

Every SDG result should show:

```text
indicator / proxy
baseline
scenario
change
data source
confidence
```

---

# 24. Uncertainty Engine

This is essential for credibility.

Run:

- parameter sweeps
- Monte Carlo simulation
- sensitivity analysis
- alternative behavioural assumptions
- model ensembles
- scenario stress tests

Output:

```text
Median impact
50% interval
80% interval
95% interval
Most influential assumptions
Model disagreement
```

Example:

```text
Estimated traffic reduction at Month 5

Median: -17.8%
80% range: -12.1% to -22.6%

Largest uncertainty:
1. mode-switch elasticity
2. bus-capacity response
3. enforcement rate
```

A 10-year forecast should look like a **fan of plausible futures**, not one precise line.

---

# 25. Backtesting

Before URBAN is trusted prospectively, it must prove it can reproduce history.

Implement **historical replay**.

Example:

```text
Choose a policy implemented in 2018.
Hide outcomes after 2018.
Give URBAN only data available before implementation.
Simulate 2018–2023.
Compare against what actually occurred.
```

Measure:

- forecast error,
- direction accuracy,
- distributional accuracy,
- geographic accuracy,
- calibration of confidence intervals,
- event timing error.

Store model scorecards.

This is one of the strongest credibility features in the entire product.

---

# 26. Explainability

Click any output.

Example:

> Why does URBAN estimate public transport demand rises 21%?

Open a causal trace:

```text
Congestion charge
↓
private vehicle generalized cost +18%
↓
mode-choice model
↓
13–24% predicted switch interval
↓
weighted by origin/destination cohort
↓
+21% median peak transit demand
```

Then show:

- equations/rules,
- parameters,
- historical analogues,
- citations,
- assumptions.

The policymaker should be able to move from a colourful 3D visual all the way down to the underlying evidence.

---

# 27. Core UI

## Main Screen

```text
┌───────────────────────────────────────────────┐
│ URBAN                                         │
│ Policy: CBD Congestion Pricing               │
├──────────────────────┬────────────────────────┤
│                      │ OUTCOMES               │
│      3D WORLD        │ Traffic        -17.8% │
│                      │ CO₂             -9.4% │
│                      │ Transit         +21.4% │
│                      │ Equity burden    +3.2% │
│                      │ Support          53%   │
├──────────────────────┴────────────────────────┤
│ T0 ━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10Y    │
│       5 months                                │
├───────────────────────────────────────────────┤
│ [PARLIAMENT] [PUBLIC] [PRESS] [RED TEAM]      │
└───────────────────────────────────────────────┘
```

---

# 28. The Hackathon Prototype

Do **not** attempt the full national system.

Build one narrow vertical slice that proves the architecture.

## Demo Policy

Choose a local urban policy with strong available data, for example:

> Pedestrianise / price vehicles entering a central district and reinvest revenue into public transport.

## Prototype Must Demonstrate

### 1. Natural Language → Policy DSL

User types policy.

URBAN extracts:
- geography
- price/intervention
- dates
- exemptions
- goals.

### 2. Baseline Digital Twin

Render:
- roads
- transit
- population cohorts
- businesses.

### 3. Synthetic Population

Create at least thousands of numerical agents with heterogeneous:
- origins/destinations
- income
- transport options
- price sensitivity.

### 4. Baseline vs Policy Simulation

Run:
- no policy
- proposed policy.

### 5. Draggable Time

At minimum:
- T0
- 1 month
- 5 months
- 1 year
- 5 years
- 10 years.

The later periods may use simplified structural assumptions, but must show increasing uncertainty.

### 6. 3D Map

Animate:
- traffic flows
- transit demand
- affected areas
- support/opposition.

### 7. Model Parliament

At least:
- Government
- Opposition
- Equity
- Economist
- Devil's Advocate.

Opposition proposes one amendment.

### 8. Re-simulate Amendment

This is the killer interaction.

```text
Opposition:
"Exempt the bottom 30% of households."

[APPLY + SIMULATE]
```

Metrics update.

### 9. Public Reaction

Show population cohort support.

### 10. Media Future

At Month 5 and Year 2, generate 3 clearly marked simulated headline scenarios based strictly on simulation events.

### 11. Evidence Drawer

Click any major result to view:
- source data,
- assumptions,
- confidence.

---

# 29. Killer Demo Script

## 0–10 seconds

Type:

> Pedestrianise the central district and increase bus frequency using the savings/revenue.

URBAN compiles the policy.

---

## 10–20 seconds

3D city appears.

Click:

> **RUN COUNTERFACTUAL**

Agents and flows animate.

---

## 20–30 seconds

Scrub timeline:

```text
T0 → Month 5
```

Dashboard updates:

```text
Traffic ↓
Emissions ↓
Transit crowding ↑
Low-income commute burden ↑
```

Red warning appears.

---

## 30–40 seconds

Enter **Parliament**.

Opposition agent says:

> The policy's benefits are concentrated downtown while lower-income peripheral commuters bear a disproportionate travel-time cost.

It proposes an amendment.

---

## 40–50 seconds

Click:

> **APPLY AMENDMENT + RE-SIMULATE**

Return to city.

Timeline and outcomes update.

Equity improves while some climate/traffic gains are preserved.

---

## 50–60 seconds

Drag to:

> **Year 2**

Open simulated press feed.

Show:

```text
SIMULATED SCENARIO
"Transit expansion absorbs early crowding as revised transport policy enters second year"
```

Then zoom out.

Final line:

> **URBAN doesn't tell governments what to believe. It gives them a world in which to test what they believe.**

---

# 30. Technology Architecture

## Frontend
- Next.js
- TypeScript
- Mapbox GL / MapLibre + deck.gl for geospatial 3D
- Three.js for Parliament / Press Room if needed
- timeline state engine
- WebSocket/SSE updates

## Backend
- Python
- FastAPI
- worker queue for simulations
- Postgres + PostGIS
- DuckDB for local analytical workloads
- object storage for datasets / runs

## Simulation Services

```text
policy-compiler
data-ingestion
baseline-builder
synthetic-population
spatial-simulation
microsimulation
economic-impact
opinion-diffusion
parliament-engine
media-engine
uncertainty-engine
backtester
```

## AI Layer

Use the configured LLM/Gemini model for:

- policy parsing
- retrieval planning
- evidence synthesis
- representative-agent reasoning
- parliamentary debate
- devil's advocacy
- explanation
- simulated media narratives

Use structured outputs everywhere possible.

Never ask the LLM to invent quantitative simulation values.

---

# 31. Core Data Structures

## Scenario

```json
{
  "scenario_id": "S2",
  "baseline_id": "B1",
  "policy_id": "P3",
  "assumptions": [],
  "external_shocks": [],
  "time_horizon_months": 120,
  "seed": 12345
}
```

## Outcome

```json
{
  "metric": "peak_transit_demand",
  "t": 5,
  "baseline": 100,
  "scenario_median": 121.4,
  "p10": 114.1,
  "p90": 129.7,
  "unit": "index",
  "provenance": ["MODEL-MODECHOICE-1", "DATA-OD-2025"],
  "status": "SIMULATED"
}
```

## Agent State

```json
{
  "agent_id": "CIT-18493",
  "t": 5,
  "location": "Z142",
  "income": 4020,
  "commute_minutes": 43,
  "monthly_transport_cost": 156,
  "policy_support": -0.21
}
```

---

# 32. Reproducibility

Every run must store:

- dataset versions
- model versions
- parameters
- random seed
- prompts
- policy DSL
- assumptions
- code version
- timestamp.

A user should be able to click:

> **REPRODUCE RUN**

and generate the same scenario.

---

# 33. Model Registry

Maintain:

```text
Model
Version
Purpose
Policy domains
Input requirements
Calibration geography
Calibration period
Validation score
Known limitations
Owner
Last reviewed
```

Never silently use a model outside its validated scope.

---

# 34. Guardrails Against "AI Astrology"

The platform fails if it becomes a beautiful interface for fabricated certainty.

Therefore:

1. LLMs never generate core numerical policy effects.
2. Every numerical result is tagged observed / estimated / simulated.
3. Every major metric has uncertainty.
4. Every major result exposes assumptions.
5. Long-run uncertainty widens.
6. Generated news is labelled synthetic.
7. Real politicians are not assigned invented factual beliefs.
8. Parliament outputs cite public-source positions when representing real parties.
9. The system shows disagreement between models.
10. Users can change assumptions and rerun.
11. Backtesting scores are visible.
12. URBAN calls itself a **decision-support / scenario simulation platform**, not an oracle.

---

# 35. What Makes URBAN Novel

URBAN is not merely:

- a regulatory impact assessment generator,
- an economic forecast dashboard,
- a digital twin,
- a chatbot for politicians,
- an agent-based society,
- a parliament simulator,
- a media simulator.

Its novelty is the **closed loop between all of them**:

```text
POLICY
  ↓
DATA
  ↓
COUNTERFACTUAL SOCIETY
  ↓
ECONOMIC + SPATIAL + DISTRIBUTIONAL SIMULATION
  ↓
PUBLIC RESPONSE
  ↓
PARLIAMENTARY OPPOSITION
  ↓
MEDIA / NARRATIVE ENVIRONMENT
  ↓
AMENDMENTS
  ↓
RE-SIMULATION
  ↓
OPTIMISED POLICY
```

The political response becomes part of the simulated system rather than a paragraph at the end of a report.

---

# 36. Product Vision

### Stage 1 — Policy Sandbox
Evaluate one proposed intervention.

### Stage 2 — Society Simulator
Model heterogeneous households, firms, institutions and public response.

### Stage 3 — Political Digital Twin
Parliament, opposition, committees, lobbying, consultation and media response.

### Stage 4 — Policy Search Engine
Given an objective and constraints, automatically search the space of interventions.

### Stage 5 — Continuous Government Twin
After a policy is deployed, ingest observed outcomes and continuously update the model:

```text
forecast → deployment → observed data → calibration → improved forecast
```

Eventually URBAN becomes a learning system for institutional memory.

Every policy leaves behind:

- assumptions,
- predicted effects,
- actual effects,
- model errors,
- amendments,
- lessons.

Governments stop repeatedly losing knowledge when administrations or staff change.

---

# 37. North-Star Experience

A minister asks:

> What happens if we implement this?

URBAN should answer:

```text
Here is the baseline.

Here are the historical analogues.

Here are the mechanisms through which the policy acts.

Here is the median simulated outcome.

Here is the uncertainty.

Here is who benefits.

Here is who loses.

Here is where the policy is most likely to fail.

Here is the opposition's strongest argument.

Here is how public opinion may evolve under these assumptions.

Here are plausible media narratives if these simulated events occur.

Here are three amendments that reduce the largest risks.

Here is what happens if we adopt each amendment.

Here is the policy configuration that best satisfies your stated goals.

Here is every assumption and piece of evidence behind those conclusions.
```

That is URBAN.

---

# 38. Research Basis

The design should be grounded in established policy-modelling practice rather than presented as an entirely new scientific capability.

### Regulatory impact and ex-post evaluation
OECD describes regulatory impact assessment as a tool for evaluating positive and negative effects of proposed regulations and notes substantial room for improvement in ex-post evaluation across OECD governments.

- OECD, *Government at a Glance 2025 — Regulatory Impact Assessment*
  https://www.oecd.org/en/publications/government-at-a-glance-2025_0efd0bcd-en/full-report/regulatory-impact-assessment_5dd9e272.html
- OECD, *Government at a Glance 2025 — Ex post evaluation*
  https://www.oecd.org/en/publications/government-at-a-glance-2025_0efd0bcd-en/full-report/ex-post-evaluation_5fd27bda.html

### Existing policy simulation
The European Commission already uses specialised quantitative models for policy analysis, including regional general-equilibrium modelling and tax-benefit microsimulation.

- European Commission JRC — RHOMOLO
  https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-rhomolo/
- European Commission JRC — EUROMOD
  https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-euromod/policy-support/
- European Commission JRC — EU-EMS
  https://web.jrc.ec.europa.eu/policy-model-inventory/explore/models/model-eu-ems/

### Transparency and uncertainty
JRC guidance stresses that models used for policy support must be interpreted within their purpose and scope, and that uncertainty/sensitivity analysis is essential.

- JRC, *Using models for policymaking*
  https://publications.jrc.ec.europa.eu/repository/handle/JRC133950
- JRC, *Uncertainty and Sensitivity Analysis for policy decision making*
  https://publications.jrc.ec.europa.eu/repository/handle/JRC122132

### Distributional analysis
The World Bank emphasises analysing who gains and loses from policy and the channels through which those impacts occur.

- World Bank — Distributional Impacts of Policy
  https://www.worldbank.org/ext/en/topic/fiscal-policy-and-growth/distributional-impact-policy

### LLM-agent social simulation
Research demonstrates both the potential and limitations of LLM-based social agents.

- Park et al., *Generative Agents: Interactive Simulacra of Human Behavior*
  https://arxiv.org/abs/2304.03442
- Chuang et al., *Simulating Opinion Dynamics with Networks of LLM-based Agents*
  https://aclanthology.org/2024.findings-naacl.211/
- Tang et al., *GenSim: A General Social Simulation Platform with Large Language Model based Agents*
  https://aclanthology.org/2025.naacl-demo.15/
- Manning & Horton, *General Social Agents*
  https://www.nber.org/papers/w34937
- *Generative AI for climate governance and acceptability-constrained policy design*
  https://www.nature.com/articles/s44168-026-00362-6

These sources motivate a hybrid approach: **mechanistic and empirical models for quantitative effects + calibrated LLM agents for open-ended social and political reasoning**.

---

# 39. Final Product Principle

The product should never imply:

> "AI knows what will happen."

The product should demonstrate:

> **"Given these data, causal assumptions, behavioural models and uncertainties, these are the futures that become more or less plausible — and here is how the policy performs across them."**

That is the standard required for URBAN to move from a visually impressive hackathon demo into credible government decision infrastructure.
