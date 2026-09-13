import { FlaskConical, Play } from "lucide-react";
import type { SequenceType } from "../types";

// The RBD fragment used throughout curie/evaluation/datasets/cases.json —
// same golden-path sequence exercised by the reliability evaluation, real
// UniProt sequence (residues 319-541 of P0DTC2), not invented for the UI.
export const DEMO_SEQUENCE =
  "RVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKCYGVSPTKLND" +
  "LCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNNLDSKVGGNYNYLYRLFRKSN" +
  "LKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTNGVGYQPYRVVVLSFELLHAPATVCGPKKST" +
  "NLVKNKCVNF";
export const DEMO_ACCESSION_HINT = "P0DTC2";

interface Props {
  sequence: string;
  onSequenceChange: (v: string) => void;
  accessionHint: string;
  onAccessionHintChange: (v: string) => void;
  onInvestigate: () => void;
  onLoadDemo: () => void;
  onRunGoldenPath: () => void;
  busy: boolean;
  detectedType?: SequenceType;
  normalizedLength?: number;
}

export function SequenceInput({
  sequence,
  onSequenceChange,
  accessionHint,
  onAccessionHintChange,
  onInvestigate,
  onLoadDemo,
  onRunGoldenPath,
  busy,
  detectedType,
  normalizedLength,
}: Props) {
  const canSubmit = sequence.trim().length > 0 && !busy;

  return (
    <div className="bg-panel-light border border-line rounded-xl p-4 flex flex-col gap-3 h-full">
      <div>
        <h2 className="text-xs font-bold uppercase tracking-wider text-ink flex items-center gap-1.5">
          <FlaskConical className="w-3.5 h-3.5 text-teal" /> Sequence / target
        </h2>
        <p className="text-[10.5px] text-muted-ink mt-0.5">
          Protein, DNA, or RNA — FASTA header optional.
        </p>
      </div>

      <textarea
        value={sequence}
        onChange={(e) => onSequenceChange(e.target.value)}
        rows={6}
        disabled={busy}
        placeholder="Paste an amino acid or nucleotide sequence..."
        className="w-full text-[11px] p-3 rounded-lg bg-panel border border-line-strong focus:border-teal/50 text-ink font-mono focus:outline-none resize-none disabled:opacity-60"
      />

      <div className="flex items-center gap-2">
        <label className="text-[10px] font-mono uppercase tracking-wider text-muted-ink whitespace-nowrap">
          Accession hint
        </label>
        <input
          type="text"
          value={accessionHint}
          onChange={(e) => onAccessionHintChange(e.target.value)}
          disabled={busy}
          placeholder="optional, e.g. P0DTC2"
          className="flex-1 text-[11px] px-2 py-1.5 rounded-md bg-panel border border-line-strong focus:border-teal/50 text-ink font-mono focus:outline-none disabled:opacity-60"
        />
      </div>
      <p className="text-[9.5px] text-muted-ink -mt-1.5 leading-snug">
        Optional. curie does not perform sequence-homology search — without a
        hint, identity stays <span className="font-mono">UNRESOLVED</span> (a
        correct, not a failed, outcome).
      </p>

      {(detectedType || normalizedLength !== undefined) && (
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div className="bg-panel border border-line rounded-md px-2 py-1.5">
            <span className="text-muted-ink uppercase block text-[8.5px] tracking-wide">Detected type</span>
            <span className="text-ink font-bold">{detectedType ?? "—"}</span>
          </div>
          <div className="bg-panel border border-line rounded-md px-2 py-1.5">
            <span className="text-muted-ink uppercase block text-[8.5px] tracking-wide">Normalized length</span>
            <span className="text-ink font-bold">{normalizedLength ?? "—"} aa</span>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-2 mt-auto pt-1">
        <button
          onClick={onInvestigate}
          disabled={!canSubmit}
          className="w-full py-2.5 rounded-lg bg-teal text-[#04211d] font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-teal/90 transition-colors"
        >
          <Play className="w-3.5 h-3.5" /> Investigate
        </button>
        <details className="group">
          <summary className="text-[9px] font-mono uppercase tracking-wider text-muted-ink/70 hover:text-muted-ink cursor-pointer select-none list-none text-center">
            Example target ▾
          </summary>
          <div className="flex gap-2 mt-1.5">
            <button
              onClick={onLoadDemo}
              disabled={busy}
              className="flex-1 py-1.5 rounded-md border border-line text-[9.5px] font-mono uppercase tracking-wider text-muted-ink hover:text-ink hover:border-line-strong disabled:opacity-40 transition-colors"
            >
              Load demo sequence
            </button>
            <button
              onClick={onRunGoldenPath}
              disabled={busy}
              className="flex-1 py-1.5 rounded-md border border-line text-[9.5px] font-mono uppercase tracking-wider text-muted-ink hover:text-ink hover:border-line-strong disabled:opacity-40 transition-colors"
            >
              Run golden path
            </button>
          </div>
        </details>
      </div>
    </div>
  );
}
