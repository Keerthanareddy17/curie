import { AlertOctagon, ShieldOff } from "lucide-react";
import type { InvestigationState } from "../types";
import { STATUS_COLOR, STATUS_LABEL } from "../lib/statusMeta";

function EvidenceScoreCard({ state }: { state: InvestigationState }) {
  return (
    <div className="bg-panel border border-line rounded-lg p-3 flex items-center justify-between gap-4">
      <div>
        <div className="text-[9px] font-mono uppercase tracking-wider text-muted-ink">Evidence score</div>
        <div className="text-xl font-bold text-ink font-mono">
          {state.evidence_score != null ? state.evidence_score.toFixed(2) : "—"}
        </div>
        <div className="text-[9px] text-muted-ink mt-0.5">
          Deterministic evidence-support score, not a calibrated probability.
        </div>
      </div>
      <div
        className={`text-[10px] font-mono uppercase tracking-wider border rounded-full px-3 py-1.5 whitespace-nowrap ${STATUS_COLOR[state.status]}`}
      >
        {STATUS_LABEL[state.status]}
      </div>
    </div>
  );
}

function ConflictPanel({ state }: { state: InvestigationState }) {
  if (state.conflicts.length === 0) return null;
  const evidenceById = new Map(state.evidence.map((e) => [e.evidence_id, e]));

  return (
    <div className="border border-red/40 bg-red/5 rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-1.5 text-red font-bold text-xs">
        <AlertOctagon className="w-3.5 h-3.5" /> Evidence conflict detected
      </div>
      {state.conflicts.map((c) => {
        const a = evidenceById.get(c.evidence_a);
        const b = evidenceById.get(c.evidence_b);
        return (
          <div key={c.conflict_id} className="text-[10.5px] text-ink border-t border-red/20 pt-2 first:border-0 first:pt-0">
            <div>{c.claim}</div>
            <div className="text-[9.5px] text-muted-ink mt-1">
              <span className="font-mono">{a?.source ?? "?"}</span> vs.{" "}
              <span className="font-mono">{b?.source ?? "?"}</span> · severity: {c.severity} · resolved:{" "}
              {c.resolved ? "yes" : "no — not silently chosen"}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AbstentionPanel({ state }: { state: InvestigationState }) {
  if (state.status !== "insufficient_evidence") return null;
  return (
    <div className="border border-amber/40 bg-amber/5 rounded-lg p-3 space-y-1.5">
      <div className="flex items-center gap-1.5 text-amber font-bold text-xs">
        <ShieldOff className="w-3.5 h-3.5" /> curie abstained from a conclusion
      </div>
      <p className="text-[10.5px] text-ink">
        Available evidence was insufficient to establish a confident result. This
        is a successful reliability outcome, not a crash — curie did not infer a
        conclusion from incomplete evidence.
      </p>
      {state.missing_evidence.length > 0 && (
        <ul className="text-[10px] text-muted-ink list-disc list-inside space-y-0.5">
          {state.missing_evidence.map((m, i) => (
            <li key={i}>{m}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ResultPanel({ state }: { state: InvestigationState }) {
  return (
    <div className="space-y-2">
      <EvidenceScoreCard state={state} />
      <ConflictPanel state={state} />
      <AbstentionPanel state={state} />
    </div>
  );
}
