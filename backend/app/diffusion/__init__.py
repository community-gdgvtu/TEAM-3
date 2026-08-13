"""Social-network / opinion-diffusion engine (SPEC §14).

Builds an abstract social graph (citizen cohorts + journalists + politicians +
institutions + influencers + community groups) with weighted influence edges and
runs a deterministic Friedkin–Johnsen opinion-diffusion process over it →
narrative spread, opinion polarisation and coalition formation over successive
information rounds. Citizen starting opinions are seeded from the deterministic
cohort-opinion model; actor priors are transparent, documented constants. No LLM
touches any number (SPEC §34).
"""
