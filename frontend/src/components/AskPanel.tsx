"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { getAsk, type InsightResponse } from "@/lib/api";

const EXAMPLES = [
  "What was life expectancy in Kenya in 2020?",
  "Which countries get the most life expectancy for their health spending?",
];

// Grounded, cited AI Q&A over the published mart (spec 004 /ask). The answer is only ever what the
// mart supports — the panel shows the citations so the user can see the grounding, never a bare claim.
export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<InsightResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(q: string) {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await getAsk(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach the AI.");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void ask(question);
  }

  return (
    <div className="space-y-3">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
          placeholder="Ask a question about the data…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          aria-label="Ask a question about the data"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>

      <div className="flex flex-wrap gap-2 text-xs text-slate-500">
        <span>Try:</span>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            className="rounded border border-slate-200 px-2 py-0.5 hover:bg-slate-50"
            onClick={() => {
              setQuestion(ex);
              void ask(ex);
            }}
          >
            {ex}
          </button>
        ))}
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}

      {result && (
        <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-900">{result.answer}</p>
          {result.citations.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {result.citations.map((c, i) => (
                <span
                  key={`${c.country_code}-${c.year}-${c.indicator}-${i}`}
                  className="rounded bg-white px-2 py-0.5 text-xs text-slate-600 ring-1 ring-slate-200"
                >
                  {c.country_name} {c.year} · {c.indicator}={c.value}
                </span>
              ))}
            </div>
          )}
          <p className="text-xs italic text-slate-500">{result.caveats}</p>
        </div>
      )}
    </div>
  );
}
