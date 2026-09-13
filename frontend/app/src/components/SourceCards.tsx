import { ChevronDown, ExternalLink } from "lucide-react";
import type { InvestigationState } from "../types";
import { TOOL_STATUS_COLOR, TOOL_STATUS_LABEL } from "../lib/statusMeta";

function Card({ title, statusLabel, statusClass, children }: {
  title: string;
  statusLabel: string;
  statusClass: string;
  children: React.ReactNode;
}) {
  return (
    <details className="group bg-panel border border-line rounded-lg" open>
      <summary className="flex items-center justify-between px-3 py-2 cursor-pointer select-none list-none">
        <span className="text-[11px] font-bold text-ink">{title}</span>
        <div className="flex items-center gap-2">
          <span className={`text-[9px] font-mono uppercase tracking-wider border rounded px-1.5 py-0.5 ${statusClass}`}>
            {statusLabel}
          </span>
          <ChevronDown className="w-3 h-3 text-muted-ink group-open:rotate-180 transition-transform" />
        </div>
      </summary>
      <div className="px-3 pb-2.5 text-[10.5px] text-muted-ink space-y-1">{children}</div>
    </details>
  );
}

export function SourceCards({ state }: { state: InvestigationState }) {
  const uniprotResult = [...state.tool_results].reverse().find((r) => r.provider === "uniprot");
  const iedbResult = [...state.tool_results].reverse().find((r) => r.provider === "iedb");
  const pmcResult = [...state.tool_results].reverse().find((r) => r.provider === "europe_pmc");
  const esmResult = [...state.tool_results].reverse().find((r) => r.provider === "esm_atlas");

  const uniprotEvidence = state.evidence.find((e) => e.source === "uniprot" && e.evidence_type !== "absence_of_evidence");
  const iedbEvidence = state.evidence.find((e) => e.source === "iedb" && e.evidence_type === "curated_epitope");
  const literatureEvidence = state.evidence.filter((e) => e.evidence_type === "literature");
  const structureEvidence = state.evidence.find((e) => e.evidence_type === "predicted_structure");

  const candidate = state.candidate_proteins[0];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
      <Card
        title="UniProt"
        statusLabel={uniprotResult ? TOOL_STATUS_LABEL[uniprotResult.status] : "NOT CALLED"}
        statusClass={uniprotResult ? TOOL_STATUS_COLOR[uniprotResult.status] : "text-muted-ink border-line-strong"}
      >
        {candidate ? (
          <>
            <div>
              <span className="text-muted-ink">Accession: </span>
              <span className="text-ink font-mono">{candidate.accession}</span>
            </div>
            <div>
              <span className="text-muted-ink">Name: </span>
              <span className="text-ink">{candidate.name ?? "—"}</span>
            </div>
            <div>
              <span className="text-muted-ink">Organism: </span>
              <span className="text-ink">{candidate.organism ?? "—"}</span>
            </div>
            {uniprotEvidence?.source_url && (
              <a
                href={uniprotEvidence.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-teal inline-flex items-center gap-1 hover:underline"
              >
                View on UniProt <ExternalLink className="w-2.5 h-2.5" />
              </a>
            )}
          </>
        ) : (
          <p>{state.identity_status === "unresolved" ? "No accession hint supplied — identity unresolved." : "Not called."}</p>
        )}
      </Card>

      <Card
        title="IEDB"
        statusLabel={iedbResult ? TOOL_STATUS_LABEL[iedbResult.status] : "NOT CALLED"}
        statusClass={iedbResult ? TOOL_STATUS_COLOR[iedbResult.status] : "text-muted-ink border-line-strong"}
      >
        {iedbEvidence ? (
          <>
            <div>
              <span className="text-muted-ink">Curated epitope records: </span>
              <span className="text-ink font-mono">{String(iedbEvidence.metadata.epitope_count ?? "—")}</span>
            </div>
            <div>
              <span className="text-muted-ink">Evidence level: </span>
              <span className="text-ink">curated (not predicted)</span>
            </div>
            <div>
              <span className="text-muted-ink">Source antigen: </span>
              <span className="text-ink font-mono">{iedbEvidence.identifier}</span>
            </div>
          </>
        ) : (
          <p>{iedbResult?.error ?? "No curated epitope evidence for this run."}</p>
        )}
      </Card>

      <Card
        title="Europe PMC"
        statusLabel={pmcResult ? TOOL_STATUS_LABEL[pmcResult.status] : "NOT CALLED"}
        statusClass={pmcResult ? TOOL_STATUS_COLOR[pmcResult.status] : "text-muted-ink border-line-strong"}
      >
        {literatureEvidence.length > 0 ? (
          <ul className="space-y-1.5">
            {literatureEvidence.slice(0, 3).map((e) => (
              <li key={e.evidence_id} className="border-t border-line/50 pt-1 first:border-0 first:pt-0">
                <div className="text-ink">{String(e.metadata.title ?? e.claim)}</div>
                <div className="flex items-center gap-2 text-[9.5px]">
                  <span>{e.identifier ? `PMID ${e.identifier}` : "no identifier"}</span>
                  {e.metadata.pub_year ? <span>· {String(e.metadata.pub_year)}</span> : null}
                  <span className="uppercase text-amber">{e.directness} (name-matched, not exact-sequence)</span>
                </div>
                {e.source_url && (
                  <a href={e.source_url} target="_blank" rel="noreferrer" className="text-teal hover:underline text-[9.5px]">
                    view article
                  </a>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p>{pmcResult?.error ?? "No literature evidence for this run."}</p>
        )}
      </Card>

      <Card
        title="ESM Atlas"
        statusLabel={esmResult ? TOOL_STATUS_LABEL[esmResult.status] : "NOT CALLED"}
        statusClass={esmResult ? TOOL_STATUS_COLOR[esmResult.status] : "text-muted-ink border-line-strong"}
      >
        {structureEvidence ? (
          <>
            <div>
              <span className="text-muted-ink">Confidence: </span>
              <span className="text-ink font-mono">
                {structureEvidence.confidence != null ? `${structureEvidence.confidence.toFixed(1)} pLDDT` : "n/a"}
              </span>
            </div>
            <div className="text-[9.5px]">Predicted structure — not experimental.</div>
          </>
        ) : (
          <p>{esmResult?.error ?? "No structure prediction for this run."}</p>
        )}
      </Card>
    </div>
  );
}
