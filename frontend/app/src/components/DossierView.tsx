import { FileText, Sparkles } from "lucide-react";
import type { Dossier } from "../types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line pt-2 first:border-0 first:pt-0">
      <div className="text-[9px] font-mono uppercase tracking-wider text-muted-ink mb-0.5">{title}</div>
      <div className="text-[11px] text-ink">{children}</div>
    </div>
  );
}

function EvidenceIdList({ ids }: { ids: string[] }) {
  if (ids.length === 0) return <span className="text-muted-ink">none</span>;
  return <span className="font-mono text-[10px] text-muted-ink">{ids.join(", ")}</span>;
}

export function DossierView({ dossier }: { dossier: Dossier }) {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-1.5 text-xs font-bold text-ink">
        <FileText className="w-3.5 h-3.5 text-teal" /> Research dossier
        <span className="text-[9px] font-mono text-muted-ink font-normal ml-auto">{dossier.investigation_id}</span>
      </div>

      {dossier.ai_synthesis && (
        <div className="border border-teal/30 bg-teal/5 rounded-lg p-2.5">
          <div className="flex items-center gap-1.5 text-[9px] font-mono uppercase tracking-wider text-teal mb-1">
            <Sparkles className="w-3 h-3" /> AI reasoning (Gemini) — interpretation, not retrieved evidence
          </div>
          <p className="text-[10.5px] text-ink leading-relaxed">{dossier.ai_synthesis}</p>
        </div>
      )}

      <Section title="Sequence summary">{dossier.sequence_summary}</Section>
      <Section title="Identity">{dossier.identity_result}</Section>
      <Section title="Structural evidence"><EvidenceIdList ids={dossier.structural_evidence} /></Section>
      <Section title="Epitope evidence"><EvidenceIdList ids={dossier.epitope_evidence} /></Section>
      <Section title="Literature evidence"><EvidenceIdList ids={dossier.literature_evidence} /></Section>
      <Section title="Cross-source agreement">{dossier.cross_source_agreement}</Section>

      {dossier.conflicts.length > 0 && (
        <Section title="Conflicts">
          {dossier.conflicts.map((c) => (
            <div key={c.conflict_id} className="text-[10.5px]">
              {c.claim} ({c.severity})
            </div>
          ))}
        </Section>
      )}

      {dossier.missing_evidence.length > 0 && (
        <Section title="Missing evidence">
          <ul className="list-disc list-inside space-y-0.5 text-[10.5px]">
            {dossier.missing_evidence.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Evidence score">{dossier.evidence_score.toFixed(2)}</Section>

      <Section title="Next research questions">
        <ul className="list-disc list-inside space-y-0.5 text-[10.5px]">
          {dossier.next_research_questions.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ul>
      </Section>

      <Section title="Limitations">
        <ul className="list-disc list-inside space-y-0.5 text-[10px] text-muted-ink">
          {dossier.limitations.map((l, i) => (
            <li key={i}>{l}</li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
