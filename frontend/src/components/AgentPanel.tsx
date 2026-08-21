"use client";

import { useState } from "react";
import { getAgentAnalyze, type AgentResponse } from "@/lib/api";

// Spec 011: the multi-step agent, made visible. Unlike Ask AI (one round), this shows the STEPS the
// agent took (which tools, with what args) before its grounded answer.
export function AgentPanel() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await getAgentAnalyze(q));
    } catch (err) {
      setError(err instanceof Error ? err.message : "The agent failed to run.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder="Ask a multi-part question, e.g. is Kenya improving and is it above what it spends?"
          className="flex-1 rounded border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={run}
          disabled={loading || !question.trim()}
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Thinking…" : "Run agent"}
        </button>
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        {["Is Kenya's life expectancy improving, and is it above what its spending predicts?"].map(
          (ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setQuestion(ex)}
              className="rounded-full border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50"
            >
              {ex}
            </button>
          ),
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}

      {result && (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm text-slate-900">{result.answer}</p>
          {result.steps.length > 0 && (
            <details className="text-xs text-slate-600">
              <summary className="cursor-pointer font-medium">
                Steps the agent took ({result.steps.length})
              </summary>
              <ol className="mt-2 list-decimal space-y-1 pl-5">
                {result.steps.map((s, i) => (
                  <li key={i}>
                    <span className="font-mono text-slate-800">{s.tool}</span>{" "}
                    <span className="text-slate-500">{s.summary}</span>
                  </li>
                ))}
              </ol>
            </details>
          )}
          <p className="text-xs text-slate-500">
            {result.citations.length} citation(s) · {result.caveat}
          </p>
        </div>
      )}
    </div>
  );
}
