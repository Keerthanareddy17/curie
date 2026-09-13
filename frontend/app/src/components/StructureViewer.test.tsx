import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StructureViewer } from "./StructureViewer";
import { makeInvestigationState } from "../test/fixtures";

describe("StructureViewer — missing/degraded structure states", () => {
  it("shows an idle empty state before any investigation runs", () => {
    render(<StructureViewer state={null} />);
    expect(screen.getByText(/no investigation running/i)).toBeInTheDocument();
  });

  it("shows a pending state when esm_atlas has not been called yet", () => {
    const state = makeInvestigationState({ tool_results: [] });
    render(<StructureViewer state={state} />);
    expect(screen.getByText(/structure pending/i)).toBeInTheDocument();
  });

  it("shows an unavailable state, with the tool status, when ESM Atlas was skipped", () => {
    const state = makeInvestigationState({
      tool_results: [
        { provider: "esm_atlas", operation: "fold_sequence", status: "skipped", latency_ms: 0, request_id: "r", error: "sequence exceeds supported fold length", data: null, fetched_at: "" },
      ],
    });
    render(<StructureViewer state={state} />);
    expect(screen.getByText(/structure unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/esm_atlas: skipped/i)).toBeInTheDocument();
    expect(screen.getByText(/exceeds supported fold length/i)).toBeInTheDocument();
  });

  it("shows an unavailable state, never a fabricated structure, when ESM Atlas failed", () => {
    const state = makeInvestigationState({
      tool_results: [
        { provider: "esm_atlas", operation: "fold_sequence", status: "timeout", latency_ms: 60000, request_id: "r", error: "timed out after 60s", data: null, fetched_at: "" },
      ],
    });
    render(<StructureViewer state={state} />);
    expect(screen.getByText(/structure unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/timed out after 60s/i)).toBeInTheDocument();
  });
});
