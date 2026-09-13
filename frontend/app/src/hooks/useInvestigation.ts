import { useCallback, useRef, useState } from "react";
import { createInvestigation, getInvestigation, isTerminalStatus } from "../lib/api";
import type { InvestigationState, PendingInvestigation } from "../types";

export type InvestigationPhase = "idle" | "starting" | "running" | "done" | "error";

const POLL_INTERVAL_MS = 1200;

function isPendingResult(x: InvestigationState | PendingInvestigation): x is PendingInvestigation {
  return (x as PendingInvestigation).status === "pending" && !("evidence" in x);
}

/**
 * Drives POST /api/investigations then polls GET /api/investigations/{id}
 * until a terminal status, per Phase 4 spec section 3/23: never recreate
 * backend logic client-side, never fabricate progress, stop polling exactly
 * at a terminal state rather than a fixed timeout.
 */
export function useInvestigation() {
  const [phase, setPhase] = useState<InvestigationPhase>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [state, setState] = useState<InvestigationState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const activeRunRef = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback((id: string) => {
    const tick = async () => {
      if (activeRunRef.current !== id) return; // superseded by a newer run
      try {
        const result = await getInvestigation(id);
        if (activeRunRef.current !== id) return;
        if (isPendingResult(result)) {
          timerRef.current = window.setTimeout(tick, POLL_INTERVAL_MS);
          return;
        }
        setState(result);
        if (isTerminalStatus(result.status)) {
          setPhase("done");
        } else {
          timerRef.current = window.setTimeout(tick, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (activeRunRef.current !== id) return;
        setError(err instanceof Error ? err.message : String(err));
        setPhase("error");
      }
    };
    tick();
  }, []);

  const start = useCallback(
    async (sequence: string, accessionHint?: string | null) => {
      stopPolling();
      setError(null);
      setState(null);
      setPhase("starting");
      try {
        const { run_id } = await createInvestigation(sequence, accessionHint);
        activeRunRef.current = run_id;
        setRunId(run_id);
        setPhase("running");
        poll(run_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        setPhase("error");
      }
    },
    [poll, stopPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    activeRunRef.current = null;
    setPhase("idle");
    setRunId(null);
    setState(null);
    setError(null);
  }, [stopPolling]);

  return { phase, runId, state, error, start, reset };
}
