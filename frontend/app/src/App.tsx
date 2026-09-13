import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Header } from "./components/Header";
import { SequenceInput, DEMO_SEQUENCE, DEMO_ACCESSION_HINT } from "./components/SequenceInput";
import { AgentActivity } from "./components/AgentActivity";
import { StructureViewer } from "./components/StructureViewer";
import { EvidenceMatrix } from "./components/EvidenceMatrix";
import { SourceCards } from "./components/SourceCards";
import { ResultPanel } from "./components/ResultPanel";
import { ReliabilityPanel } from "./components/ReliabilityPanel";
import { HowCurieKnows } from "./components/HowCurieKnows";
import { DossierView } from "./components/DossierView";
import { useInvestigation } from "./hooks/useInvestigation";
import { checkHealth } from "./lib/api";

export default function App() {
  const [sequence, setSequence] = useState("");
  const [accessionHint, setAccessionHint] = useState("");
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const { phase, state, error, start } = useInvestigation();

  useEffect(() => {
    checkHealth()
      .then(() => setBackendUp(true))
      .catch(() => setBackendUp(false));
  }, []);

  const busy = phase === "starting" || phase === "running";

  const handleInvestigate = () => start(sequence, accessionHint || null);
  const handleLoadDemo = () => {
    setSequence(DEMO_SEQUENCE);
    setAccessionHint(DEMO_ACCESSION_HINT);
  };
  const handleGoldenPath = () => {
    setSequence(DEMO_SEQUENCE);
    setAccessionHint(DEMO_ACCESSION_HINT);
    start(DEMO_SEQUENCE, DEMO_ACCESSION_HINT);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header status={state?.status ?? null} />

      {backendUp === false && (
        <div className="bg-red/10 border-b border-red/40 text-red text-[11px] px-6 py-2 flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5" />
          Cannot reach the curie backend. Start it with{" "}
          <span className="font-mono">python -m curie serve</span> and reload.
        </div>
      )}
      {error && (
        <div className="bg-red/10 border-b border-red/40 text-red text-[11px] px-6 py-2 flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5" /> {error}
        </div>
      )}

      <main className="flex-1 max-w-[1400px] w-full mx-auto px-6 py-5 space-y-5">
        {/* Top: sequence input | 3D structure | agent activity */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-3">
            <SequenceInput
              sequence={sequence}
              onSequenceChange={setSequence}
              accessionHint={accessionHint}
              onAccessionHintChange={setAccessionHint}
              onInvestigate={handleInvestigate}
              onLoadDemo={handleLoadDemo}
              onRunGoldenPath={handleGoldenPath}
              busy={busy}
              detectedType={state?.sequence_type}
              normalizedLength={state?.normalized_sequence.length}
            />
          </div>

          <div className="lg:col-span-6 bg-panel-light border border-line rounded-xl p-4 min-h-[420px]">
            <StructureViewer state={state} />
          </div>

          <div className="lg:col-span-3 bg-panel-light border border-line rounded-xl p-4">
            <h2 className="text-xs font-bold uppercase tracking-wider text-ink mb-2">Agent activity</h2>
            <AgentActivity state={state} running={busy} />
          </div>
        </div>

        {state && (
          <section className="space-y-3">
            <div className="text-[9px] font-mono uppercase tracking-widest text-teal border-b border-teal/20 pb-1">
              Current investigation — run {state.run_id}
            </div>

            <ResultPanel state={state} />

            <div className="bg-panel-light border border-line rounded-xl p-4">
              <h3 className="text-xs font-bold text-ink uppercase tracking-wide mb-2">Evidence matrix</h3>
              <EvidenceMatrix state={state} />
            </div>

            <div className="bg-panel-light border border-line rounded-xl p-4">
              <h3 className="text-xs font-bold text-ink uppercase tracking-wide mb-2">Sources</h3>
              <SourceCards state={state} />
            </div>

            {state.dossier ? (
              <div className="bg-panel-light border border-line rounded-xl p-4">
                <DossierView dossier={state.dossier} />
              </div>
            ) : (
              phase === "done" && (
                <p className="text-[11px] text-amber">
                  Investigation completed without a dossier — this indicates a backend issue, not a normal outcome.
                </p>
              )
            )}
          </section>
        )}

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="text-[9px] font-mono uppercase tracking-widest text-muted-ink border-b border-line pb-1 lg:col-span-2">
            Reliability benchmark — precomputed, independent of the investigation above
          </div>
          <ReliabilityPanel />
          <HowCurieKnows />
        </section>

        <footer className="text-[9.5px] text-muted-ink text-center py-4 border-t border-line">
          Curie is research and education software. It does not provide clinical
          recommendations, therapeutic claims, or wet-lab protocols.
        </footer>
      </main>
    </div>
  );
}
