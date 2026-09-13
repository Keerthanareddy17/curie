import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SequenceInput } from "./SequenceInput";

function setup(overrides: Partial<React.ComponentProps<typeof SequenceInput>> = {}) {
  const props = {
    sequence: "",
    onSequenceChange: vi.fn(),
    accessionHint: "",
    onAccessionHintChange: vi.fn(),
    onInvestigate: vi.fn(),
    onLoadDemo: vi.fn(),
    onRunGoldenPath: vi.fn(),
    busy: false,
    ...overrides,
  };
  render(<SequenceInput {...props} />);
  return props;
}

describe("SequenceInput", () => {
  it("renders the sequence textarea and buttons", () => {
    setup();
    expect(screen.getByPlaceholderText(/paste an amino acid/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /investigate/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /load demo sequence/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /run golden path/i })).toBeInTheDocument();
  });

  it("disables Investigate when the sequence is empty", () => {
    setup({ sequence: "" });
    expect(screen.getByRole("button", { name: /investigate/i })).toBeDisabled();
  });

  it("enables Investigate once a sequence is present, and calls the handler on click", async () => {
    const props = setup({ sequence: "MKV" });
    const button = screen.getByRole("button", { name: /investigate/i });
    expect(button).toBeEnabled();
    await userEvent.click(button);
    expect(props.onInvestigate).toHaveBeenCalledOnce();
  });

  it("calls onLoadDemo when the demo button is clicked", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("button", { name: /load demo sequence/i }));
    expect(props.onLoadDemo).toHaveBeenCalledOnce();
  });

  it("calls onRunGoldenPath when the golden path button is clicked", async () => {
    const props = setup();
    await userEvent.click(screen.getByRole("button", { name: /run golden path/i }));
    expect(props.onRunGoldenPath).toHaveBeenCalledOnce();
  });

  it("disables all actions while busy", () => {
    setup({ sequence: "MKV", busy: true });
    expect(screen.getByRole("button", { name: /investigate/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /load demo sequence/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /run golden path/i })).toBeDisabled();
  });

  it("shows detected type and normalized length when provided", () => {
    setup({ detectedType: "protein", normalizedLength: 223 });
    expect(screen.getByText("protein")).toBeInTheDocument();
    expect(screen.getByText("223 aa")).toBeInTheDocument();
  });
});
