"""Policy compiler endpoint (SPEC §3, Step 2).

``POST /policy/compile`` turns natural-language policy text into the structured
Policy DSL, exposing every extracted assumption for human correction. The LLM is
used only for language structuring with a deterministic rule-based fallback;
neither path produces numeric simulation effects (SPEC §34).
"""

from __future__ import annotations

from fastapi import APIRouter

from ..policy import compile_policy
from ..policy.dsl import CompileRequest, CompileResponse

router = APIRouter(prefix="/policy", tags=["policy"])


@router.post("/compile", response_model=CompileResponse, summary="Compile NL policy → DSL")
def compile_endpoint(req: CompileRequest) -> CompileResponse:
    """Compile ``req.text`` into a Policy DSL plus reviewable assumptions.

    ``method`` reports whether the LLM or the rule-based fallback produced the
    DSL. ``assumptions`` lists every inferred/defaulted field so the frontend can
    render an editable panel (SPEC §3: never bury assumptions).
    """
    return compile_policy(req.text, req.jurisdiction)
