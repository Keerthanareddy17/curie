import { Minus, Check, X } from "lucide-react";
import type { AgreementLevel, InvestigationState } from "../types";

const COLUMNS = [
  { key: "uniprot", label: "UniProt" },
  { key: "iedb", label: "IEDB" },
  { key: "europe_pmc", label: "Literature" },
  { key: "esm_atlas", label: "Structure" },
] as const;

const AGREEMENT_LABEL: Record<AgreementLevel, string> = {
  agree: "Supported",
  conflict: "Conflicting",
  partial: "Partial",
  unverifiable: "Unverifiable",
};

const AGREEMENT_COLOR: Record<AgreementLevel, string> = {
  agree: "text-emerald-400",
  conflict: "text-red",
  partial: "text-amber",
  unverifiable: "text-muted-ink",
};

/** Every ✓ here is derived from real evidence_ids on the claim, cross-referenced
 * against real EvidenceRecord.source — nothing is inferred or assumed. */
export function EvidenceMatrix({ state }: { state: InvestigationState }) {
  if (state.claims.length === 0) {
    return <p className="text-[11px] text-muted-ink py-4 text-center">No adjudication claims produced yet.</p>;
  }

  const evidenceById = new Map(state.evidence.map((e) => [e.evidence_id, e]));

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="border-b border-line text-left">
            <th className="py-1.5 pr-3 font-mono uppercase text-[9px] tracking-wider text-muted-ink">Claim</th>
            {COLUMNS.map((c) => (
              <th key={c.key} className="py-1.5 px-2 font-mono uppercase text-[9px] tracking-wider text-muted-ink text-center">
                {c.label}
              </th>
            ))}
            <th className="py-1.5 pl-2 font-mono uppercase text-[9px] tracking-wider text-muted-ink text-right">Result</th>
          </tr>
        </thead>
        <tbody>
          {state.claims.map((claim) => {
            const relatedIds = [...claim.supporting_evidence_ids, ...claim.conflicting_evidence_ids];
            const relatedSources = new Set(
              relatedIds.map((id) => evidenceById.get(id)?.source).filter(Boolean) as string[]
            );
            return (
              <tr key={claim.claim_id} className="border-b border-line/50">
                <td className="py-1.5 pr-3 text-ink">{claim.statement}</td>
                {COLUMNS.map((c) => (
                  <td key={c.key} className="py-1.5 px-2 text-center">
                    {relatedSources.has(c.key) ? (
                      claim.agreement === "conflict" ? (
                        <X className="w-3 h-3 text-red inline" />
                      ) : (
                        <Check className="w-3 h-3 text-emerald-400 inline" />
                      )
                    ) : (
                      <Minus className="w-3 h-3 text-muted-ink/30 inline" />
                    )}
                  </td>
                ))}
                <td className={`py-1.5 pl-2 text-right font-semibold ${AGREEMENT_COLOR[claim.agreement]}`}>
                  {AGREEMENT_LABEL[claim.agreement]}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
