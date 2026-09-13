import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EvidenceMatrix } from "./EvidenceMatrix";
import { makeInvestigationState } from "../test/fixtures";

describe("EvidenceMatrix", () => {
  it("shows a message when there are no claims", () => {
    render(<EvidenceMatrix state={makeInvestigationState({ claims: [] })} />);
    expect(screen.getByText(/no adjudication claims produced/i)).toBeInTheDocument();
  });

  it("renders a row per real claim with its statement and result", () => {
    render(<EvidenceMatrix state={makeInvestigationState()} />);
    expect(screen.getByText("Sequence identity was resolved")).toBeInTheDocument();
    expect(screen.getByText("Supported")).toBeInTheDocument();
  });

  it("marks a conflicting claim as Conflicting, not Supported", () => {
    const state = makeInvestigationState({
      claims: [
        {
          claim_id: "c2",
          statement: "UniProt and IEDB describe the same source protein",
          supporting_evidence_ids: [],
          conflicting_evidence_ids: ["ev-1"],
          agreement: "conflict",
          notes: "",
        },
      ],
    });
    render(<EvidenceMatrix state={state} />);
    expect(screen.getByText("Conflicting")).toBeInTheDocument();
  });
});
