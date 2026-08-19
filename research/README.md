# research/

Individual exploration lives here — **reference material, not the shipped
implementation.** This is where your own experiments are welcome to differ from the app's structure.

**Conventions**

- One subfolder per person/topic, e.g. `research/AR-life-expectancy/`.
- **Commit** the code, notebooks, and *small* result files — a `model_comparison_results.csv`, a
  `run_summary.json`, and a short `README.md` describing what you tried and found.
- **Do NOT commit large binaries** — trained models (`*.joblib`), vector stores (`chroma*/`,
  `*.sqlite3`), or big datasets. They are gitignored and regenerate from your code. (Squash-merge
  keeps them out of `develop` even if they're in your branch history.)
- Each research folder should carry its own `requirements.txt` if it needs libraries the app doesn't.

**Reference, not canonical.** The reviewed, shipped implementation of a feature goes in the app
(`backend/ml/`, etc.) against its spec — not here. Good research here can *seed* a spec: e.g. a RAG
explorer becomes the basis for **spec 004 (AI insights)**. So nothing you do here is wasted — it's
either a reference others learn from, or the seed of the next spec.
