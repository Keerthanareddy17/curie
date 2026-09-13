import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DossierView } from "./DossierView";
import { makeDossier } from "../test/fixtures";

describe("DossierView", () => {
  it("renders the core dossier sections from real data", () => {
    render(<DossierView dossier={makeDossier()} />);
    expect(screen.getByText(/research dossier/i)).toBeInTheDocument();
    expect(screen.getByText("223-residue protein sequence")).toBeInTheDocument();
    expect(screen.getByText(/resolved via supplied accession hint/i)).toBeInTheDocument();
    expect(screen.getByText("1.00")).toBeInTheDocument();
  });

  it("never renders clinical or therapeutic language", () => {
    render(<DossierView dossier={makeDossier()} />);
    const text = document.body.textContent ?? "";
    expect(text.toLowerCase()).not.toMatch(/therapeutic recommendation|vaccine is validated|wet-lab protocol/);
  });

  it("renders conflicts section only when conflicts exist", () => {
    const { rerender } = render(<DossierView dossier={makeDossier({ conflicts: [] })} />);
    expect(screen.queryByText(/^conflicts$/i)).not.toBeInTheDocument();

    rerender(
      <DossierView
        dossier={makeDossier({
          conflicts: [
            {
              conflict_id: "cf1",
              claim: "identity mismatch",
              evidence_a: "ev-1",
              evidence_b: "ev-2",
              conflict_type: "cross_source_disagreement",
              severity: "high",
              resolved: false,
              notes: "",
            },
          ],
        })}
      />
    );
    expect(screen.getByText(/identity mismatch/i)).toBeInTheDocument();
  });
});
