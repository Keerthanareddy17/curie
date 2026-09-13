import { AlertTriangle, Box } from "lucide-react";
import Molecular3DVisualizer from "./Molecular3DVisualizer";
import { summarizePdb } from "../lib/pdb";
import type { EvidenceRecord, InvestigationState, ToolResult } from "../types";

function findEsmResult(state: InvestigationState): ToolResult | undefined {
  return [...state.tool_results].reverse().find((r) => r.provider === "esm_atlas");
}

function findStructureEvidence(state: InvestigationState): EvidenceRecord | undefined {
  return state.evidence.find((e) => e.evidence_type === "predicted_structure");
}

export function StructureViewer({ state }: { state: InvestigationState | null }) {
  if (!state) {
    return (
      <EmptyState
        icon={<Box className="w-8 h-8 text-muted-ink/50" />}
        title="No investigation running"
        detail="Paste a sequence and click Investigate, or Run Golden Path, to see a real predicted structure here."
      />
    );
  }

  const esmResult = findEsmResult(state);

  if (!esmResult) {
    return (
      <EmptyState
        icon={<Box className="w-8 h-8 text-muted-ink/50" />}
        title="Structure pending"
        detail="ESM Atlas has not been called yet for this investigation."
      />
    );
  }

  if (esmResult.status !== "ok" || typeof esmResult.data !== "string") {
    return (
      <EmptyState
        icon={<AlertTriangle className="w-8 h-8 text-amber/60" />}
        title="Structure unavailable"
        detail={
          esmResult.status === "skipped"
            ? `ESM Atlas was skipped: ${esmResult.error ?? "reason not recorded"}.`
            : `ESM Atlas call failed (${esmResult.status}): ${esmResult.error ?? "no further detail"}.`
        }
        toolStatus={esmResult.status}
      />
    );
  }

  const pdbData = esmResult.data;
  const { residues, atoms } = summarizePdb(pdbData);
  const structureEvidence = findStructureEvidence(state);
  const confidence =
    structureEvidence?.confidence != null
      ? `${structureEvidence.confidence.toFixed(1)} pLDDT (predicted)`
      : "not available";

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono uppercase tracking-wider text-teal">Predicted structure</span>
        <span className="text-[9px] font-mono text-muted-ink">live · ESM Atlas</span>
      </div>
      <div className="flex-1 min-h-0">
        <Molecular3DVisualizer
          mode="protein"
          pdbData={pdbData}
          activeStyle="cartoon"
          structureInfo={{ residues, atoms, confidence, source: "ESM Atlas" }}
        />
      </div>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  detail,
  toolStatus,
}: {
  icon: React.ReactNode;
  title: string;
  detail: string;
  toolStatus?: string;
}) {
  return (
    <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-center gap-2 border border-dashed border-line-strong rounded-xl bg-panel/50 p-6">
      {icon}
      <div className="text-xs font-bold text-ink">{title}</div>
      <div className="text-[10.5px] text-muted-ink max-w-xs">{detail}</div>
      {toolStatus && (
        <span className="text-[9px] font-mono uppercase tracking-wider text-muted-ink border border-line-strong rounded px-1.5 py-0.5 mt-1">
          esm_atlas: {toolStatus}
        </span>
      )}
    </div>
  );
}
