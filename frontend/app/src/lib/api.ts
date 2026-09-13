import type {
  Dossier,
  EvaluationReport,
  InvestigationState,
  PendingInvestigation,
  TraceEvent,
} from "../types";

// Local dev default: Vite (5173) and uvicorn (8000) run as separate origins.
// In production this MUST be set to the deployed backend's public URL
// (e.g. https://curie-backend.onrender.com) via the VITE_API_BASE_URL build
// env var — Vercel does not serve the FastAPI backend, so there is no
// same-origin fallback in production.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch (err) {
    throw new ApiError(
      `Could not reach the curie backend at ${API_BASE}. Is it running? (${(err as Error).message})`,
      0
    );
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON; keep statusText
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export function checkHealth(): Promise<{ status: string; version: string; time: string }> {
  return request("/api/health");
}

export function createInvestigation(sequence: string, accessionHint?: string | null): Promise<{ run_id: string }> {
  return request("/api/investigations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sequence, accession_hint: accessionHint ?? null }),
  });
}

export function getInvestigation(runId: string): Promise<InvestigationState | PendingInvestigation> {
  return request(`/api/investigations/${runId}`);
}

export function getTrace(runId: string): Promise<TraceEvent[]> {
  return request(`/api/investigations/${runId}/trace`);
}

export function getDossier(runId: string): Promise<Dossier> {
  return request(`/api/investigations/${runId}/dossier`);
}

export function getLatestEvaluation(): Promise<EvaluationReport> {
  return request("/api/evaluation/latest");
}

const TERMINAL_STATUSES = new Set([
  "supported",
  "partially_supported",
  "conflicting",
  "insufficient_evidence",
  "failed",
]);

export function isTerminalStatus(status: string): boolean {
  return TERMINAL_STATUSES.has(status);
}
