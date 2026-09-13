import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultPanel } from "./ResultPanel";
import { makeInvestigationState } from "../test/fixtures";

describe("ResultPanel", () => {
  it("shows the real evidence score and status, never a probability phrasing", () => {
    render(<ResultPanel state={makeInvestigationState({ evidence_score: 0.82, status: "supported" })} />);
    expect(screen.getByText("0.82")).toBeInTheDocument();
    expect(screen.getByText("SUPPORTED")).toBeInTheDocument();
    // The disclaimer is allowed to use the word "probability" to explain the
    // score is NOT one — what must never appear is the score presented AS one.
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/82%\s*(certain|probability|likely)/i);
    expect(text).not.toMatch(/0\.82\s*probability of/i);
  });

  it("renders conflicts prominently when present", () => {
    const state = makeInvestigationState({
      status: "conflicting",
      conflicts: [
        {
          conflict_id: "cf1",
          claim: "UniProt and IEDB disagree on identity",
          evidence_a: "ev-1",
          evidence_b: "ev-2",
          conflict_type: "cross_source_disagreement",
          severity: "high",
          resolved: false,
          notes: "",
        },
      ],
    });
    render(<ResultPanel state={state} />);
    expect(screen.getByText(/evidence conflict detected/i)).toBeInTheDocument();
    expect(screen.getByText("UniProt and IEDB disagree on identity")).toBeInTheDocument();
  });

  it("does not render a conflict panel when there are no conflicts", () => {
    render(<ResultPanel state={makeInvestigationState({ conflicts: [] })} />);
    expect(screen.queryByText(/evidence conflict detected/i)).not.toBeInTheDocument();
  });

  it("renders the abstention message for INSUFFICIENT_EVIDENCE, not an error state", () => {
    const state = makeInvestigationState({
      status: "insufficient_evidence",
      missing_evidence: ["identity is unresolved"],
    });
    render(<ResultPanel state={state} />);
    expect(screen.getByText(/curie abstained from a conclusion/i)).toBeInTheDocument();
    expect(screen.getByText("identity is unresolved")).toBeInTheDocument();
    expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
  });

  it("does not render the abstention panel for a supported result", () => {
    render(<ResultPanel state={makeInvestigationState({ status: "supported" })} />);
    expect(screen.queryByText(/abstained/i)).not.toBeInTheDocument();
  });
});
