import { Microscope } from "lucide-react";
import type { InvestigationStatusValue } from "../types";
import { STATUS_COLOR, STATUS_LABEL } from "../lib/statusMeta";

export function Header({ status }: { status: InvestigationStatusValue | null }) {
  return (
    <header className="w-full border-b border-line bg-panel px-6 py-3 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <Microscope className="w-5 h-5 text-teal" />
        <div className="leading-tight">
          <div className="flex items-baseline gap-2">
            <h1 className="text-base font-bold tracking-tight text-ink">curie</h1>
            <span className="text-[10px] text-muted-ink hidden sm:inline">
              Evidence-aware biological research agent
            </span>
          </div>
        </div>
        <span className="text-[9px] font-mono uppercase tracking-wider text-amber border border-amber/30 bg-amber/5 rounded px-1.5 py-0.5">
          Research use only
        </span>
      </div>

      {status && (
        <div
          className={`flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider border rounded-full px-2.5 py-1 ${STATUS_COLOR[status]}`}
        >
          <span className="relative flex h-1.5 w-1.5">
            {(status === "planning" || status === "collecting" || status === "adjudicating") && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-60" />
            )}
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current" />
          </span>
          Investigation {STATUS_LABEL[status]}
        </div>
      )}
    </header>
  );
}
