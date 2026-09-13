import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentActivity } from "./AgentActivity";
import { makeInvestigationState, makeTrace } from "../test/fixtures";

describe("AgentActivity", () => {
  it("shows an idle message when there is no state yet", () => {
    render(<AgentActivity state={null} running={false} />);
    expect(screen.getByText(/agent activity will appear here/i)).toBeInTheDocument();
  });

  it("shows a starting indicator while running with no state yet", () => {
    render(<AgentActivity state={null} running={true} />);
    expect(screen.getByText(/starting investigation/i)).toBeInTheDocument();
  });

  it("renders real trace events, not placeholders", () => {
    const state = makeInvestigationState();
    render(<AgentActivity state={state} running={false} />);
    expect(screen.getByText("Sequence validated")).toBeInTheDocument();
    expect(screen.getByText("Planning investigation")).toBeInTheDocument();
    expect(screen.getByText("Dossier generated")).toBeInTheDocument();
  });

  it("renders tool statuses for all four evidence-collection providers", () => {
    const state = makeInvestigationState();
    render(<AgentActivity state={state} running={false} />);
    expect(screen.getByText("UniProt")).toBeInTheDocument();
    expect(screen.getByText("IEDB")).toBeInTheDocument();
    expect(screen.getByText("Europe PMC")).toBeInTheDocument();
    expect(screen.getByText("ESM Atlas")).toBeInTheDocument();
  });

  it("shows a step as not-yet-run when no trace event exists for it", () => {
    const state = makeInvestigationState({ trace: [makeTrace({ node: "sequence_intake" })] });
    render(<AgentActivity state={state} running={false} />);
    const planning = screen.getByText("Planning investigation");
    expect(planning.className).toMatch(/muted-ink/);
  });
});
