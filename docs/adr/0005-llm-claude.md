# ADR-0005: LLM — Anthropic Claude via API

- **Status:** Accepted
- **Date:** 2026-08-20

## Context
Two features need an LLM: a structured **country health brief** (`/brief`) and a **grounded, cited
Q&A** over the mart (`/ask`). Both must be schema-valid or citation-grounded — no free-form hallucination
— and must degrade safely when no key is configured.

## Decision
Use **Anthropic Claude** via the API (through `langchain-anthropic`), with **structured output** for the
brief and a **SQL-tool agent** with whitelisted, parameterized queries for Q&A. A **deterministic
fallback** runs when no key is present, so the stack works offline.

## Alternatives considered
- **Self-hosted open model (via SageMaker/vLLM):** adds serving infra and ops for no clear gain at this
  scale; the LLM is a managed dependency, not our model to host.
- **Another hosted provider:** viable, but Claude's structured-output + tool-use fit the grounding
  requirement well; the choice is isolated behind config (`ANTHROPIC_MODEL`).

## Consequences
- LLM features are a thin, cited layer over governed data — never a free-form generator.
- **Boundary:** the LLM is *not* SageMaker's concern (ADR territory for the trained model only); on AWS
  it's the Anthropic API or Bedrock. The Claude features are evaluated by the spec-008 eval gate
  (groundedness, citations, decline behaviour, honest framing).
