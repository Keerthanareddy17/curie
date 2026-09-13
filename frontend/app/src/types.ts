// Mirrors curie/shared/models.py and curie/agent/state.py. Kept as plain
// interfaces (not generated) since the backend surface is small and stable;
// if it grows, generate this from the FastAPI OpenAPI schema instead of
// hand-maintaining a second copy.

export type ToolStatus = "ok" | "error" | "not_implemented" | "timeout" | "skipped";

export interface ToolResult {
  provider: string;
  operation: string;
  status: ToolStatus;
  latency_ms: number;
  request_id: string;
  error: string | null;
  data: unknown;
  fetched_at: string;
}

export type SequenceType = "protein" | "nucleotide" | "unknown";
export type IdentityStatus = "resolved_hint" | "unresolved";
export type InvestigationStatusValue =
  | "planning"
  | "collecting"
  | "adjudicating"
  | "supported"
  | "partially_supported"
  | "conflicting"
  | "insufficient_evidence"
  | "failed";

export type EvidenceType =
  | "sequence_identity"
  | "curated_annotation"
  | "experimental_structure"
  | "predicted_structure"
  | "curated_epitope"
  | "predicted_epitope"
  | "literature"
  | "absence_of_evidence";

export type EvidenceLevel = "curated" | "observed" | "predicted" | "none";
export type Directness = "direct" | "indirect" | "unknown";
export type AgreementLevel = "agree" | "partial" | "conflict" | "unverifiable";

export interface EvidenceRecord {
  evidence_id: string;
  source: string;
  source_type: string;
  identifier: string | null;
  claim: string;
  evidence_type: EvidenceType;
  evidence_level: EvidenceLevel;
  directness: Directness;
  confidence: number | null;
  source_url: string | null;
  retrieved_at: string;
  metadata: Record<string, unknown>;
}

export interface CandidateProtein {
  accession: string;
  name: string | null;
  organism: string | null;
  match_type: string;
  source: string;
}

export interface Claim {
  claim_id: string;
  statement: string;
  supporting_evidence_ids: string[];
  conflicting_evidence_ids: string[];
  agreement: AgreementLevel;
  notes: string;
}

export interface EvidenceConflict {
  conflict_id: string;
  claim: string;
  evidence_a: string;
  evidence_b: string;
  conflict_type: string;
  severity: string;
  resolved: boolean;
  notes: string;
}

export interface ResearchPlan {
  needs_identity: boolean;
  needs_epitope_evidence: boolean;
  needs_literature: boolean;
  needs_structure: boolean;
  structure_allowed: boolean;
  reasoning: string;
}

export interface TraceEvent {
  run_id: string;
  node: string;
  timestamp: string;
  duration_ms: number;
  status: string;
  tools_called: string[];
  input_summary: string;
  output_summary: string;
  evidence_count: number;
  evidence_score: number | null;
  errors: string[];
}

export interface Dossier {
  investigation_id: string;
  generated_at: string;
  sequence_summary: string;
  sequence_type: SequenceType;
  identity_result: string;
  identity_evidence: string[];
  structural_evidence: string[];
  epitope_evidence: string[];
  literature_evidence: string[];
  cross_source_agreement: string;
  conflicts: EvidenceConflict[];
  missing_evidence: string[];
  evidence_score: number;
  final_status: InvestigationStatusValue;
  provenance: ToolResult[];
  limitations: string[];
  next_research_questions: string[];
  ai_synthesis: string | null;
}

export interface InvestigationState {
  run_id: string;
  raw_sequence: string;
  accession_hint: string | null;
  notes: string;
  normalized_sequence: string;
  translated_sequence: string | null;
  sequence_type: SequenceType;
  residue_composition: Record<string, number>;
  mean_hydrophobicity: number | null;
  mean_antigenicity: number | null;
  research_plan: ResearchPlan | null;
  identity_status: IdentityStatus;
  candidate_proteins: CandidateProtein[];
  protein_name: string | null;
  tool_results: ToolResult[];
  evidence: EvidenceRecord[];
  errors: string[];
  claims: Claim[];
  conflicts: EvidenceConflict[];
  evidence_score: number | null;
  missing_evidence: string[];
  status: InvestigationStatusValue;
  trace: TraceEvent[];
  ai_synthesis: string | null;
  dossier: Dossier | null;
}

/** A pending run hasn't produced a full InvestigationState yet. */
export interface PendingInvestigation {
  run_id: string;
  status: "pending";
}

export function isPending(x: InvestigationState | PendingInvestigation): x is PendingInvestigation {
  return x.status === "pending" && !("evidence" in x);
}

// --- evaluation report (curie/evaluation/report.py) -------------------------

export interface EvaluationMetricDetail {
  value: number | null;
  [key: string]: unknown;
}

export interface EvaluationReport {
  run_timestamp: string;
  cases_evaluated: number;
  scenarios_evaluated: number;
  metrics: Record<string, number | null>;
  metrics_detail: Record<string, EvaluationMetricDetail>;
  identity_evaluation_breakdown: Record<string, unknown>;
  cases: Array<Record<string, unknown>>;
  reliability_scenarios: Array<Record<string, unknown>>;
  limitations: string[];
}
