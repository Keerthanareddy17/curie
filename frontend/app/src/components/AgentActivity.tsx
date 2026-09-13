import { Check, CircleDashed, Loader2, X } from "lucide-react";
import type { InvestigationState, ToolResult, TraceEvent } from "../types";
import { PROVIDER_LABEL, TOOL_STATUS_COLOR, TOOL_STATUS_LABEL, formatSeconds } from "../lib/statusMeta";

const PRE_NODES: Array<{ node: string; label: string }> = [
  { node: "sequence_intake", label: "Sequence validated" },
  { node: "research_planner", label: "Planning investigation" },
  { node: "identity_resolution", label: "Identity resolution" },
];

const EVIDENCE_PROVIDERS = ["uniprot", "iedb", "europe_pmc", "esm_atlas"];

const POST_NODES: Array<{ node: string; label: string }> = [
  { node: "evidence_normalization", label: "Evidence normalization" },
  { node: "evidence_adjudication", label: "Evidence adjudication" },
  { node: "confidence_gate", label: "Confidence gate" },
  { node: "gemini_synthesis", label: "Gemini synthesis" },
  { node: "dossier_generation", label: "Dossier generated" },
];

function findTrace(trace: TraceEvent[], node: string): TraceEvent | undefined {
  return trace.find((t) => t.node === node);
}

function findTool(results: ToolResult[], provider: string): ToolResult | undefined {
  return [...results].reverse().find((r) => r.provider === provider);
}

function StepIcon({ trace }: { trace?: TraceEvent }) {
  if (!trace) return <CircleDashed className="w-3.5 h-3.5 text-muted-ink/50" />;
  if (trace.status === "ok") return <Check className="w-3.5 h-3.5 text-emerald-400" />;
  if (trace.status === "skipped") return <CircleDashed className="w-3.5 h-3.5 text-muted-ink" />;
  return <X className="w-3.5 h-3.5 text-red" />;
}

function TraceRow({ label, trace }: { label: string; trace?: TraceEvent }) {
  const geminiAssisted = trace?.tools_called.includes("gemini");
  return (
    <div className="flex items-center gap-2 py-1">
      <StepIcon trace={trace} />
      <span className={`text-[11px] flex-1 ${trace ? "text-ink" : "text-muted-ink/60"}`}>
        {label}
        {geminiAssisted && <span className="text-teal text-[9px] font-mono uppercase ml-1.5">· gemini</span>}
      </span>
      {trace && <span className="text-[9.5px] font-mono text-muted-ink">{formatSeconds(trace.duration_ms)}</span>}
    </div>
  );
}

export function AgentActivity({ state, running }: { state: InvestigationState | null; running: boolean }) {
  if (!state) {
    return (
      <div className="text-[11px] text-muted-ink flex items-center gap-2 py-6 justify-center">
        {running ? (
          <>
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Starting investigation...
          </>
        ) : (
          "Agent activity will appear here once an investigation starts."
        )}
      </div>
    );
  }

  const trace = state.trace;

  return (
    <div className="flex flex-col gap-1">
      {PRE_NODES.map(({ node, label }) => (
        <TraceRow key={node} label={label} trace={findTrace(trace, node)} />
      ))}

      <div className="my-1.5 pt-1.5 border-t border-line">
        <div className="text-[9px] font-mono uppercase tracking-wider text-muted-ink mb-1.5">
          Evidence collection — independent sources, called concurrently
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {EVIDENCE_PROVIDERS.map((provider) => {
            const result = findTool(state.tool_results, provider);
            return (
              <div
                key={provider}
                className={`border rounded-md px-2 py-1.5 flex items-center justify-between text-[10px] ${
                  result ? TOOL_STATUS_COLOR[result.status] : "text-muted-ink/50 border-line-strong"
                }`}
              >
                <span className="font-semibold">{PROVIDER_LABEL[provider]}</span>
                <span className="font-mono text-[9px]">
                  {result ? `${TOOL_STATUS_LABEL[result.status]} ${formatSeconds(result.latency_ms)}` : "—"}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-[9px] text-muted-ink mt-1 leading-snug">
          UniProt and ESM Atlas run independently of each other; IEDB and
          Europe PMC run independently of each other but depend on identity
          resolution's output (see docs/ARCHITECTURE.md).
        </p>
      </div>

      <div className="pt-1 border-t border-line">
        {POST_NODES.map(({ node, label }) => (
          <TraceRow key={node} label={label} trace={findTrace(trace, node)} />
        ))}
      </div>
    </div>
  );
}
