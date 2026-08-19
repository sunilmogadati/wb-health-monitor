"""GET /api/v1/ask — natural-language Q&A over the published mart (spec 004, FR-007)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ai.insights import InsightResponse, answer_question

router = APIRouter(tags=["insights"])


@router.get(
    "/ask", response_model=InsightResponse, summary="Ask a question about the published mart"
)
def ask(
    q: str = Query(..., min_length=1, description="A plain-English question about the health data"),
) -> InsightResponse:
    return answer_question(q)
