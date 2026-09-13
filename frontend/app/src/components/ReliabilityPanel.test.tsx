import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ReliabilityPanel } from "./ReliabilityPanel";
import { makeEvaluationReport } from "../test/fixtures";
import * as api from "../lib/api";

describe("ReliabilityPanel", () => {
  it("loads and renders real metrics from the evaluation artifact", async () => {
    vi.spyOn(api, "getLatestEvaluation").mockResolvedValue(makeEvaluationReport());
    render(<ReliabilityPanel />);

    await waitFor(() => expect(screen.getAllByText("100.0%").length).toBeGreaterThan(0));
    expect(screen.getByText(/evaluation benchmark/i)).toBeInTheDocument();
    expect(screen.getByText("0.0%")).toBeInTheDocument(); // unsupported_claim_rate
  });

  it("shows an explicit unavailable message, never fake numbers, when the artifact can't be loaded", async () => {
    vi.spyOn(api, "getLatestEvaluation").mockRejectedValue(new Error("404"));
    render(<ReliabilityPanel />);

    await waitFor(() => expect(screen.getByText(/evaluation results unavailable/i)).toBeInTheDocument());
    expect(screen.queryByText("100.0%")).not.toBeInTheDocument();
  });

  it("shows NOT EVALUATED for a null metric rather than a fabricated value", async () => {
    vi.spyOn(api, "getLatestEvaluation").mockResolvedValue(
      makeEvaluationReport({ metrics: { conflict_detection: null } })
    );
    render(<ReliabilityPanel />);

    await waitFor(() => expect(screen.getByText("NOT EVALUATED")).toBeInTheDocument());
  });
});
