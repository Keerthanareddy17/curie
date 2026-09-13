import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./lib/api";
import { makeEvaluationReport, makeInvestigationState } from "./test/fixtures";

// jsdom can't execute the CDN <script> injection Molecular3DVisualizer does
// to load 3Dmol.js/jQuery, and that's not what these tests are checking —
// they check that StructureViewer *decides* to mount it with real pdbData,
// which is what the app-level "does the 3D viewer get used" question is.
vi.mock("./components/Molecular3DVisualizer", () => ({
  default: (props: { pdbData?: string }) => (
    <div data-testid="mock-3d-viewer">{props.pdbData ? "rendering real pdb" : "no pdb"}</div>
  ),
}));

beforeEach(() => {
  vi.spyOn(api, "getLatestEvaluation").mockResolvedValue(makeEvaluationReport());
});

describe("App", () => {
  it("shows a clear backend-unavailable banner rather than a blank screen", async () => {
    vi.spyOn(api, "checkHealth").mockRejectedValue(new Error("connection refused"));
    render(<App />);
    await waitFor(() => expect(screen.getByText(/cannot reach the curie backend/i)).toBeInTheDocument());
  });

  it("does not show the backend-unavailable banner once health check succeeds", async () => {
    vi.spyOn(api, "checkHealth").mockResolvedValue({ status: "ok", version: "0.1.0", time: "" });
    render(<App />);
    await waitFor(() => expect(api.checkHealth).toHaveBeenCalled());
    expect(screen.queryByText(/cannot reach the curie backend/i)).not.toBeInTheDocument();
  });

  it("runs the golden path end to end: submits, polls, and renders the real terminal result", async () => {
    vi.spyOn(api, "checkHealth").mockResolvedValue({ status: "ok", version: "0.1.0", time: "" });
    const createSpy = vi.spyOn(api, "createInvestigation").mockResolvedValue({ run_id: "inv-gp" });
    vi.spyOn(api, "getInvestigation").mockResolvedValue(
      makeInvestigationState({ run_id: "inv-gp", status: "supported" })
    );

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /run golden path/i }));

    expect(createSpy).toHaveBeenCalledWith(expect.stringContaining("RVQPTESIVRFPNITNL"), "P0DTC2");

    await waitFor(() => expect(screen.getByText(/current investigation — run inv-gp/i)).toBeInTheDocument());
    expect(screen.getByTestId("mock-3d-viewer")).toHaveTextContent("rendering real pdb");
    expect(screen.getByText(/research dossier/i)).toBeInTheDocument();
  });

  it("shows a request-failure error rather than fake demo data", async () => {
    vi.spyOn(api, "checkHealth").mockResolvedValue({ status: "ok", version: "0.1.0", time: "" });
    vi.spyOn(api, "createInvestigation").mockRejectedValue(new Error("500 Internal Server Error"));

    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: /run golden path/i }));

    await waitFor(() => expect(screen.getByText(/500 Internal Server Error/)).toBeInTheDocument());
    expect(screen.queryByText(/research dossier/i)).not.toBeInTheDocument();
  });
});
