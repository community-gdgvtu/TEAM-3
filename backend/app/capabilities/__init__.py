"""Service capability manifest (SPEC §27/§33 transparency).

``GET /capabilities`` maps every HTTP route the engine serves to its SPEC
section, functional area, provenance class and keyless-example companion, and
reconciles that curated catalogue **live** against the running app's routes so
it can never silently drift from what is actually served. It is the machine-
readable "front door" — where ``/registry`` (§33) catalogues the *models* and
``/data-fabric`` (§4) the *datasets*, this catalogues the *HTTP surface* itself.
Deterministic, no LLM, Observed about the service.
"""
