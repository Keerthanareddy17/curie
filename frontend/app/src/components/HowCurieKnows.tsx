import { CheckCircle2 } from "lucide-react";

const POINTS = [
  "Independent sources — UniProt, IEDB, Europe PMC, and ESM Atlas are called separately; no single source can define the outcome.",
  "Structured evidence records — every fact carries provenance: source, identifier, retrieval time, and a URL where available.",
  "Deterministic adjudication — cross-source checks are rule-based, not a model's opinion; the same evidence always yields the same score.",
  "Provenance tracking — every claim traces back to a specific tool call, never free-floating text.",
  "Conflict detection — disagreeing sources are surfaced explicitly, never silently resolved in one direction.",
  "Abstention — insufficient evidence produces a stated abstention, not a guess.",
  "Reproducible evaluation — curie/evaluation/ re-runs this same logic against real APIs and controlled failure scenarios on demand.",
];

export function HowCurieKnows() {
  return (
    <div className="bg-panel-light border border-line rounded-xl p-4">
      <h3 className="text-xs font-bold text-ink uppercase tracking-wide mb-2">How curie knows</h3>
      <ul className="space-y-1.5">
        {POINTS.map((p, i) => (
          <li key={i} className="flex items-start gap-1.5 text-[10.5px] text-muted-ink">
            <CheckCircle2 className="w-3 h-3 text-teal shrink-0 mt-0.5" />
            <span>{p}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
