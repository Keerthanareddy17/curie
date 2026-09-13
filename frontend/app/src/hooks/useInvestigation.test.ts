import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useInvestigation } from "./useInvestigation";
import * as api from "../lib/api";
import { makeInvestigationState } from "../test/fixtures";

describe("useInvestigation", () => {
  it("posts, then polls until a terminal status, then stops", async () => {
    vi.spyOn(api, "createInvestigation").mockResolvedValue({ run_id: "inv-1" });
    const getSpy = vi
      .spyOn(api, "getInvestigation")
      .mockResolvedValueOnce({ run_id: "inv-1", status: "pending" })
      .mockResolvedValueOnce(makeInvestigationState({ run_id: "inv-1", status: "collecting" }))
      .mockResolvedValueOnce(makeInvestigationState({ run_id: "inv-1", status: "supported" }));

    const { result } = renderHook(() => useInvestigation());

    await act(async () => {
      await result.current.start("MKV", null);
    });

    expect(result.current.phase).toBe("running");
    expect(result.current.runId).toBe("inv-1");

    await waitFor(() => expect(result.current.phase).toBe("done"), { timeout: 5000 });
    expect(result.current.state?.status).toBe("supported");

    // Polling must stop at the terminal state — no further calls after it settles.
    const callsAtDone = getSpy.mock.calls.length;
    await new Promise((r) => setTimeout(r, 1500));
    expect(getSpy.mock.calls.length).toBe(callsAtDone);
  }, 10000);

  it("surfaces a submission error instead of silently failing", async () => {
    vi.spyOn(api, "createInvestigation").mockRejectedValue(new Error("backend unreachable"));
    const { result } = renderHook(() => useInvestigation());

    await act(async () => {
      await result.current.start("MKV", null);
    });

    expect(result.current.phase).toBe("error");
    expect(result.current.error).toMatch(/backend unreachable/);
  });
});
