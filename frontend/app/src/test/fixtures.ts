import type { Dossier, EvaluationReport, InvestigationState, TraceEvent } from "../types";

export function makeTrace(overrides: Partial<TraceEvent> = {}): TraceEvent {
  return {
    run_id: "inv-test",
    node: "sequence_intake",
    timestamp: "2026-01-01T00:00:00Z",
    duration_ms: 12.3,
    status: "ok",
    tools_called: [],
    input_summary: "",
    output_summary: "",
    evidence_count: 0,
    evidence_score: null,
    errors: [],
    ...overrides,
  };
}

export function makeDossier(overrides: Partial<Dossier> = {}): Dossier {
  return {
    investigation_id: "inv-test",
    generated_at: "2026-01-01T00:00:00Z",
    sequence_summary: "223-residue protein sequence",
    sequence_type: "protein",
    identity_result: "Resolved via supplied accession hint: P0DTC2 (Spike glycoprotein).",
    identity_evidence: ["ev-1"],
    structural_evidence: ["ev-2"],
    epitope_evidence: ["ev-3"],
    literature_evidence: ["ev-4"],
    cross_source_agreement: "3 of 3 check(s) agree, 0 conflict, 0 partial, 0 unverifiable.",
    conflicts: [],
    missing_evidence: [],
    evidence_score: 1.0,
    final_status: "supported",
    provenance: [],
    limitations: ["curie is research and education software and produces no clinical recommendations."],
    next_research_questions: ["No specific follow-up gaps were identified from this run's evidence."],
    ai_synthesis: null,
    ...overrides,
  };
}

export function makeInvestigationState(overrides: Partial<InvestigationState> = {}): InvestigationState {
  return {
    run_id: "inv-test",
    raw_sequence: "MKV",
    accession_hint: "P0DTC2",
    notes: "",
    normalized_sequence: "MKV",
    translated_sequence: null,
    sequence_type: "protein",
    residue_composition: {},
    mean_hydrophobicity: null,
    mean_antigenicity: null,
    research_plan: null,
    identity_status: "resolved_hint",
    candidate_proteins: [
      { accession: "P0DTC2", name: "Spike glycoprotein", organism: "SARS-CoV-2", match_type: "accession_hint", source: "uniprot" },
    ],
    protein_name: "Spike glycoprotein",
    tool_results: [
      { provider: "uniprot", operation: "get_entry", status: "ok", latency_ms: 800, request_id: "r1", error: null, data: {}, fetched_at: "" },
      { provider: "esm_atlas", operation: "fold_sequence", status: "ok", latency_ms: 900, request_id: "r2", error: null, data: "ATOM", fetched_at: "" },
      { provider: "iedb", operation: "search_epitopes_by_source_accession", status: "ok", latency_ms: 200, request_id: "r3", error: null, data: [], fetched_at: "" },
      { provider: "europe_pmc", operation: "search", status: "ok", latency_ms: 600, request_id: "r4", error: null, data: {}, fetched_at: "" },
    ],
    evidence: [
      { evidence_id: "ev-1", source: "uniprot", source_type: "database", identifier: "P0DTC2", claim: "resolves", evidence_type: "curated_annotation", evidence_level: "curated", directness: "direct", confidence: null, source_url: "https://www.uniprot.org/uniprotkb/P0DTC2", retrieved_at: "", metadata: {} },
      { evidence_id: "ev-2", source: "esm_atlas", source_type: "prediction", identifier: null, claim: "folded", evidence_type: "predicted_structure", evidence_level: "predicted", directness: "direct", confidence: 91.2, source_url: null, retrieved_at: "", metadata: {} },
    ],
    errors: [],
    claims: [
      { claim_id: "c1", statement: "Sequence identity was resolved", supporting_evidence_ids: ["ev-1"], conflicting_evidence_ids: [], agreement: "agree", notes: "" },
    ],
    conflicts: [],
    evidence_score: 1.0,
    missing_evidence: [],
    status: "supported",
    trace: [
      makeTrace({ node: "sequence_intake" }),
      makeTrace({ node: "research_planner" }),
      makeTrace({ node: "identity_resolution" }),
      makeTrace({ node: "structure_prediction" }),
      makeTrace({ node: "epitope_evidence" }),
      makeTrace({ node: "literature_check" }),
      makeTrace({ node: "evidence_normalization" }),
      makeTrace({ node: "evidence_adjudication" }),
      makeTrace({ node: "confidence_gate" }),
      makeTrace({ node: "dossier_generation" }),
    ],
    dossier: makeDossier(),
    ai_synthesis: null,
    ...overrides,
  };
}

export function makeEvaluationReport(overrides: Partial<EvaluationReport> = {}): EvaluationReport {
  return {
    run_timestamp: "2026-01-01T00:00:00Z",
    cases_evaluated: 6,
    scenarios_evaluated: 8,
    metrics: {
      source_retrieval_success: 1.0,
      provenance_validity: 1.0,
      evidence_grounding_rate: 1.0,
      evidence_type_correctness: 1.0,
      cross_source_consistency: 1.0,
      conflict_detection: 1.0,
      abstention_correctness: 1.0,
      tool_recovery_success: 1.0,
      unsupported_claim_rate: 0.0,
      end_to_end_success: 1.0,
    },
    metrics_detail: {},
    identity_evaluation_breakdown: {},
    cases: [],
    reliability_scenarios: [],
    limitations: [],
    ...overrides,
  };
}
