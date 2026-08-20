"""Continuous evaluation & quality gates (spec 008).

The deterministic checks (``checks``) are the free CI gate — pure functions over response payloads,
no DB / LLM / network, unit-testable with crafted fixtures. The throttled LLM-as-judge for
groundedness (``judge``, later) runs off the PR path. Thresholds live in ``thresholds.json``.
"""
