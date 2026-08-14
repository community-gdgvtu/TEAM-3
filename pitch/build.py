#!/usr/bin/env python3
"""Build the GOV SIM pitch deck.

Every demo slide is rendered from data pulled out of the running production
stack: the FastAPI engine on :8000 (measured call-by-call) and the geometry
the Next.js frontend actually ships in public/city. Nothing here is retyped
by hand — deck.json and map.json are written by mkdeck.py / mkmap.py.
"""
import json, os, html

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/Users/gavinwu/Desktop/Files on Macbook/2026 Files/01 Business/Hackathon/urban-policy-twin/pitch/govsim-pitch.html"

D = json.load(open(os.path.join(HERE, "deck.json")))
MAP = json.load(open(os.path.join(HERE, "map.json")))
FONTS = json.load(open(os.path.join(HERE, "fonts.json")))

e = lambda s: html.escape(str(s))


def num(v, dp=0):
    return f"{v:,.{dp}f}"


# ── fonts: the exact woff2 files the production app serves ──────────────────
FONT_CSS = """
@font-face{font-family:Fraunces;font-style:normal;font-weight:400 600;font-display:swap;
  src:url(data:font/woff2;base64,%(fraunces)s) format("woff2")}
@font-face{font-family:"IBM Plex Sans";font-style:normal;font-weight:400 600;font-display:swap;
  src:url(data:font/woff2;base64,%(plexsans)s) format("woff2")}
@font-face{font-family:"IBM Plex Mono";font-style:normal;font-weight:400;font-display:swap;
  src:url(data:font/woff2;base64,%(plexmono)s) format("woff2")}
@font-face{font-family:"IBM Plex Mono";font-style:normal;font-weight:600;font-display:swap;
  src:url(data:font/woff2;base64,%(plexmono6)s) format("woff2")}
""" % FONTS


# ── slide 01 ────────────────────────────────────────────────────────────────
CASES = [
    ("Netherlands", "2013–2019",
     "An algorithm flags 26,000 families for benefit fraud. Wrongly. Repayments of €20,000–60,000. "
     "Over 1,600 children removed into care. The entire cabinet resigns in 2021."),
    ("Sri Lanka", "2021",
     "Overnight ban on fertiliser imports. Rice yields fall over 30%, tea exports lose ~$425m, "
     "grocery prices rise up to 90%. Reversed in seven months. Contributed to the collapse of a presidency."),
    ("Australia", "2015–2020",
     "Robodebt. Promised $4.7bn in savings. 500,000+ people pursued for unlawful debts. "
     "$1.8bn class-action settlement. Only 5 in 10,000 debts were ever formally challenged."),
    ("India", "2016",
     "86% of currency voided overnight. Employment and output fall ~2pp in the quarter. "
     "The informal economy — half of GDP — is hit hardest."),
    ("United Kingdom", "2013–",
     "Universal Credit staged rollout. +2.8pp mental-health problems on becoming unemployed "
     "(+5.2pp for lone parents). ~35,000 burglaries and ~25,000 vehicle crimes attributable."),
]

# ── slide 05 ────────────────────────────────────────────────────────────────
INDUSTRIES = [
    ("Aviation", "Full-motion flight simulators; certification hours flown virtually"),
    ("Aerospace", "Mission profiles, re-entry, orbital insertion"),
    ("Automotive", "Crash, crumple, thermal — thousands of virtual impacts per physical one"),
    ("Semiconductors", "Full logic and timing simulation before tape-out"),
    ("Software", "Staging, CI, canary release, load and chaos testing"),
    ("Finance", "Backtesting, Monte Carlo, regulatory stress tests"),
    ("Pharmaceuticals", "In-silico trials, model-informed drug development"),
    ("Surgery", "Patient-specific rehearsal on imaging-derived models"),
    ("Nuclear", "Reactor physics and containment simulation"),
    ("Power grid", "Load flow, contingency, cascade failure"),
    ("Weather", "Numerical and now learned global models"),
    ("Epidemiology", "Outbreak and intervention modelling"),
    ("Defence", "Wargaming and force-on-force simulation"),
    ("Maritime", "Hull, seakeeping, bridge simulators"),
    ("Rail", "Signalling and timetable simulation"),
    ("Logistics", "Network, warehouse and fleet simulation"),
    ("Motorsport", "CFD and lap simulation under regulated compute budgets"),
    ("Construction", "Structural, seismic, thermal FEA"),
    ("Mining", "Ore body, blast and ventilation modelling"),
    ("Agriculture", "Yield, irrigation and climate response models"),
    ("Insurance", "Catastrophe models pricing entire national risk pools"),
    ("Telecoms", "RF propagation and network capacity planning"),
    ("Robotics", "Sim-to-real training in physics engines"),
    ("Architecture", "Daylight, airflow, occupancy, energy"),
]

# ── slide 06: the five failures, as coordinates ─────────────────────────────
FAILURE_POINTS = [
    ("Netherlands", 52.13, 5.29, "2013"),
    ("Sri Lanka", 7.87, 80.77, "2021"),
    ("Australia", -25.27, 133.78, "2015"),
    ("India", 20.59, 78.96, "2016"),
    ("United Kingdom", 55.38, -3.44, "2013"),
    ("Auckland, NZ", -36.85, 174.76, "modelled here"),
]

SDGS = [
    ("11", "Sustainable Cities and Communities", "transport access, land use, resilience"),
    ("16", "Peace, Justice and Strong Institutions", "evidence-informed, auditable, reproducible decisions"),
    ("10", "Reduced Inequalities", "burden by decile and zone, surfaced before enactment"),
    ("13", "Climate Action", "emissions per scenario"),
]

WORKS_CITED = [
    "Chodorow-Reich, Gabriel, et al. <i>Cash and the Economy: Evidence from India's Demonetization</i>. Working Paper 25370, National Bureau of Economic Research, Dec. 2018.",
    "European Court of Auditors. <i>Ex-post Review of EU Legislation: A Well-Established System, but Incomplete</i>. Special Report 16/2018, Publications Office of the European Union, 2018.",
    "Holmes, Catherine. <i>Report of the Royal Commission into the Robodebt Scheme</i>. Commonwealth of Australia, July 2023.",
    "Lam, Remi, et al. &ldquo;Learning Skillful Medium-Range Global Weather Forecasting.&rdquo; <i>Science</i>, vol. 382, no. 6677, Dec. 2023, doi:10.1126/science.adi2336.",
    "Lahiri, Amartya. &ldquo;The Great Indian Demonetization.&rdquo; <i>Journal of Economic Perspectives</i>, vol. 34, no. 1, Winter 2020, pp. 55–74.",
    "National Audit Office. <i>Government's Use of External Consultants</i>. NAO.",
    "Organisation for Economic Co-operation and Development. &ldquo;Ex-post Evaluation.&rdquo; <i>Government at a Glance 2025</i>, OECD Publishing, 2025.",
    "Parlementaire Ondervragingscommissie Kinderopvangtoeslag. <i>Ongekend Onrecht</i>. Tweede Kamer der Staten-Generaal, Dec. 2020.",
    "&ldquo;Sri Lanka's Organic Farming Experiment Went Catastrophically Wrong.&rdquo; <i>Foreign Policy</i>, 5 Mar. 2022.",
    "&ldquo;What Sri Lanka's Ban of Chemical Fertilizers in 2021 Can Teach the World.&rdquo; <i>International Water Management Institute</i>, 17 Oct. 2025.",
    "&ldquo;What Is Digital-Twin Technology?&rdquo; <i>McKinsey &amp; Company</i>, 26 Aug. 2024.",
    "Wickham, Sophie, et al. &ldquo;Universal Credit and Mental Health.&rdquo; <i>Journal of Health Economics</i>, Elsevier.",
    "&ldquo;Universal Credit, Financial Insecurity and Crime.&rdquo; <i>Journal of Law, Economics, and Organization</i>, vol. 40, no. 1, 2024, pp. 129–.",
    "OpenStreetMap contributors, via the Overpass API. Auckland extract fetched %s. Open Database Licence (ODbL) 1.0." % D["osm"]["fetched_at"],
    "New Zealand Electoral Commission — official 2023 general-election results. electionresults.govt.nz.",
    "METR-LA loop-detector corpus, 207 sensors, 5-minute resolution. huggingface.co/datasets/witgaw/METR-LA.",
]


CSS = r"""
/* GOV SIM pitch deck — the production design system (frontend/app/globals.css),
   applied to a 15-slide argument. Blueprint-ink ground, cyan linework, amber
   reserved for provenance. Committed dark: the instrument has one look. */
:root{
  --bg:#0a1620; --panel:#101f2c; --panel-2:#0d1e2a;
  --border:#223b4d; --border-strong:#2c4a5f;
  --text:#eef4f2; --muted:#85a0ab;
  --accent:#4fc3d1; --accent-dim:rgba(79,195,209,.14);
  --stamp:#e2a13d; --stamp-dim:rgba(226,161,61,.16);
  --ok:#5cc98a; --bad:#ef6b57;
  --font-display:Fraunces,ui-serif,Georgia,serif;
  --font-body:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  --ease:cubic-bezier(.16,1,.3,1);
  --rule:1px solid var(--border);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0; background:var(--bg); color:var(--text);
  font-family:var(--font-body); line-height:1.5;
  -webkit-font-smoothing:antialiased;
}
/* the production ambient aurora + grain, so the deck sits in the app's light */
body::before{
  content:""; position:fixed; inset:-10%; z-index:-2; pointer-events:none;
  background-image:
    radial-gradient(46rem 34rem at 12% 8%,rgba(79,195,209,.13),transparent 62%),
    radial-gradient(40rem 30rem at 92% 18%,rgba(226,161,61,.09),transparent 58%),
    radial-gradient(34rem 30rem at 30% 96%,rgba(79,195,209,.06),transparent 60%);
}
body::after{
  content:""; position:fixed; inset:0; z-index:-1; pointer-events:none;
  opacity:.05; mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
}

/* ── deck chrome ───────────────────────────────────────────────────────── */
/* No scroll-behavior:smooth here — a mandatory-snap container cancels
   programmatic smooth scrolls, which leaves keyboard nav dead. Slide changes
   are instant, the way presentation software behaves; the wheel still snaps. */
.deck{scroll-snap-type:y mandatory; overflow-y:auto; height:100dvh}
.slide{
  scroll-snap-align:start; scroll-snap-stop:always;
  min-height:100dvh; display:flex; flex-direction:column; justify-content:center;
  padding:clamp(1.8rem,4vw,3.6rem) clamp(1.1rem,5vw,5rem) clamp(4.4rem,6vw,5.4rem);
  position:relative;
}
.wrap{width:100%; max-width:1180px; margin:0 auto; transform-origin:top center}
.wrap-wide{max-width:1400px}
.rail{position:fixed; top:0; left:0; right:0; height:2px; background:rgba(34,59,77,.6); z-index:60}
.rail-fill{height:100%; width:0; background:var(--accent); transition:width .4s var(--ease)}
.hud{
  position:fixed; bottom:0; left:0; right:0; z-index:60;
  display:flex; align-items:center; gap:1rem; justify-content:space-between;
  padding:.5rem clamp(1.1rem,5vw,5rem);
  font-family:var(--font-mono); font-size:.66rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); background:linear-gradient(to top,rgba(10,22,32,.94),rgba(10,22,32,0));
}
.hud b{color:var(--text); font-weight:600}
.hud-mark{color:var(--stamp)}
.hud-nav{display:flex; gap:.4rem}
.hud-nav button{
  font:inherit; letter-spacing:inherit; text-transform:inherit;
  background:var(--panel); color:var(--muted); border:var(--rule); border-radius:2px;
  padding:.25rem .55rem; cursor:pointer; transition:color .2s var(--ease),border-color .2s var(--ease);
}
.hud-nav button:hover{color:var(--accent); border-color:var(--border-strong)}
.hud-nav button:focus-visible,.tgl:focus-visible,.scrub:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

/* ── type ──────────────────────────────────────────────────────────────── */
.eyebrow{
  font-family:var(--font-mono); font-size:.68rem; letter-spacing:.18em;
  text-transform:uppercase; color:var(--stamp); margin:0 0 .9rem;
}
.eyebrow-cy{color:var(--accent)}
h1,h2,h3{font-family:var(--font-display); font-weight:500; text-wrap:balance; margin:0}
h1{font-size:clamp(2.1rem,5.4vw,4.15rem); line-height:1.04; letter-spacing:-.015em}
h2{font-size:clamp(1.6rem,3.4vw,2.7rem); line-height:1.1; letter-spacing:-.01em}
h3{font-size:clamp(1.05rem,1.7vw,1.32rem); line-height:1.25}
p{margin:0}
.lede{font-size:clamp(1rem,1.35vw,1.16rem); color:var(--muted); max-width:64ch; line-height:1.62}
.kicker{
  font-family:var(--font-mono); font-size:.72rem; letter-spacing:.13em;
  text-transform:uppercase; color:var(--muted);
}
.pull{
  font-family:var(--font-display); font-size:clamp(1.15rem,2.05vw,1.72rem);
  line-height:1.32; color:var(--text); max-width:52ch; text-wrap:balance;
}
.pull em{color:var(--accent); font-style:normal}
.stamp{color:var(--stamp)}
.cy{color:var(--accent)}
.ok{color:var(--ok)} .bad{color:var(--bad)}
.mono{font-family:var(--font-mono); font-variant-numeric:tabular-nums}
.stack{display:flex; flex-direction:column}
.g0{gap:.35rem} .g1{gap:.7rem} .g2{gap:1.15rem} .g3{gap:1.8rem} .g4{gap:2.6rem}

/* ── panels: the app's surface ─────────────────────────────────────────── */
.panel{
  background:var(--panel); border:var(--rule); border-radius:3px;
  padding:clamp(.85rem,1.5vw,1.35rem);
}
.panel-2{background:var(--panel-2)}
.panel-head{
  display:flex; align-items:baseline; justify-content:space-between; gap:1rem;
  padding-bottom:.6rem; margin-bottom:.85rem; border-bottom:var(--rule); flex-wrap:wrap;
}
.panel-title{font-family:var(--font-mono); font-size:.72rem; letter-spacing:.15em; text-transform:uppercase; color:var(--text)}
.tag{
  font-family:var(--font-mono); font-size:.6rem; letter-spacing:.13em; text-transform:uppercase;
  padding:.13rem .42rem; border-radius:2px; border:1px solid var(--border-strong); color:var(--muted);
  white-space:nowrap;
}
.tag-sim{color:var(--accent); border-color:rgba(79,195,209,.45); background:var(--accent-dim)}
.tag-obs{color:var(--stamp); border-color:rgba(226,161,61,.45); background:var(--stamp-dim)}
.tag-gen{color:var(--muted)}
/* the provenance footer every demo slide carries — the deck audits itself */
.src{
  margin-top:.9rem; padding-top:.6rem; border-top:1px dashed var(--border);
  font-family:var(--font-mono); font-size:.63rem; letter-spacing:.06em; color:var(--muted);
  display:flex; flex-wrap:wrap; gap:.35rem 1.1rem; align-items:center;
}
.src b{color:var(--accent); font-weight:400}

/* ── grids ─────────────────────────────────────────────────────────────── */
.cols{display:grid; gap:clamp(.7rem,1.4vw,1.15rem)}
.c2{grid-template-columns:repeat(2,minmax(0,1fr))}
.c3{grid-template-columns:repeat(3,minmax(0,1fr))}
.c4{grid-template-columns:repeat(4,minmax(0,1fr))}
.c23{grid-template-columns:minmax(0,1.15fr) minmax(0,1fr)}
.c32{grid-template-columns:minmax(0,1.6fr) minmax(0,1fr)}
@media(max-width:900px){
  .c2,.c3,.c4,.c23,.c32{grid-template-columns:minmax(0,1fr)}
}

/* ── data tables ───────────────────────────────────────────────────────── */
table{border-collapse:collapse; width:100%; font-size:.82rem}
th,td{text-align:left; padding:.34rem .6rem; border-bottom:1px solid rgba(34,59,77,.55); vertical-align:top}
thead th{
  font-family:var(--font-mono); font-size:.6rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); font-weight:400; border-bottom:1px solid var(--border-strong);
}
td.n,th.n{text-align:right; font-family:var(--font-mono); font-variant-numeric:tabular-nums}
tbody tr:last-child td{border-bottom:none}
.scrollx{overflow-x:auto}

/* ── slide 01: the case wall ───────────────────────────────────────────── */
.case{display:grid; grid-template-columns:13rem minmax(0,1fr); gap:0 1.6rem; padding:.72rem 0; border-top:var(--rule)}
.case:last-child{border-bottom:var(--rule)}
.case-where{font-family:var(--font-mono); font-size:.78rem; color:var(--text); letter-spacing:.02em}
.case-when{font-family:var(--font-mono); font-size:.68rem; color:var(--stamp); letter-spacing:.1em}
.case-what{font-size:.87rem; color:var(--muted); line-height:1.55}
@media(max-width:760px){.case{grid-template-columns:minmax(0,1fr); gap:.25rem}}

/* ── slide 02: the perimeter ───────────────────────────────────────────── */
.perim{display:grid; grid-template-columns:minmax(0,1fr) 5.5rem minmax(0,.85fr); align-items:center; gap:0}
.vault{border:1px solid var(--border-strong); border-radius:3px; background:var(--panel-2); padding:1.1rem}
.vault-label{font-family:var(--font-mono); font-size:.6rem; letter-spacing:.16em; text-transform:uppercase; color:var(--stamp); margin-bottom:.75rem}
.ds{display:flex; align-items:center; gap:.55rem; padding:.42rem 0; border-bottom:1px solid rgba(34,59,77,.5); font-size:.85rem}
.ds:last-child{border-bottom:none}
.ds i{width:.42rem; height:.42rem; background:var(--accent); border-radius:1px; flex:none}
.barred{position:relative; height:3.4rem; display:flex; align-items:center; justify-content:center}
.barred::before{content:""; position:absolute; inset:auto 0; height:1px; background:repeating-linear-gradient(90deg,var(--bad) 0 6px,transparent 6px 11px)}
.barred span{
  position:relative; background:var(--bg); padding:.2rem .45rem; color:var(--bad);
  font-family:var(--font-mono); font-size:.58rem; letter-spacing:.16em; text-transform:uppercase;
}
.outsider{border:1px dashed var(--border-strong); border-radius:3px; padding:1.1rem; color:var(--muted)}
@media(max-width:760px){.perim{grid-template-columns:minmax(0,1fr)} .barred{height:2.6rem}}

/* ── slide 03: the loop ────────────────────────────────────────────────── */
.loopgrid{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.55rem}
.loopstep{border:var(--rule); border-radius:3px; padding:.6rem .7rem; background:var(--panel-2)}
.loopstep .k{font-family:var(--font-mono); font-size:.58rem; letter-spacing:.14em; text-transform:uppercase; color:var(--accent)}
.loopstep .v{font-size:.85rem; margin-top:.15rem}
.loopstep .w{font-family:var(--font-mono); font-size:.66rem; color:var(--muted); margin-top:.25rem}
@media(max-width:760px){.loopgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}

/* ── stat tiles ────────────────────────────────────────────────────────── */
.tile{border:var(--rule); border-radius:3px; background:var(--panel); padding:.75rem .85rem; display:flex; flex-direction:column; gap:.22rem}
.tile-k{font-family:var(--font-mono); font-size:.6rem; letter-spacing:.13em; text-transform:uppercase; color:var(--muted)}
.tile-v{font-family:var(--font-mono); font-size:clamp(1.25rem,2.5vw,1.9rem); font-variant-numeric:tabular-nums; line-height:1; color:var(--text)}
.tile-v.sm{font-size:clamp(1rem,1.7vw,1.3rem)}
.tile-u{font-family:var(--font-mono); font-size:.63rem; color:var(--muted)}
.tile-accent .tile-v{color:var(--accent)}
.tile-stamp .tile-v{color:var(--stamp)}

/* ── slide 05: industries ──────────────────────────────────────────────── */
.inds{columns:3; column-gap:2rem; font-size:.76rem}
.ind{break-inside:avoid; display:grid; grid-template-columns:7.4rem minmax(0,1fr); gap:.7rem; padding:.24rem 0; border-bottom:1px solid rgba(34,59,77,.45)}
.ind b{font-weight:500; color:var(--text); font-size:.78rem}
.ind span{color:var(--muted); line-height:1.4}
@media(max-width:1000px){.inds{columns:2}}
@media(max-width:640px){.inds{columns:1}}

/* ── slide 06: coordinates + sdg ───────────────────────────────────────── */
.sdg{border:var(--rule); border-left:2px solid var(--stamp); border-radius:2px; padding:.6rem .8rem; background:var(--panel)}
.sdg b{font-family:var(--font-mono); font-size:1.05rem; color:var(--stamp); display:block; line-height:1}
.sdg .t{font-size:.85rem; margin-top:.3rem}
.sdg .m{font-size:.72rem; color:var(--muted); margin-top:.15rem}

/* ── slide 07: the run console (the real one) ──────────────────────────── */
.console{background:var(--panel-2); border:var(--rule); border-radius:3px; overflow:hidden}
.console-top{display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.55rem .8rem; border-bottom:var(--rule); flex-wrap:wrap}
.prompt{
  font-family:var(--font-mono); font-size:.73rem; line-height:1.55; color:var(--muted);
  padding:.7rem .8rem; border-bottom:var(--rule); background:rgba(10,22,32,.5);
}
.prompt b{color:var(--text); font-weight:400}
.stages{display:flex; flex-direction:column}
.stage{
  display:grid; grid-template-columns:1.5rem minmax(0,1fr) 5.2rem 5rem;
  align-items:baseline; gap:.7rem; padding:.42rem .8rem;
  border-bottom:1px solid rgba(34,59,77,.45); font-size:.83rem;
  opacity:.25; transform:translateY(3px); transition:opacity .34s var(--ease),transform .34s var(--ease);
}
.stage.on{opacity:1; transform:none}
.stage:last-child{border-bottom:none}
.stage-i{font-family:var(--font-mono); font-size:.63rem; color:var(--accent)}
.stage-l b{font-weight:500}
.stage-l i{display:block; font-style:normal; font-family:var(--font-mono); font-size:.63rem; color:var(--muted); margin-top:.1rem}
.stage-t,.stage-b{font-family:var(--font-mono); font-size:.72rem; text-align:right; font-variant-numeric:tabular-nums}
.stage-t{color:var(--accent)} .stage-b{color:var(--muted)}
.console-foot{display:flex; justify-content:space-between; gap:1rem; padding:.55rem .8rem; border-top:var(--rule); background:rgba(10,22,32,.5); flex-wrap:wrap}
@media(max-width:700px){.stage{grid-template-columns:1.4rem minmax(0,1fr) 4.4rem; }.stage-b{display:none}}

/* ── slide 08: the stack ───────────────────────────────────────────────── */
.band{border:var(--rule); border-radius:3px; background:var(--panel); padding:.7rem .9rem; display:grid; grid-template-columns:7.5rem minmax(0,1fr); gap:1rem; align-items:start}
.band-k{font-family:var(--font-mono); font-size:.66rem; letter-spacing:.16em; text-transform:uppercase; color:var(--accent)}
.band-v{font-size:.82rem; color:var(--muted); line-height:1.55}
.band-v b{color:var(--text); font-weight:500}
.band-arrow{text-align:center; color:var(--border-strong); font-family:var(--font-mono); font-size:.8rem; line-height:1}
@media(max-width:700px){.band{grid-template-columns:minmax(0,1fr); gap:.3rem}}
.chips{display:flex; flex-wrap:wrap; gap:.3rem}
.chip{
  font-family:var(--font-mono); font-size:.63rem; letter-spacing:.05em; color:var(--muted);
  border:var(--rule); border-radius:2px; padding:.16rem .4rem; background:var(--panel-2);
}

/* ── slide 10: the map ─────────────────────────────────────────────────── */
.mapbox{position:relative; border:var(--rule); border-radius:3px; background:#081019; overflow:hidden}
.mapbox svg{display:block; width:100%; height:auto}
.mapctl{display:flex; flex-wrap:wrap; gap:.3rem; align-items:center}
.tgl{
  font-family:var(--font-mono); font-size:.62rem; letter-spacing:.1em; text-transform:uppercase;
  background:var(--panel-2); color:var(--muted); border:var(--rule); border-radius:2px;
  padding:.22rem .5rem; cursor:pointer; transition:.2s var(--ease);
}
.tgl[aria-pressed="true"]{color:var(--accent); border-color:rgba(79,195,209,.5); background:var(--accent-dim)}
.maplegend{display:flex; flex-wrap:wrap; gap:.2rem .9rem; font-family:var(--font-mono); font-size:.6rem; color:var(--muted)}
.maplegend i{display:inline-block; width:.85rem; height:2px; margin-right:.35rem; vertical-align:middle}
.scrub{width:100%; accent-color:var(--accent); background:transparent}
.mapover{
  position:absolute; left:.6rem; bottom:.6rem; background:rgba(10,22,32,.86);
  border:var(--rule); border-radius:2px; padding:.4rem .6rem;
  font-family:var(--font-mono); font-size:.63rem; color:var(--muted); backdrop-filter:blur(3px);
}
.mapover b{color:var(--accent); font-weight:400}

/* ── charts ────────────────────────────────────────────────────────────── */
.chart{width:100%; height:auto; display:block; overflow:visible}
.ax{font-family:var(--font-mono); font-size:8px; fill:#85a0ab}
.gridline{stroke:rgba(34,59,77,.55); stroke-width:1}

/* ── slide 12: the chamber ─────────────────────────────────────────────── */
.seats{display:block; width:100%; height:auto}
.divis{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem}
.divi{border:var(--rule); border-radius:3px; padding:.7rem .8rem; background:var(--panel); border-top:2px solid var(--ok)}
.divi.lost{border-top-color:var(--bad)}
.divi-r{font-family:var(--font-mono); font-size:clamp(1.3rem,2.6vw,1.9rem); font-variant-numeric:tabular-nums; line-height:1}
.divi-v{font-family:var(--font-mono); font-size:.62rem; letter-spacing:.16em; text-transform:uppercase; margin-top:.3rem}
@media(max-width:700px){.divis{grid-template-columns:minmax(0,1fr)}}

/* ── slide 13: press ───────────────────────────────────────────────────── */
.press{border:var(--rule); border-radius:3px; background:var(--panel); padding:.7rem .8rem; position:relative; display:flex; flex-direction:column; gap:.3rem}
.press-outlet{font-family:var(--font-mono); font-size:.6rem; letter-spacing:.13em; text-transform:uppercase; color:var(--stamp)}
.press-h{font-family:var(--font-display); font-size:1rem; line-height:1.22; text-wrap:balance}
.press-s{font-size:.76rem; color:var(--muted); line-height:1.45}
.press-mark{
  position:absolute; top:.55rem; right:.6rem; font-family:var(--font-mono); font-size:.52rem;
  letter-spacing:.18em; color:rgba(226,161,61,.55); border:1px solid rgba(226,161,61,.3);
  padding:.05rem .25rem; border-radius:2px;
}
.bar-row{display:grid; grid-template-columns:8.5rem minmax(0,1fr) 3.2rem; align-items:center; gap:.5rem; font-size:.75rem}
.bar-track{height:.5rem; background:rgba(34,59,77,.5); border-radius:1px; overflow:hidden; display:flex}
.bar-neg{background:var(--bad); height:100%} .bar-pos{background:var(--ok); height:100%}

/* ── slide 15 + appendix ───────────────────────────────────────────────── */
.close-lines{display:flex; flex-direction:column; gap:1.05rem}
.close-lines p{font-family:var(--font-display); font-size:clamp(1.05rem,2vw,1.5rem); line-height:1.32; color:var(--muted); max-width:46ch}
.close-lines p.on{color:var(--text)}
.refs{columns:2; column-gap:2.4rem; font-size:.72rem; color:var(--muted); line-height:1.5}
.refs li{break-inside:avoid; margin-bottom:.5rem}
@media(max-width:820px){.refs{columns:1}}
.appendix{min-height:auto; padding-bottom:5rem}

@media(prefers-reduced-motion:reduce){
  html,.deck{scroll-behavior:auto}
  .stage{opacity:1; transform:none; transition:none}
  .rail-fill{transition:none}
}
"""


# ═══ slides 01–06: the case ═══════════════════════════════════════════════
def s01():
    rows = "".join(
        f'<div class="case"><div><div class="case-where">{e(w)}</div>'
        f'<div class="case-when">{e(y)}</div></div>'
        f'<div class="case-what">{e(t)}</div></div>' for w, y, t in CASES)
    return f"""
<section class="slide" id="s1" data-title="Policy is tested on real people">
  <div class="wrap stack g3">
    <div class="stack g2">
      <p class="eyebrow">01 — Policy is tested on real people</p>
      <h1>The Dutch government resigned.<br>26,000 families were already ruined.</h1>
    </div>
    <div>{rows}</div>
    <p class="pull">Five continents. Five decades of policy technique. The same method:
      <em>enact it, then find out.</em></p>
  </div>
</section>"""


def s02():
    data = ["National infrastructure topology and load",
            "Citizen-level tax, benefit and health administrative records",
            "Security and border systems",
            "Utility, grid and telecom operational data",
            "Commercially confidential enterprise filings"]
    items = "".join(f'<div class="ds"><i></i>{e(d)}</div>' for d in data)
    return f"""
<section class="slide" id="s2" data-title="The data cannot leave the building">
  <div class="wrap stack g3">
    <div class="stack g2">
      <p class="eyebrow">02 — Why it happens, reason one</p>
      <h2>The data that decides your life is not allowed in the room.</h2>
      <p class="lede">Every country's most decision-relevant data is legally immobile — classified,
        privacy-protected or sovereign. It cannot be exported to an external advisor.</p>
    </div>
    <div class="perim">
      <div class="vault">
        <div class="vault-label">Inside the perimeter</div>
        {items}
      </div>
      <div class="barred"><span>barred</span></div>
      <div class="outsider">
        <div class="vault-label" style="color:var(--muted)">Outside it</div>
        <p style="font-size:.87rem">An external advisor with published aggregates, national averages
          and inference — modelling <i>around the hole</i>.</p>
      </div>
    </div>
    <p class="pull">The consultant is not failing. The consultant is <em>barred</em>.</p>
  </div>
</section>"""


def s03():
    steps = [("01", "Brief", "weeks"), ("02", "Procure", "2–6 months"), ("03", "Scope", "weeks"),
             ("04", "Collect", "months"), ("05", "Single-domain report", "months"),
             ("06", "Review → re-brief", "and around again")]
    cells = "".join(
        f'<div class="loopstep"><div class="k">{k}</div><div class="v">{e(v)}</div>'
        f'<div class="w">{e(w)}</div></div>' for k, v, w in steps)
    tiles = [("Global consulting spend", "~US$85bn", "per year"),
             ("UK central government", "£1.36bn", "2022–23"),
             ("Officials rating the work valuable", "86%", "NAO"),
             ("Revolutions a government can afford", "One", "per question")]
    tl = "".join(
        f'<div class="tile{" tile-stamp" if i == 3 else ""}"><div class="tile-k">{e(k)}</div>'
        f'<div class="tile-v sm">{e(v)}</div><div class="tile-u">{e(u)}</div></div>'
        for i, (k, v, u) in enumerate(tiles))
    cons = ["One report per question, because a second costs another year and another million.",
            "Four reports, four disciplines, zero interaction modelled — the second-order effect lives in the gap between them.",
            "A national elasticity applied to one specific street network."]
    cl = "".join(f'<li>{e(c)}</li>' for c in cons)
    return f"""
<section class="slide" id="s3" data-title="The loop">
  <div class="wrap stack g3">
    <div class="stack g2">
      <p class="eyebrow">03 — Why it happens, reason two</p>
      <h2>The loop takes 6–18 months per revolution.</h2>
    </div>
    <div class="loopgrid">{cells}</div>
    <div class="cols c4">{tl}</div>
    <ul class="lede" style="padding-left:1.1rem; display:flex; flex-direction:column; gap:.4rem">{cl}</ul>
    <p class="pull">You cannot iterate at £1.36 billion a cycle. So nobody iterates.
      <em>The first draft ships.</em></p>
  </div>
</section>"""


def s04():
    return """
<section class="slide" id="s4" data-title="The evidence exists. It is not being used.">
  <div class="wrap stack g3">
    <div class="stack g2">
      <p class="eyebrow">04 — Two things that are both true</p>
      <h2>The evidence exists. It isn't being used.</h2>
    </div>
    <div class="cols c2">
      <div class="panel panel-2" style="opacity:.82">
        <div class="panel-head"><span class="panel-title">Nobody checks afterwards</span>
          <span class="tag">Government practice</span></div>
        <div class="stack g2">
          <div class="tile"><div class="tile-k">Countries with any ex-post review of legislation</div>
            <div class="tile-v">14<span style="color:var(--muted)"> / 32</span></div>
            <div class="tile-u">OECD, Government at a Glance 2025</div></div>
          <div class="tile"><div class="tile-k">EU member states sharing evaluation results</div>
            <div class="tile-v">&lt;15%</div><div class="tile-u">European Court of Auditors, SR 16/2018</div></div>
          <p class="lede" style="font-size:.85rem">So the failure is never fed back. The next policy
            starts from the same place.</p>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head"><span class="panel-title">Prediction is a solved-enough problem</span>
          <span class="tag tag-sim">State of the art</span></div>
        <div class="stack g2">
          <div class="tile tile-accent"><div class="tile-k">GraphCast vs. the best operational weather system</div>
            <div class="tile-v">90%</div><div class="tile-u">of 1,380 verification targets — Lam et al., Science, 2023</div></div>
          <div class="tile tile-accent"><div class="tile-k">10-day global forecast, one machine</div>
            <div class="tile-v">&lt;60 s</div><div class="tile-u">against hours on a supercomputer</div></div>
          <p class="lede" style="font-size:.85rem">Machine learning now outperforms decades of
            physics-based simulation in the single hardest forecasting domain there is.</p>
        </div>
      </div>
    </div>
    <p class="pull">Weather gets a supercomputer and a neural network. Policy gets a press conference.
      Decisions that bind millions are still made on narrative, anecdote and instinct — not because
      better tools don't exist, but because <em>nobody has pointed them at government</em>.</p>
  </div>
</section>"""


def s05():
    rows = "".join(f'<div class="ind"><b>{e(k)}</b><span>{e(v)}</span></div>' for k, v in INDUSTRIES)
    return f"""
<section class="slide" id="s5" data-title="Everyone else simulates first">
  <div class="wrap wrap-wide stack g3">
    <div class="stack g1">
      <p class="eyebrow">05 — {len(INDUSTRIES)} industries that rehearse</p>
      <h2>Everyone else simulates first.</h2>
    </div>
    <div class="inds">{rows}</div>
    <div style="display:flex; align-items:baseline; gap:1.4rem; flex-wrap:wrap; border-top:1px solid var(--border-strong); padding-top:1rem">
      <h1 style="font-size:clamp(2rem,4.5vw,3.4rem)">Government.</h1>
      <p class="pull" style="margin-bottom:.2rem">The sector that spends the most and
        <em>rehearses the least</em>.</p>
    </div>
  </div>
</section>"""


def s06():
    rows = ""
    for name, lat, lon, when in FAILURE_POINTS:
        here = when == "modelled here"
        col = "var(--accent)" if here else "var(--stamp)"
        rows += (f'<tr><td style="color:{col}">◆</td><td>{e(name)}</td>'
                 f'<td class="n">{lat:+.2f}</td><td class="n">{lon:+.2f}</td>'
                 f'<td class="n" style="color:var(--muted)">{e(when)}</td></tr>')
    sdg = "".join(f'<div class="sdg"><b>{n}</b><div class="t">{e(t)}</div>'
                  f'<div class="m">{e(m)}</div></div>' for n, t, m in SDGS)
    return f"""
<section class="slide" id="s6" data-title="This is not a local problem">
  <div class="wrap stack g3">
    <div class="stack g2">
      <p class="eyebrow">06 — First principles</p>
      <h2>This is not a local problem.</h2>
    </div>
    <div class="cols c2">
      <div class="stack g2">
        <ol class="lede" style="padding-left:1.1rem; display:flex; flex-direction:column; gap:.5rem; font-size:.92rem">
          <li>A policy is an irreversible intervention in a complex adaptive system.</li>
          <li>Every government makes them with partial data, one discipline at a time, and no rehearsal.</li>
          <li>Every government has the data required — it just cannot leave the building.</li>
        </ol>
        <div class="panel panel-2">
          <div class="panel-head"><span class="panel-title">Where the first slide happened</span>
            <span class="tag tag-obs">Observed</span></div>
          <table>
            <thead><tr><th></th><th>Jurisdiction</th><th class="n">Lat</th><th class="n">Lon</th><th class="n">Year</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
          <p class="kicker" style="text-transform:none; letter-spacing:0; font-size:.72rem; margin-top:.6rem">
            Five continents, one method. The last row is the city this build models —
            and every number in it lands on a coordinate like these.</p>
        </div>
      </div>
      <div class="stack g1">{sdg}</div>
    </div>
    <p class="pull">An international failure mode. A local blast radius.
      <em>Same fix, any jurisdiction.</em></p>
  </div>
</section>"""


# ═══ slides 07–14: the instrument ═════════════════════════════════════════
STAGE_COPY = {
    "compile": ("Policy compiled", "Prose structured into an auditable Policy DSL with explicit parameters."),
    "datasets": ("Datasets loaded", "Auckland OSM geometry, the loop-detector sensor network and the OD matrix, in parallel."),
    "models": ("Models loaded", "The regressor bake-off and the LSTM, with their held-out scores from the registry."),
    "forecast": ("Prediction generated", "Twelve five-minute steps of link speed, from a twelve-step observed history."),
    "simulate": ("Simulation complete", "World A, World B and Δ(B−A) across every Time-Machine checkpoint."),
    "public": ("Public reaction modelled", "Cohort opinion by segment, driven by the simulated distributional result."),
    "division": ("Division simulated", "A whipped vote over the real 2023 House, party by party."),
    "media": ("Coverage generated", "Headlines across the spectrum, each grounded in a simulated figure."),
}


def src_line(*bits):
    return '<div class="src">' + "".join(f"<span>{b}</span>" for b in bits) + "</div>"


def s07():
    rows = ""
    for i, st in enumerate(D["stages"], 1):
        lbl, det = STAGE_COPY[st["id"]]
        rows += (f'<div class="stage" data-i="{i}">'
                 f'<span class="stage-i">{i:02d}</span>'
                 f'<span class="stage-l"><b>{e(lbl)}</b><i>{e(det)}</i></span>'
                 f'<span class="stage-t">{st["ms"]} ms</span>'
                 f'<span class="stage-b">{num(st["bytes"] / 1024, 1)} KB</span></div>')
    kb = D["total_bytes"] / 1024
    return f"""
<section class="slide" id="s7" data-title="GOV SIM">
  <div class="wrap wrap-wide stack g2">
    <div class="stack g1">
      <p class="eyebrow">07 — GOV SIM</p>
      <h2>Write a policy in plain English. Watch ten years happen.</h2>
    </div>
    <div class="cols c32">
      <div class="console" id="console">
        <div class="console-top">
          <span class="panel-title">Run console — live engine, localhost:8000</span>
          <span class="tag tag-obs">Measured, not animated</span>
        </div>
        <div class="prompt"><b>Policy prompt →</b> {e(D["prompt"])}</div>
        <div class="stages">{rows}</div>
        <div class="console-foot">
          <span class="kicker">8 / 8 stages complete</span>
          <span class="mono" style="font-size:.72rem">
            <b class="cy">{D["total_ms"]} ms</b> engine time · {num(kb, 1)} KB over the wire ·
            {D["capabilities"]["routes"]} routes available</span>
        </div>
      </div>
      <div class="stack g2">
        <p class="lede" style="font-size:.88rem">Eight dependent stages across a compiler, a model
          registry, an LSTM, an agent-based engine, an opinion model, the House and a newsroom.
          No queue, no callback, no procurement.</p>
        <div class="tile tile-accent">
          <div class="tile-k">Time to first answer</div>
          <div class="tile-v" style="font-size:clamp(1.1rem,1.9vw,1.5rem)">6–18 months → {(D["total_ms"] / 1000):.2f} s</div>
          <div class="tile-u">measured wall-clock across the eight calls, this machine</div>
        </div>
        <p class="pull" style="font-size:clamp(1rem,1.6vw,1.3rem)">The political reaction is
          <em>inside</em> the model, not a paragraph at the end of a report.</p>
        <p class="kicker" style="text-transform:none; letter-spacing:0; font-size:.75rem">
          Every row is a real HTTP call. The byte counts are what came over the wire; the
          milliseconds are measured at the call site. Every run is hashed and reproducible.</p>
      </div>
    </div>
    {src_line("<b>POST</b> /policy/compile → /simulate → /public → /parliament/nz/division → /media",
              "timings: <b>perf_counter</b> at the call site",
              "bytes: response body length")}
  </div>
</section>"""


def s08():
    r = D["registry"]["counts"]
    f = D["fabric"]["counts"]
    c = D["capabilities"]
    bands = [
        ("Interface", "<b>Next.js 14 · TypeScript · deck.gl 9 · MapLibre</b> — extruded building "
         "footprints on the real street network. The ten-year projection is computed in-browser, so "
         "scrubbing is instant and the demo survives the backend being down."),
        ("Engine", f"<b>Python 3.11 · FastAPI · {c['routes']} routes across {c['areas']} areas</b> — "
         "compiler · baseline · synthetic population · microsim · spatial assignment · economy · "
         "system dynamics · time-series · analogues · ensemble · uncertainty · stress · opinion · "
         "diffusion · parliament · media · SDG · optimiser · backtest · evidence · registry."),
        ("Models", f"<b>scikit-learn · PyTorch · CPU</b> — LSTM 2×64, 12 horizons at once "
         f"(R² {D['ml']['lstm'][0]['r2']:.3f} at +5 min); nine classical regressors, best "
         f"{[m for m in D['ml']['regressors'] if m['best']][0]['name']} at R² "
         f"{[m for m in D['ml']['regressors'] if m['best']][0]['r2']:.3f} at +30 min; isolation "
         "forest for incident anomalies; random-forest response surface over hour × weekday."),
        ("Context", f"<b>MongoDB, local, read and written</b> — sensor_readings · ml_models · runs · "
         f"policies. {r['models']} registered models, {r['documented_assumptions']} documented "
         f"assumptions read live from the code so values cannot drift. The LLM runs inside the "
         f"perimeter. Nothing crosses the border."),
    ]
    bandhtml = ""
    for i, (k, v) in enumerate(bands):
        bandhtml += f'<div class="band"><div class="band-k">{e(k)}</div><div class="band-v">{v}</div></div>'
        if i < len(bands) - 1:
            bandhtml += '<div class="band-arrow">▲</div>'
    sources = ["OpenStreetMap via Overpass — roads, buildings, land use, coastline",
               "GTFS — transit feeds from ~10,000 agencies worldwide",
               "World Bank · OECD · UN — economic and demographic baselines",
               "Copernicus · NASA Earthdata — emissions, flood and heat exposure",
               "National census OD schemas — home → work flows by mode",
               "Historical election returns, wherever they are published"]
    srows = "".join(f'<div class="ds"><i></i>{e(s)}</div>' for s in sources)
    return f"""
<section class="slide" id="s8" data-title="The stack">
  <div class="wrap stack g3">
    <div class="stack g1">
      <p class="eyebrow">08 — The stack</p>
      <h2>Four layers. The numbers only ever come from the bottom three.</h2>
    </div>
    <div class="cols c32">
      <div class="stack g0" style="gap:.3rem">{bandhtml}</div>
      <div class="stack g2">
        <div class="cols c2" style="gap:.4rem">
          <div class="tile tile-accent"><div class="tile-k">HTTP routes</div><div class="tile-v">{c['routes']}</div><div class="tile-u">{c['get']} GET · {c['post']} POST</div></div>
          <div class="tile tile-accent"><div class="tile-k">Registered models</div><div class="tile-v">{r['models']}</div><div class="tile-u">{r['numeric_models']} numeric · {r['deterministic_models']} deterministic</div></div>
          <div class="tile tile-stamp"><div class="tile-k">Documented assumptions</div><div class="tile-v">{r['documented_assumptions']}</div><div class="tile-u">read from source, live</div></div>
          <div class="tile"><div class="tile-k">Models where an LLM touches a number</div><div class="tile-v ok">{r['models_touching_numbers_with_llm']}</div><div class="tile-u">{r['guardrails_holding']} / {r['guardrails_total']} guardrails holding</div></div>
        </div>
        <div class="panel panel-2">
          <div class="panel-head"><span class="panel-title">Same pipeline, any country</span>
            <span class="tag tag-obs">Live sources</span></div>
          {srows}
        </div>
      </div>
    </div>
    <p class="pull">LLMs parse policy, argue, red-team and write the press.
      <em>They never produce a number.</em></p>
    {src_line("<b>GET</b> /capabilities · /registry · /data-fabric",
              f"app v{e(D['registry']['app_version'])}",
              f"{f['datasets']} datasets · {num(f['records_total'])} records · {f['formats_native']} native formats",
              "generated from live route and parameter introspection")}
  </div>
</section>"""


def s09():
    rows = [("Datasets held together", "1 per report", "all of them, one store"),
            ("Disciplines in the answer", "1", "7 engines, simultaneously"),
            ("Sensitive data included", "no — barred", "yes — never leaves"),
            ("Time to first answer", "6–18 months", f"{(D['total_ms'] / 1000):.2f} s measured"),
            ("Cost per additional scenario", "another contract", "zero"),
            ("Scenarios a government can afford", "1", "unlimited"),
            ("Political outcome modelled", "no", "yes")]
    tr = "".join(f'<tr><td>{e(a)}</td><td class="mono" style="color:var(--muted)">{e(b)}</td>'
                 f'<td class="mono cy">{e(c)}</td></tr>' for a, b, c in rows)
    return f"""
<section class="slide" id="s9" data-title="Context is the speed-up">
  <div class="wrap stack g3">
    <div class="stack g1">
      <p class="eyebrow">09 — Context is the speed-up</p>
      <h2>&ldquo;What happens if we congestion-charge the city centre?&rdquo;</h2>
      <p class="lede">The same question, asked of the two available methods.</p>
    </div>
    <div class="panel scrollx">
      <table>
        <thead><tr><th></th><th>Conventional</th><th>AI-native</th></tr></thead>
        <tbody>{tr}</tbody>
      </table>
    </div>
    <div class="cols c2">
      <p class="lede" style="font-size:.86rem">Cross-industry benchmark: unifying context before
        committing cuts development time by up to <b class="cy">50%</b> and prototype cost by
        <b class="cy">40%</b> (McKinsey, on digital twins). The gain has never come from better
        experts — it comes from putting the whole system in one place and running it before committing.</p>
      <p class="pull">A government that can run a thousand scenarios <em>does not need to be right
        the first time</em>.</p>
    </div>
    {src_line("Conventional column: NAO / OECD consulting-cycle data",
              "AI-native column: <b>measured</b> GOV SIM run times, this build",
              "a derived comparison, not a single published study")}
  </div>
</section>"""


def s10():
    W, H = MAP["w"], MAP["h"]
    V = MAP["view"]
    R = MAP["roads"]
    road_style = [("service", "#20394b", .4), ("local", "#31566c", .55),
                  ("collector", "#3d7c95", .8), ("arterial", "#4fc3d1", 1.1),
                  ("motorway", "#8fe3ee", 1.7)]
    roads_svg = "".join(
        f'<path d="{R[c]}" fill="none" stroke="{col}" stroke-width="{w}" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="{.85 if c != "service" else .55}"/>'
        for c, col, w in road_style if c in R)
    # the 144-link assignment network, coloured by the real flow change on it
    arcs = ""
    for a in MAP["arcs"]:
        drop = a["delta"]
        mag = min(1.0, abs(drop) / 800)
        col = "#ef6b57" if drop > 0 else "#5cc98a"
        arcs += (f'<line x1="{a["x1"]}" y1="{a["y1"]}" x2="{a["x2"]}" y2="{a["y2"]}" '
                 f'stroke="{col}" stroke-width="{1.5 + mag * 6:.1f}" stroke-opacity="{.25 + mag * .5:.2f}" '
                 f'stroke-linecap="round"><title>{e(a["id"])} · {e(a["cls"])} · flow '
                 f'{a["flow_a"]:.0f} → {a["flow_b"]:.0f} veh/hr</title></line>')
    net = "".join(
        f'<line x1="{l["x1"]}" y1="{l["y1"]}" x2="{l["x2"]}" y2="{l["y2"]}" '
        f'stroke="#2c4a5f" stroke-width=".8" stroke-opacity=".5"/>' for l in MAP["net"])
    # the five zones with the largest modelled CO2 fall, labelled where they are
    drops = ""
    for d in MAP["drops"]:
        z = MAP["zone_centroids"].get(d["zone_id"])
        if not z:
            continue
        drops += (f'<g><circle cx="{z["x"]}" cy="{z["y"]}" r="16" fill="#5cc98a" fill-opacity=".14"/>'
                  f'<circle cx="{z["x"]}" cy="{z["y"]}" r="3" fill="#5cc98a"/>'
                  f'<text class="ax" x="{z["x"] + 21}" y="{z["y"] + 3}" fill="#5cc98a">'
                  f'{d["delta_pct"]:+.1f}% CO₂</text></g>')
    osm = D["osm"]
    sp = D["spatial"]
    return f"""
<section class="slide" id="s10" data-title="See it on the ground">
  <div class="wrap wrap-wide stack g2">
    <div class="stack g1">
      <p class="eyebrow">10 — See it on the ground</p>
      <h2>Every number on this map is attached to a coordinate.</h2>
    </div>
    <div class="cols c32">
      <div class="stack g1">
        <div class="mapctl">
          <button class="tgl" aria-pressed="true" data-layer="streets">Streets</button>
          <button class="tgl" aria-pressed="true" data-layer="cordon">Cordon</button>
          <button class="tgl" aria-pressed="false" data-layer="network">Model network</button>
          <button class="tgl" aria-pressed="false" data-layer="flows">Assignment Δflow</button>
          <button class="tgl" aria-pressed="false" data-layer="co2">CO₂ falls</button>
        </div>
        <div class="mapbox">
          <svg viewBox="{V['x']} {V['y']} {V['w']} {V['h']}" role="img"
               aria-label="Auckland central: real OpenStreetMap street network with the congestion-charge cordon and the modelled change in peak-hour flow">
            <rect x="{V['x']}" y="{V['y']}" width="{V['w']}" height="{V['h']}" fill="#081019"/>
            <path d="{MAP['parks']}" fill="#12291f" fill-opacity=".55" stroke="none"/>
            <path d="{MAP['water']}" fill="#0b2231" stroke="#14384a" stroke-width=".8"/>
            <g id="lyr-streets">{roads_svg}</g>
            <g id="lyr-network" style="display:none">{net}</g>
            <g id="lyr-flows" style="display:none">{arcs}</g>
            <g id="lyr-cordon">
              <path d="{MAP['cordon']}" fill="rgba(226,161,61,.07)" stroke="#e2a13d"
                    stroke-width="2" stroke-dasharray="7 4"/>
            </g>
            <g id="lyr-co2" style="display:none">{drops}</g>
          </svg>
          <div class="mapover">
            Auckland CBD · {osm['radius_km']} km radius · fetched {e(osm['fetched_at'][:10])}<br>
            <b>{num(osm['frontend']['roads'])}</b> street links ·
            <b>{num(osm['frontend']['buildings'])}</b> building footprints ·
            <b>{num(osm['frontend']['water'])}</b> water features
          </div>
        </div>
        <div class="maplegend">
          <span><i style="background:#7fdbe6"></i>motorway</span>
          <span><i style="background:#4fc3d1"></i>arterial</span>
          <span><i style="background:#356d84"></i>collector</span>
          <span><i style="background:#274a5e"></i>local</span>
          <span><i style="background:#1b3040"></i>service</span>
          <span><i style="background:#e2a13d"></i>charge cordon</span>
          <span><i style="background:#5cc98a"></i>flow falls</span>
          <span><i style="background:#ef6b57"></i>flow rises</span>
          <span style="color:var(--muted)">assignment runs on a 144-link abstraction of this network</span>
        </div>
      </div>
      <div class="stack g2">
        <div class="panel">
          <div class="panel-head"><span class="panel-title">Peak-hour assignment</span>
            <span class="tag tag-sim">Simulated</span></div>
          <table>
            <thead><tr><th>Network</th><th class="n">World A</th><th class="n">World B</th><th class="n">Δ</th></tr></thead>
            <tbody>
              <tr><td>Cordon inflow, veh/hr</td><td class="n">{num(sp['world_a']['cordon_inflow_veh_per_hr'])}</td><td class="n">{num(sp['world_b']['cordon_inflow_veh_per_hr'])}</td><td class="n ok">{sp['cordon_inflow_delta_pct']:+.1f}%</td></tr>
              <tr><td>Vehicle hours</td><td class="n">{num(sp['world_a']['total_vehicle_hours'])}</td><td class="n">{num(sp['world_b']['total_vehicle_hours'])}</td><td class="n ok">{sp['vehicle_hours_delta_pct']:+.1f}%</td></tr>
              <tr><td>Mean volume / capacity</td><td class="n">{sp['world_a']['mean_vc']:.3f}</td><td class="n">{sp['world_b']['mean_vc']:.3f}</td><td class="n ok">−{(1 - sp['world_b']['mean_vc'] / sp['world_a']['mean_vc']) * 100:.0f}%</td></tr>
              <tr><td>Mean speed, km/h</td><td class="n">{sp['world_a']['mean_speed_kmh']:.1f}</td><td class="n">{sp['world_b']['mean_speed_kmh']:.1f}</td><td class="n ok">+{sp['world_b']['mean_speed_kmh'] - sp['world_a']['mean_speed_kmh']:.1f}</td></tr>
              <tr><td>Road CO₂ in cordon, kg/hr</td><td class="n">{num(sp['pollution']['cbd_a'])}</td><td class="n">{num(sp['pollution']['cbd_b'])}</td><td class="n ok">{sp['pollution']['cbd_delta_pct']:+.1f}%</td></tr>
            </tbody>
          </table>
          <p class="kicker" style="margin-top:.6rem; text-transform:none; letter-spacing:0; font-size:.72rem; color:var(--muted)">
            {e(sp['pollution']['displacement_note'])}</p>
        </div>
        <div class="panel panel-2">
          <div class="panel-head"><span class="panel-title">Drag the timeline —
            <span class="cy" id="scrub-at">10 years</span></span>
            <span class="tag tag-sim">Δ(B−A)</span></div>
          <input type="range" class="scrub" id="scrub" min="0" max="{len(D['checkpoints']) - 1}"
                 value="{len(D['checkpoints']) - 1}" step="1" aria-label="Simulation horizon">
          <div style="display:flex; justify-content:space-between" class="kicker">
            <span>T0 · implementation</span><span>10 years</span>
          </div>
          <div class="stack g0" id="scrub-vals" style="margin-top:.6rem"></div>
        </div>
      </div>
    </div>
    {src_line("Geometry: <b>OpenStreetMap</b> via Overpass, ODbL 1.0 — " + e(osm['source']['endpoint']),
              f"fetch took {osm['elapsed_seconds']}s for {num(osm['counts']['roads'])} roads / {num(osm['counts']['buildings'])} buildings",
              "Flows: <b>POST</b> /spatial — MSA user-equilibrium, BPR volume-delay, 25 iterations")}
  </div>
</section>"""


def s11():
    ml = D["ml"]
    hz = ml["lstm"]
    W, H, PL, PB, PT = 460, 220, 34, 26, 12
    xs = lambda i: PL + i / (len(hz) - 1) * (W - PL - 8)
    ys = lambda r: PT + (1 - (r - 0.5) / 0.5) * (H - PT - PB)
    line = "M" + "L".join(f"{xs(i):.1f} {ys(h['r2']):.1f}" for i, h in enumerate(hz))
    area = line + f"L{xs(len(hz) - 1):.1f} {H - PB} L{xs(0):.1f} {H - PB} Z"
    grid, ticks = "", ""
    for r in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        y = ys(r)
        grid += f'<line class="gridline" x1="{PL}" y1="{y:.1f}" x2="{W - 8}" y2="{y:.1f}"/>'
        ticks += f'<text class="ax" x="{PL - 6}" y="{y + 3:.1f}" text-anchor="end">{r:.1f}</text>'
    for i, h in enumerate(hz):
        if h["horizon_min"] % 15 == 0 or i == 0:
            ticks += (f'<text class="ax" x="{xs(i):.1f}" y="{H - PB + 13}" '
                      f'text-anchor="middle">+{h["horizon_min"]}m</text>')
    dots = "".join(f'<circle cx="{xs(i):.1f}" cy="{ys(h["r2"]):.1f}" r="2.4" fill="#4fc3d1">'
                   f'<title>+{h["horizon_min"]} min · R² {h["r2"]:.4f} · MAE {h["mae"]:.2f} mph</title></circle>'
                   for i, h in enumerate(hz))

    dec = D["microsim"]["by_income_decile"]
    mx = max(d["mean_burden_pct_income"] for d in dec)
    bars = ""
    for d in dec:
        w = d["mean_burden_pct_income"] / mx * 100
        nm = d["group"].replace(" (lowest income)", " ·low").replace(" (highest income)", " ·high")
        bars += (f'<div class="bar-row"><span style="color:var(--muted)">{e(nm)}</span>'
                 f'<span class="bar-track"><i class="bar-neg" style="width:{w:.1f}%; background:'
                 f'{"#e2a13d" if d is dec[0] else "#4fc3d1"}"></i></span>'
                 f'<span class="mono" style="text-align:right">{d["mean_burden_pct_income"]:.3f}%</span></div>')

    an = D["analogues"]
    arows = "".join(
        f'<tr><td>{e(c["name"])}</td><td class="n">{c["year"]}</td>'
        f'<td class="n">{c["did_effect_pct"]:+.0f}%</td>'
        f'<td class="n">{c["transferability_score"]:.3f}</td>'
        f'<td class="n" style="color:{"var(--muted)" if not c["applicable"] else "var(--accent)"}">'
        f'{"excluded" if not c["applicable"] else f"{c['pool_weight']:.3f}"}</td></tr>'
        for c in an["cases"])

    engines = ["Spatial assignment", "Microsimulation", "Economic spillover", "System dynamics",
               "Time-series baseline", "Historical analogues", "Opinion diffusion"]
    chips = "".join(f'<span class="chip">{e(x)}</span>' for x in engines)
    return f"""
<section class="slide" id="s11" data-title="What it can actually predict">
  <div class="wrap wrap-wide stack g2">
    <div class="stack g1">
      <p class="eyebrow">11 — What it can actually predict</p>
      <h2>Seven engines, one geometry, and a decay curve we plot rather than hide.</h2>
      <div class="chips">{chips}</div>
    </div>
    <div class="cols c3">
      <div class="panel">
        <div class="panel-head"><span class="panel-title">LSTM skill vs. horizon</span>
          <span class="tag tag-obs">Held-out test</span></div>
        <svg viewBox="0 0 {W} {H}" class="chart" role="img"
             aria-label="LSTM R-squared decaying from {hz[0]['r2']:.3f} at +5 minutes to {hz[-1]['r2']:.3f} at +60 minutes">
          <defs><linearGradient id="lg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#4fc3d1" stop-opacity=".28"/>
            <stop offset="1" stop-color="#4fc3d1" stop-opacity="0"/></linearGradient></defs>
          {grid}
          <path d="{area}" fill="url(#lg)"/>
          <path d="{line}" fill="none" stroke="#4fc3d1" stroke-width="1.8"/>
          {dots}{ticks}
          <text class="ax" x="{PL}" y="{H - 4}" fill="#85a0ab">prediction horizon →</text>
          <text class="ax" x="{PL - 6}" y="{PT - 3}" text-anchor="end" fill="#85a0ab">R²</text>
        </svg>
        <div class="cols c2" style="gap:.4rem; margin-top:.5rem">
          <div class="tile tile-accent"><div class="tile-k">at +5 min</div>
            <div class="tile-v sm">{hz[0]['r2']:.3f}</div><div class="tile-u">MAE {hz[0]['mae']:.2f} mph</div></div>
          <div class="tile"><div class="tile-k">at +60 min</div>
            <div class="tile-v sm">{hz[-1]['r2']:.3f}</div><div class="tile-u">MAE {hz[-1]['mae']:.2f} mph</div></div>
        </div>
        <p class="kicker" style="text-transform:none; letter-spacing:0; font-size:.7rem; margin-top:.5rem">
          {ml['arch']['layers']}×{ml['arch']['hidden_size']} LSTM, {num(ml['arch']['params'])} parameters,
          {ml['dataset']['sensors']} sensors, {num(ml['dataset']['train_rows_sampled'])} training rows.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><span class="panel-title">Who pays, by income decile</span>
          <span class="tag tag-sim">Microsimulation</span></div>
        <div class="stack g0">{bars}</div>
        <div class="cols c2" style="gap:.4rem; margin-top:.7rem">
          <div class="tile tile-stamp"><div class="tile-k">Regressivity ratio</div>
            <div class="tile-v sm">{D['microsim']['regressivity_ratio']:.2f}×</div>
            <div class="tile-u">decile 1 burden ÷ decile 10</div></div>
          <div class="tile"><div class="tile-k">Stated cap</div>
            <div class="tile-v sm ok">{D['microsim']['constraint_check']['modelled_low_income_burden_pct']:.3f}%</div>
            <div class="tile-u">within the {D['microsim']['constraint_check']['cap_pct']:.0f}% constraint</div></div>
        </div>
        <p class="kicker" style="text-transform:none; letter-spacing:0; font-size:.7rem; margin-top:.5rem">
          {num(D['microsim']['commuters'])} synthetic commuters · {num(D['microsim']['winners'])} better off ·
          {num(D['microsim']['losers'])} worse off · worst hit: {e(D['microsim']['worst_hit'])}.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><span class="panel-title">Historical analogues</span>
          <span class="tag tag-obs">Observed → scored</span></div>
        <div class="scrollx"><table>
          <thead><tr><th>Case</th><th class="n">Year</th><th class="n">DiD</th><th class="n">Transfer</th><th class="n">Weight</th></tr></thead>
          <tbody>{arows}</tbody>
        </table></div>
        <div class="tile tile-accent" style="margin-top:.6rem">
          <div class="tile-k">Pooled estimate — {e(an['metric_label'])}, {e(an['horizon_label'])}</div>
          <div class="tile-v sm">{an['estimated_effect_pct']:+.1f}%</div>
          <div class="tile-u">CI {an['ci_low_pct']:+.1f}% to {an['ci_high_pct']:+.1f}% ·
            quality {e(an['analogue_quality'])} · transferability {an['transferability_score']:.3f}</div>
        </div>
      </div>
    </div>
    {src_line("<b>GET</b> /ml/models — scores read from the trained registry, not asserted",
              "<b>POST</b> /microsim · /analogues",
              "each analogue scored for transferability to <b>this</b> geography, and one is excluded outright")}
  </div>
</section>"""


def _seat_positions(n, cx, cy, r0, dr, rows):
    """Lay n seats out over `rows` concentric arcs — a hemicycle, not a bar chart.

    Seats come back ordered left-to-right across the whole chamber, so a party
    block occupies a contiguous wedge the way it does on the floor."""
    import math
    caps = [(r0 + i * dr) for i in range(rows)]
    total = sum(caps)
    counts = [max(1, round(n * c / total)) for c in caps]
    while sum(counts) > n:
        counts[counts.index(max(counts))] -= 1
    while sum(counts) < n:
        counts[counts.index(min(counts))] += 1
    pts = []
    for i, cnt in enumerate(counts):
        r = r0 + i * dr
        for j in range(cnt):
            frac = (j + .5) / cnt
            t = math.pi - frac * math.pi
            pts.append((frac, cx + r * math.cos(t), cy - r * math.sin(t)))
    pts.sort(key=lambda p: p[0])
    return [(p[1], p[2]) for p in pts]


def _party_arc(cx, cy, r, f0, f1):
    """An outer band spanning the angular fraction a party occupies."""
    import math
    a0 = math.pi - f0 * math.pi
    a1 = math.pi - f1 * math.pi
    x0, y0 = cx + r * math.cos(a0), cy - r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy - r * math.sin(a1)
    return f'M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}'


def s12():
    ch = D["chamber"]
    benches = ch["benches"]
    carried, lost = D["division_carried"], D["division_lost"]

    def votes(div):
        out = []
        by = {b["party"]: b for b in div["divisions"]}
        for b in benches:
            d = by[b["party"]]
            out += ["aye"] * d["ayes"] + ["abstain"] * d["abstentions"] + ["no"] * d["noes"]
        return out

    order = []
    for b in benches:
        order += [b] * b["seats"]
    CX, CY = 300, 182
    pos = _seat_positions(len(order), CX, CY, 74, 20, 5)
    va, vb = votes(carried), votes(lost)
    seats = ""
    for i, (p, b) in enumerate(zip(pos, order)):
        seats += (f'<circle class="seat" cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="4.9" '
                  f'stroke="#0d1e2a" stroke-width=".9" data-a="{va[i]}" data-b="{vb[i]}">'
                  f'<title>{e(b["short"])} — {va[i]} / {vb[i]}</title></circle>')

    # party wedges outside the seats: identity without fighting the vote colour
    arcs, n0, tot = "", 0, len(order)
    for b in benches:
        f0, f1 = n0 / tot, (n0 + b["seats"]) / tot
        arcs += (f'<path d="{_party_arc(CX, CY, 172, f0 + .004, f1 - .004)}" fill="none" '
                 f'stroke="{b["colour"]}" stroke-width="5" stroke-linecap="butt"><title>'
                 f'{e(b["name"])} — {b["seats"]} seats, {b["party_vote_pct"]}% party vote</title></path>')
        n0 += b["seats"]

    key = "".join(
        f'<span class="chip" style="border-left:3px solid {b["colour"]}">{e(b["short"])} {b["seats"]}</span>'
        for b in benches)

    def divi(div, label, cls):
        r = div["result"]
        return (f'<div class="divi {cls}"><div class="tile-k">{label}</div>'
                f'<div class="divi-r">{r["ayes"]}–{r["noes"]}</div>'
                f'<div class="divi-v {"ok" if r["passed"] else "bad"}">'
                f'{"Carried" if r["passed"] else "Lost"} · {r["abstentions"]} abstained · '
                f'majority {r["majority_needed"]}</div></div>')

    sw = D["division_sweep"]
    rows = "".join(
        f'<tr><td class="n">{s["burden"]:.1f}%</td><td class="n">{s["equity_harm"]:.2f}</td>'
        f'<td class="n">{s["ayes"]}–{s["noes"]}</td><td class="n">{s["abst"]}</td>'
        f'<td class="n" style="color:var(--{"ok" if s["passed"] else "bad"})">'
        f'{"carried" if s["passed"] else "lost"}</td></tr>'
        for s in sw if s["burden"] in (0.0, 3.5, 4.0, 4.5, 5.0))
    return f"""
<section class="slide" id="s12" data-title="It has to survive the chamber">
  <div class="wrap wrap-wide stack g2">
    <div class="stack g1">
      <p class="eyebrow">12 — It has to survive the chamber</p>
      <h2>Same policy. Same House. Opposite outcome.</h2>
    </div>
    <div class="cols c32">
      <div class="panel">
        <div class="panel-head">
          <span class="panel-title">New Zealand House of Representatives · {ch['year']} · {ch['total_seats']} seats</span>
          <span class="tag tag-obs">Seats Observed</span>
        </div>
        <svg viewBox="105 0 390 195" class="seats" id="chamber" role="img"
             aria-label="Hemicycle of {ch['total_seats']} seats, filled by how each member votes, with party wedges outside">
          {arcs}{seats}
        </svg>
        <div class="chips" style="margin-top:.5rem">{key}</div>
        <div class="maplegend" style="margin-top:.5rem">
          <span><i style="background:#5cc98a; height:8px; width:8px; border-radius:50%"></i>aye</span>
          <span><i style="background:#ef6b57; height:8px; width:8px; border-radius:50%"></i>no</span>
          <span><i style="background:#2c4a5f; height:8px; width:8px; border-radius:50%"></i>abstain</span>
          <span style="color:var(--muted)">outer band = party</span>
        </div>
      </div>
      <div class="stack g2">
        <div class="mapctl">
          <button class="tgl" aria-pressed="true" data-div="a">It works, cap respected</button>
          <button class="tgl" aria-pressed="false" data-div="b">No effect, cap breached</button>
        </div>
        <div class="divis">
          {divi(carried, 'Delivers, burden ' + f"{carried['outcome']['low_income_burden_pct']:.2f}%", '')}
          {divi(lost, 'Fails to deliver, burden ' + f"{lost['outcome']['low_income_burden_pct']:.2f}%", 'lost')}
        </div>
        <div class="panel panel-2">
          <div class="panel-head"><span class="panel-title">Where the House turns</span>
            <span class="tag tag-sim">Swept live</span></div>
          <div class="scrollx"><table>
            <thead><tr><th class="n">Low-income burden</th><th class="n">Equity harm</th>
              <th class="n">Division</th><th class="n">Abst.</th><th class="n">Result</th></tr></thead>
            <tbody>{rows}</tbody>
          </table></div>
          <p class="kicker" style="text-transform:none; letter-spacing:0; font-size:.71rem; margin-top:.5rem">
            Cross the stated 5% constraint and the government loses 30 votes — Labour, then the
            Greens, move to abstention. Effectiveness is what actually decides it.</p>
        </div>
      </div>
    </div>
    <p class="pull">The version that passes is never the version that was modelled —
      <em>unless you model the version that passes</em>.</p>
    {src_line("<b>GET</b> /parliament/nz/chamber — official 2023 party-vote shares and seat counts",
              "<b>POST</b> /parliament/nz/division — party-bloc scoring over published stance priors",
              "priors are <b>Estimated</b> from published transport positions, not from a roll call")}
  </div>
</section>"""


def s13():
    pub = D["public"]
    ext = pub["extremes"]
    def cohort_rows(items):
        out = ""
        for c in items:
            n = c["distribution"]["net_support"]
            w = min(1.0, abs(n) / .35) * 50
            lbl = f"{c['income_band']} · {c['geography']} · {c['travel_mode'].replace('_', ' ')}"
            neg = n < 0
            out += (f'<div class="bar-row"><span style="color:var(--muted); font-size:.71rem">{e(lbl)}</span>'
                    f'<span class="bar-track" style="background:none; position:relative">'
                    f'<span style="position:absolute; left:50%; top:0; bottom:0; width:1px; background:var(--border-strong)"></span>'
                    f'<span style="position:absolute; {"right:50%" if neg else "left:50%"}; top:0; bottom:0; '
                    f'width:{w:.1f}%; background:var(--{"bad" if neg else "ok"}); border-radius:1px"></span></span>'
                    f'<span class="mono" style="text-align:right; color:var(--{"bad" if neg else "ok"})">{n:+.0%}</span></div>')
        return out

    year2 = D["media"]["scenarios"][-1]
    cards = "".join(
        f'<article class="press"><span class="press-mark">SIMULATED</span>'
        f'<div class="press-outlet">{e(h["outlet_label"].replace(" (SIMULATED)", ""))}</div>'
        f'<h3 class="press-h">{e(h["headline"])}</h3>'
        f'<p class="press-s">{e(h.get("standfirst", ""))}</p></article>'
        for h in year2["headlines"])

    fm = D["failure_modes"][:3]
    fmr = "".join(
        f'<div class="tile"><div class="tile-k">{e(f["severity"])} · p={f["probability"]:.2f}</div>'
        f'<div style="font-size:.83rem; margin:.15rem 0 .2rem">{e(f["risk"])}</div>'
        f'<div class="tile-u" style="line-height:1.45">{e(f["mechanism"][:150])}…</div></div>' for f in fm)

    st = D["stress"]
    worst = min(((s["label"], m["retained"]) for s in st["scenarios"] for m in s["metrics"]),
                key=lambda x: x[1])
    shocks = "".join(f'<span class="chip" style="color:var(--ok); border-color:rgba(92,201,138,.4)">'
                     f'{e(s["label"])}</span>' for s in st["scenarios"])
    return f"""
<section class="slide" id="s13" data-title="And the public, and the press">
  <div class="wrap wrap-wide stack g2">
    <div class="stack g1">
      <p class="eyebrow">13 — And the public, and the press</p>
      <h2>Not an average voter. {pub['n_cohorts']} cohorts, each with its own reason.</h2>
    </div>
    <div class="cols c32">
      <div class="stack g1">
        <div class="cols c2" style="gap:.45rem">
          <div class="panel panel-2">
            <div class="panel-head"><span class="panel-title">Where it loses</span></div>
            {cohort_rows(ext['opposed'])}
          </div>
          <div class="panel panel-2">
            <div class="panel-head"><span class="panel-title">Where it wins</span></div>
            {cohort_rows(ext['supportive'])}
          </div>
        </div>
        <div class="cols c3" style="gap:.45rem">
          <div class="tile tile-accent"><div class="tile-k">Net support, as drafted</div>
            <div class="tile-v sm">{D['net_support_protected']:+.1%}</div>
            <div class="tile-u">exemptions + 70% reinvestment</div></div>
          <div class="tile"><div class="tile-k">Net support, flat charge</div>
            <div class="tile-v sm bad">{D['net_support_flat']:+.1%}</div>
            <div class="tile-u">no exemptions, revenue to general fund</div></div>
          <div class="tile"><div class="tile-k">Micro-agents modelled</div>
            <div class="tile-v sm">{num(pub['population'])}</div>
            <div class="tile-u">income × geography × mode</div></div>
        </div>
        <div class="panel">
          <div class="panel-head"><span class="panel-title">Red team — what breaks it</span>
            <span class="tag tag-gen">Generated prose, simulated numbers</span></div>
          <div class="cols c3" style="gap:.45rem">{fmr}</div>
          <div style="margin-top:.7rem">
            <div class="kicker" style="margin-bottom:.35rem">Stressed under {len(st['scenarios'])} shocks
              at {e(st['horizon_label'])} — every one holds</div>
            <div class="chips">{shocks}</div>
            <p class="kicker" style="text-transform:none; letter-spacing:0; font-size:.71rem; margin-top:.45rem">
              Worst retention: <b class="cy">{worst[1]:.1f}%</b> of the benefit under {e(worst[0].lower())}.
              The system is built to print &ldquo;fails under recession&rdquo; when it is true. Here it isn't —
              so it says so, and the red team finds the real fault instead:
              <b>{e(fm[0]['risk'].lower())}</b>, p={fm[0]['probability']:.2f}.</p>
          </div>
        </div>
      </div>
      <div class="stack g1">
        <div class="kicker">Front pages at {e(year2['label'])} — {len(year2['headlines'])} desks,
          each grounded in a simulated figure</div>
        {cards}
      </div>
    </div>
    {src_line("<b>POST</b> /public — cohort opinion from material impact + perceived fairness + prior",
              "<b>POST</b> /media — archetype templates bound to the event ledger",
              "<b>POST</b> /stress-test · /parliament/failure-modes",
              "no real outlet is named, quoted or imitated")}
  </div>
</section>"""


def s14():
    r = D["registry"]
    limits = [
        "Scenarios under stated assumptions — not forecasts.",
        "LLMs never produce a quantitative result.",
        "Uncertainty widens with the horizon, visibly.",
        "Every output tagged Observed / Estimated / Simulated / Generated.",
        "Every number traces back: data → transformation → model → assumption.",
        "REPRODUCE RUN regenerates any result exactly.",
        "Backtest scores shown, including the bad ones.",
    ]
    li = "".join(f"<li>{e(x)}</li>" for x in limits)
    grows = ""
    for g in r["guardrails"]:
        grows += (f'<tr><td>{e(g["rule"])}</td>'
                  f'<td class="n" style="color:var(--{"ok" if g["holds"] else "bad"})">'
                  f'{"holds" if g["holds"] else "broken"}</td></tr>')
    sdg = D["sdg"]
    ind = ""
    for g in sdg["goals"]:
        for i in g["indicators"]:
            chg = (f'{i["change_pct"]:+.1f}%' if i.get("change_pct") is not None else "—")
            ind += (f'<tr><td class="mono stamp">{g["goal"]}</td><td>{e(i["indicator"])}</td>'
                    f'<td class="n">{i["baseline"]:,.1f}</td><td class="n">{i["scenario"]:,.1f}</td>'
                    f'<td class="n ok">{chg}</td>'
                    f'<td><span class="tag {"tag-sim" if i["tag"] == "Simulated" else ""}">{e(i["tag"])}</span></td></tr>')
    return f"""
<section class="slide" id="s14" data-title="Limits, and what we measure">
  <div class="wrap wrap-wide stack g2">
    <div class="stack g1">
      <p class="eyebrow">14 — Limits, and what we measure</p>
      <h2>Decision support. Not an oracle.</h2>
    </div>
    <div class="cols c23">
      <div class="stack g1">
        <div class="panel">
          <div class="panel-head"><span class="panel-title">What it is not</span></div>
          <ol class="lede" style="padding-left:1.1rem; font-size:.84rem; display:flex; flex-direction:column; gap:.28rem">{li}</ol>
        </div>
        <div class="panel panel-2">
          <div class="panel-head"><span class="panel-title">Guardrails, checked live</span>
            <span class="tag tag-obs">{r['counts']['guardrails_holding']} / {r['counts']['guardrails_total']}</span></div>
          <div class="scrollx"><table><tbody>{grows}</tbody></table></div>
        </div>
      </div>
      <div class="stack g1">
        <div class="cols c2" style="gap:.45rem">
          <div class="tile tile-accent"><div class="tile-k">Registered models</div>
            <div class="tile-v">{r['counts']['models']}</div>
            <div class="tile-u">{r['counts']['deterministic_models']} deterministic</div></div>
          <div class="tile tile-stamp"><div class="tile-k">Documented assumptions</div>
            <div class="tile-v">{r['counts']['documented_assumptions']}</div>
            <div class="tile-u">introspected from source</div></div>
          <div class="tile"><div class="tile-k">LLM-touched numbers</div>
            <div class="tile-v ok">{r['counts']['models_touching_numbers_with_llm']}</div>
            <div class="tile-u">across all {r['counts']['numeric_models']} numeric models</div></div>
          <div class="tile"><div class="tile-k">Composite SDG score</div>
            <div class="tile-v" style="font-size:1.1rem; color:var(--muted)">none</div>
            <div class="tile-u">a composite index is a marketing number</div></div>
        </div>
        <div class="panel">
          <div class="panel-head"><span class="panel-title">What it moves — measured, not scored</span>
            <span class="tag tag-sim">{e(sdg['headline'].split('.')[0])}</span></div>
          <div class="scrollx"><table>
            <thead><tr><th>SDG</th><th>Indicator</th><th class="n">Baseline</th><th class="n">Scenario</th>
              <th class="n">Change</th><th>Tag</th></tr></thead>
            <tbody>{ind}</tbody>
          </table></div>
        </div>
      </div>
    </div>
    {src_line("<b>GET</b> /registry — models, assumptions and guardrails, introspected live",
              "<b>POST</b> /sdg — baseline · scenario · change · source · confidence, per indicator",
              "<b>POST</b> /reproduce — regenerates any run from its hash")}
  </div>
</section>"""


def s15():
    lines = ["Twenty-four industries rehearse before they commit.",
             "Government is the last one that doesn't.",
             "The data exists. The models exist. The compute fits in a building.",
             "What's been missing is a place to put it all at once."]
    lh = "".join(f'<p{" class=on" if i == 3 else ""}>{e(l)}</p>' for i, l in enumerate(lines))
    return f"""
<section class="slide" id="s15" data-title="Stop governing on instinct">
  <div class="wrap stack g4">
    <div class="close-lines">{lh}</div>
    <div class="stack g2">
      <h1>Stop governing on instinct.</h1>
      <p class="lede">Every disaster on the first slide was discoverable in simulation.
        None of them were simulated.</p>
      <p class="pull" style="font-size:clamp(1.2rem,2.4vw,2rem)">
        <b class="cy">GOV SIM.</b> Run the policy <em>before</em> you run the country.</p>
    </div>
    <div class="cols c4">
      <div class="tile tile-accent"><div class="tile-k">Study area</div>
        <div class="tile-v sm">Auckland</div><div class="tile-u">any jurisdiction, same pipeline</div></div>
      <div class="tile"><div class="tile-k">Horizon</div><div class="tile-v sm">10 years</div>
        <div class="tile-u">8 checkpoints, scrubable</div></div>
      <div class="tile"><div class="tile-k">Full pipeline</div>
        <div class="tile-v sm">{(D['total_ms'] / 1000):.2f} s</div><div class="tile-u">measured, 8 stages</div></div>
      <div class="tile tile-stamp"><div class="tile-k">Cost per extra scenario</div>
        <div class="tile-v sm">0</div><div class="tile-u">run it again</div></div>
    </div>
  </div>
</section>"""


def appendix():
    refs = "".join(f"<li>{r}</li>" for r in WORKS_CITED)
    fab = D["fabric"]
    ds = "".join(
        f'<tr><td>{e(d["title"])}</td><td style="color:var(--muted)">{e(d["publisher"])}</td>'
        f'<td class="n">{num(d["record_count"]) if d.get("record_count") else "—"}</td>'
        f'<td class="mono" style="font-size:.68rem; color:var(--muted)">{e(d.get("revision") or "—")}</td>'
        f'<td><span class="tag {"tag-sim" if d.get("tag") == "Simulated" else "tag-obs"}">'
        f'{e(d.get("tag") or d.get("kind") or "—")}</span></td></tr>'
        for d in fab["datasets"])
    return f"""
<section class="slide appendix" id="s16" data-title="Provenance and works cited">
  <div class="wrap wrap-wide stack g2">
    <div class="stack g1">
      <p class="eyebrow">Appendix — what is real, and what is not</p>
      <h2>Provenance, in full.</h2>
      <p class="lede">Every demo panel in this deck was rendered from the running build: the FastAPI
        engine on localhost:8000, called stage by stage with timings measured at the call site, and the
        Auckland geometry the frontend ships. The deck holds itself to the standard the product does.</p>
    </div>
    <div class="cols c2">
      <div class="panel">
        <div class="panel-head"><span class="panel-title">Real, observed</span>
          <span class="tag tag-obs">Observed</span></div>
        <ul class="lede" style="font-size:.82rem; padding-left:1.1rem; display:flex; flex-direction:column; gap:.3rem">
          <li>Auckland street network, buildings, land use and coastline — OpenStreetMap via Overpass,
            {num(D['osm']['counts']['roads'])} roads and {num(D['osm']['counts']['buildings'])} buildings in
            the full extract.</li>
          <li>New Zealand House composition — Electoral Commission official 2023 results, {D['chamber']['total_seats']} seats.</li>
          <li>METR-LA loop-detector corpus — {D['ml']['dataset']['sensors']} sensors, 5-minute resolution.</li>
          <li>Model scores — held-out test split, read from the trained registry.</li>
          <li>Historical analogue effects — published evaluations of eight charging schemes.</li>
        </ul>
      </div>
      <div class="panel panel-2">
        <div class="panel-head"><span class="panel-title">Modelled or synthetic — and labelled as such</span>
          <span class="tag tag-sim">Simulated</span></div>
        <ul class="lede" style="font-size:.82rem; padding-left:1.1rem; display:flex; flex-direction:column; gap:.3rem">
          <li>The {num(D['microsim']['commuters'])} commuters are synthetic micro-agents on a modelled
            zone system, not real residents.</li>
          <li>Party stance priors are Estimated from published transport positions, not a roll call.</li>
          <li>Press coverage is template-generated, watermarked, and imitates no real outlet.</li>
          <li>The historical backtest case is an illustrative synthetic benchmark, and the app says so.</li>
          <li>All forward numbers are scenarios under stated assumptions — not forecasts.</li>
        </ul>
      </div>
    </div>
    <div class="panel scrollx">
      <div class="panel-head"><span class="panel-title">Datasets in the fabric</span>
        <span class="tag">{fab['counts']['datasets']} datasets · {num(fab['counts']['records_total'])} records</span></div>
      <table><thead><tr><th>Dataset</th><th>Publisher</th><th class="n">Records</th>
        <th>Content hash</th><th>Tag</th></tr></thead><tbody>{ds}</tbody></table>
    </div>
    <div class="panel">
      <div class="panel-head"><span class="panel-title">Works cited</span></div>
      <ol class="refs">{refs}</ol>
    </div>
  </div>
</section>"""


JS = r"""
(function(){
  var deck = document.getElementById('deck');
  var slides = Array.prototype.slice.call(deck.querySelectorAll('.slide'));
  var fill = document.getElementById('rail-fill');
  var idx = document.getElementById('hud-idx');
  var ttl = document.getElementById('hud-title');
  var current = 0;

  function mark(i){
    current = i;
    idx.textContent = String(i+1).padStart(2,'0') + ' / ' + String(slides.length).padStart(2,'0');
    ttl.textContent = slides[i].dataset.title || '';
    fill.style.width = ((i+1)/slides.length*100) + '%';
  }
  var io = new IntersectionObserver(function(es){
    es.forEach(function(en){
      if(!en.isIntersecting) return;
      mark(slides.indexOf(en.target));
      if(en.target.id === 's7') runConsole();
    });
  }, {threshold:0.5});
  slides.forEach(function(s){ io.observe(s); });

  /* Set scrollTop on the container rather than calling scrollIntoView, which a
     mandatory-snap container cancels outright. */
  function go(n){
    var i = Math.max(0, Math.min(slides.length-1, n));
    deck.scrollTop = slides[i].offsetTop - deck.offsetTop;
  }
  document.addEventListener('keydown', function(ev){
    if(ev.metaKey || ev.ctrlKey || ev.altKey) return;
    var t = ev.target.tagName;
    if(t === 'INPUT' || t === 'TEXTAREA') return;
    if(ev.key === 'ArrowDown' || ev.key === 'ArrowRight' || ev.key === 'PageDown' || ev.key === ' '){
      ev.preventDefault(); go(current+1);
    } else if(ev.key === 'ArrowUp' || ev.key === 'ArrowLeft' || ev.key === 'PageUp'){
      ev.preventDefault(); go(current-1);
    } else if(ev.key === 'Home'){ ev.preventDefault(); go(0); }
      else if(ev.key === 'End'){ ev.preventDefault(); go(slides.length-1); }
  });
  document.getElementById('nav-prev').addEventListener('click', function(){ go(current-1); });
  document.getElementById('nav-next').addEventListener('click', function(){ go(current+1); });

  /* Fit each slide to the viewport the way presentation software does: scale
     the content block down rather than clipping it or letting it scroll away.
     Below the floor the slide is allowed to scroll instead of going unreadable. */
  var FLOOR = 0.62;
  function fit(){
    slides.forEach(function(s){
      var w = s.querySelector('.wrap');
      if(!w || s.classList.contains('appendix')) return;
      w.style.transform = ''; w.style.marginBottom = '';
      var cs = getComputedStyle(s);
      /* measure against the viewport, not the slide — the slide grows to fit
         its own content, so its height is never the constraint */
      var avail = window.innerHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      var h = w.getBoundingClientRect().height;
      if(h <= avail || h === 0) return;
      var k = Math.max(FLOOR, avail / h);
      w.style.transform = 'scale(' + k.toFixed(4) + ')';
      w.style.marginBottom = (-(h * (1 - k)).toFixed(1)) + 'px';
      s.style.overflowY = (h * k > avail) ? 'auto' : '';
    });
  }
  var rt;
  window.addEventListener('resize', function(){ clearTimeout(rt); rt = setTimeout(fit, 150); });
  if(document.fonts && document.fonts.ready){ document.fonts.ready.then(fit); }
  window.addEventListener('load', fit);
  fit();

  /* slide 07 — replay the measured run, stage by stage, at its real cadence */
  var ran = false;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function runConsole(){
    if(ran) return; ran = true;
    var rows = document.querySelectorAll('#console .stage');
    if(reduce){ rows.forEach(function(r){ r.classList.add('on'); }); return; }
    var t = 0;
    rows.forEach(function(r, i){
      t += Math.max(90, Number(r.querySelector('.stage-t').textContent.replace(/\D/g,'')) * 0.9);
      setTimeout(function(){ r.classList.add('on'); }, t);
    });
  }

  /* slide 10 — layer toggles over the real geometry */
  document.querySelectorAll('[data-layer]').forEach(function(b){
    b.addEventListener('click', function(){
      var on = b.getAttribute('aria-pressed') === 'true';
      b.setAttribute('aria-pressed', String(!on));
      var g = document.getElementById('lyr-' + b.dataset.layer);
      if(g) g.style.display = on ? 'none' : '';
    });
  });

  /* slide 10 — the timeline, off the real delta series */
  var SERIES = window.__GOVSIM_SERIES__, CPS = window.__GOVSIM_CPS__;
  var scrub = document.getElementById('scrub');
  var vals = document.getElementById('scrub-vals');
  var at = document.getElementById('scrub-at');
  var KEYS = ['traffic.vehicle_trips_into_cbd','emissions.daily_co2_tonnes',
              'mode_share.car_pct','transit.daily_transit_trips'];
  function paint(){
    var i = Number(scrub.value);
    at.textContent = CPS[i].label;
    vals.innerHTML = KEYS.map(function(k){
      var s = SERIES[k], p = s.points[i];
      var good = p.pct <= 0 ? (k.indexOf('transit') === 0 ? 'bad' : 'ok')
                            : (k.indexOf('transit') === 0 ? 'ok' : 'bad');
      if(i === 0) good = '';
      return '<div class="bar-row"><span style="color:var(--muted); font-size:.72rem">' + s.label +
        '</span><span class="mono" style="font-size:.72rem; text-align:right; color:var(--muted)">' +
        p.d.toLocaleString(undefined,{maximumFractionDigits:1}) + ' ' + s.unit +
        '</span><span class="mono ' + good + '" style="text-align:right">' +
        (p.pct >= 0 ? '+' : '') + p.pct.toFixed(1) + '%</span></div>';
    }).join('');
  }
  if(scrub){ scrub.addEventListener('input', paint); paint(); }

  /* slide 12 — swap the two divisions on the same chamber */
  var VOTE = {aye:'#5cc98a', no:'#ef6b57', abstain:'#2c4a5f'};
  function division(which){
    document.querySelectorAll('#chamber .seat').forEach(function(c){
      c.setAttribute('fill', VOTE[c.dataset[which]]);
    });
    document.querySelectorAll('[data-div]').forEach(function(b){
      b.setAttribute('aria-pressed', String(b.dataset.div === which));
    });
  }
  document.querySelectorAll('[data-div]').forEach(function(b){
    b.addEventListener('click', function(){ division(b.dataset.div); });
  });
  division('a');
  mark(0);
})();
"""


def build():
    slides = [s01(), s02(), s03(), s04(), s05(), s06(), s07(), s08(), s09(),
              s10(), s11(), s12(), s13(), s14(), s15(), appendix()]
    payload = json.dumps({k: D["series"][k] for k in D["series"]}, separators=(",", ":"))
    cps = json.dumps([{"label": c["label"], "t": c["t_months"]} for c in D["checkpoints"]],
                     separators=(",", ":"))
    doc = f"""<meta charset="utf-8">
<title>GOV SIM</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{FONT_CSS}{CSS}</style>
<div class="rail"><div class="rail-fill" id="rail-fill"></div></div>
<main class="deck" id="deck">
{"".join(slides)}
</main>
<div class="hud">
  <span><span class="hud-mark">GOV&nbsp;SIM</span> · run the policy before you run the country</span>
  <span id="hud-title" style="flex:1; text-align:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap"></span>
  <span style="display:flex; align-items:center; gap:.7rem">
    <b id="hud-idx">01 / 16</b>
    <span class="hud-nav"><button id="nav-prev" aria-label="Previous slide">←</button><button id="nav-next" aria-label="Next slide">→</button></span>
  </span>
</div>
<script>window.__GOVSIM_SERIES__={payload};window.__GOVSIM_CPS__={cps};</script>
<script>{JS}</script>
"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(doc)
    print("wrote", OUT, round(len(doc) / 1024), "KB")


if __name__ == "__main__":
    build()
