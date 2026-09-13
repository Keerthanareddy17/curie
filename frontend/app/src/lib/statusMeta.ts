import type { InvestigationStatusValue, ToolStatus } from "../types";

export const STATUS_LABEL: Record<InvestigationStatusValue, string> = {
  planning: "PLANNING",
  collecting: "COLLECTING",
  adjudicating: "ADJUDICATING",
  supported: "SUPPORTED",
  partially_supported: "PARTIALLY SUPPORTED",
  conflicting: "CONFLICTING",
  insufficient_evidence: "INSUFFICIENT EVIDENCE",
  failed: "FAILED",
};

// Deliberately restrained: green only for a clean SUPPORTED, amber for
// partial/abstention (uncertainty is not a failure), red only for a genuine
// conflict or execution failure.
export const STATUS_COLOR: Record<InvestigationStatusValue, string> = {
  planning: "text-muted-ink border-line-strong",
  collecting: "text-teal border-teal/40",
  adjudicating: "text-teal border-teal/40",
  supported: "text-emerald-400 border-emerald-400/40",
  partially_supported: "text-amber border-amber/40",
  conflicting: "text-red border-red/40",
  insufficient_evidence: "text-amber border-amber/40",
  failed: "text-red border-red/40",
};

export const TOOL_STATUS_LABEL: Record<ToolStatus, string> = {
  ok: "OK",
  error: "FAILED",
  timeout: "TIMEOUT",
  skipped: "SKIPPED",
  not_implemented: "NOT IMPLEMENTED",
};

export const TOOL_STATUS_COLOR: Record<ToolStatus, string> = {
  ok: "text-emerald-400 border-emerald-400/40 bg-emerald-400/5",
  error: "text-red border-red/40 bg-red/5",
  timeout: "text-red border-red/40 bg-red/5",
  skipped: "text-muted-ink border-line-strong bg-white/[0.02]",
  not_implemented: "text-muted-ink border-line-strong bg-white/[0.02]",
};

export const PROVIDER_LABEL: Record<string, string> = {
  uniprot: "UniProt",
  iedb: "IEDB",
  europe_pmc: "Europe PMC",
  esm_atlas: "ESM Atlas",
};

export function formatSeconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}
