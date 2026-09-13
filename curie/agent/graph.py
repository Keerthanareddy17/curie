"""curie's investigation graph.

    sequence_intake -> research_planner (Gemini-advised when GEMINI_API_KEY is set, else deterministic)
    research_planner -> identity_resolution        \\
    research_planner -> structure_prediction        > run concurrently
    identity_resolution -> epitope_evidence         \\
    identity_resolution -> literature_check          > run concurrently
    structure_prediction, epitope_evidence, literature_check -> evidence_normalization
    evidence_normalization -> evidence_adjudication -> confidence_gate
        -> gemini_synthesis (optional narration, cannot change anything before it)
        -> dossier_generation

structure_prediction has no data dependency on identity_resolution (folding only
needs residues), so it runs in the same superstep as identity_resolution rather
than after it. epitope_evidence and literature_check both need identity's output
(an accession / a protein name) so they run one step later, but independently of
each other. `evidence_normalization` is declared with `defer=True` so it waits
for all three collection branches regardless of their differing depth — verified
during development that a plain multi-predecessor node fires once per incoming
edge (i.e. twice, prematurely) without `defer`, not once after all of them.

Gemini appears in exactly two places, both optional and both non-authoritative:
`research_planner` (may suggest which evidence to pursue; never decides
`needs_identity` or `structure_allowed`, and downstream nodes independently
re-verify their own preconditions regardless) and `gemini_synthesis` (narrates
the evidence_score/status/claims/conflicts that confidence_gate already fixed,
and cannot feed back into them — see curie/tools/gemini.py).
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from curie.agent.nodes.confidence_gate import confidence_gate
from curie.agent.nodes.dossier_generation import dossier_generation
from curie.agent.nodes.epitope_evidence import epitope_evidence
from curie.agent.nodes.evidence_adjudication import evidence_adjudication
from curie.agent.nodes.evidence_normalization import evidence_normalization
from curie.agent.nodes.gemini_synthesis import gemini_synthesis
from curie.agent.nodes.identity_resolution import identity_resolution
from curie.agent.nodes.literature_check import literature_check
from curie.agent.nodes.research_planner import research_planner
from curie.agent.nodes.sequence_intake import sequence_intake
from curie.agent.nodes.structure_prediction import structure_prediction
from curie.agent.state import InvestigationState


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(InvestigationState)

    graph.add_node("sequence_intake", sequence_intake)
    graph.add_node("research_planner", research_planner)
    graph.add_node("identity_resolution", identity_resolution)
    graph.add_node("structure_prediction", structure_prediction)
    graph.add_node("epitope_evidence", epitope_evidence)
    graph.add_node("literature_check", literature_check)
    graph.add_node("evidence_normalization", evidence_normalization, defer=True)
    graph.add_node("evidence_adjudication", evidence_adjudication)
    graph.add_node("confidence_gate", confidence_gate)
    graph.add_node("gemini_synthesis", gemini_synthesis)
    graph.add_node("dossier_generation", dossier_generation)

    graph.set_entry_point("sequence_intake")
    graph.add_edge("sequence_intake", "research_planner")

    graph.add_edge("research_planner", "identity_resolution")
    graph.add_edge("research_planner", "structure_prediction")

    graph.add_edge("identity_resolution", "epitope_evidence")
    graph.add_edge("identity_resolution", "literature_check")

    graph.add_edge("structure_prediction", "evidence_normalization")
    graph.add_edge("epitope_evidence", "evidence_normalization")
    graph.add_edge("literature_check", "evidence_normalization")

    graph.add_edge("evidence_normalization", "evidence_adjudication")
    graph.add_edge("evidence_adjudication", "confidence_gate")
    graph.add_edge("confidence_gate", "gemini_synthesis")
    graph.add_edge("gemini_synthesis", "dossier_generation")
    graph.add_edge("dossier_generation", END)

    return graph.compile()


async def run_investigation(
    raw_sequence: str, accession_hint: str | None = None, run_id: str | None = None
) -> InvestigationState:
    """Run the full graph on one sequence and return the final, validated state.

    `run_id` lets a caller (the backend's run store) pre-issue an id before the
    graph starts, so the id returned to a client immediately from `POST
    /api/investigations` matches the one every trace event and log line inside
    the run carries. Left unset, InvestigationState generates its own.
    """
    compiled = build_graph()
    kwargs = {"raw_sequence": raw_sequence, "accession_hint": accession_hint}
    if run_id is not None:
        kwargs["run_id"] = run_id
    initial_state = InvestigationState(**kwargs)
    result = await compiled.ainvoke(initial_state)
    return InvestigationState.model_validate(result)
