"""Sequence intake node.

Responsibility: turn raw user input into a validated, characterized sequence the
rest of the graph can act on — classify DNA/RNA vs. protein, translate if needed,
and compute deterministic composition statistics. No external calls; this is the
one node that must succeed offline, since every downstream node depends on it.
An empty `normalized_sequence` here is what the confidence gate treats as a
critical failure (InvestigationStatus.FAILED) later, since nothing meaningful
could have run downstream.
"""

from __future__ import annotations

import time

from curie.agent.state import InvestigationState
from curie.shared.logging import get_logger
from curie.shared.models import SequenceType, TraceEvent
from curie.shared.sequence_utils import (
    clean_sequence,
    looks_like_nucleotide,
    mean_antigenicity,
    mean_hydrophobicity,
    residue_composition,
    translate_dna,
)

logger = get_logger(__name__)

NODE_NAME = "sequence_intake"


def sequence_intake(state: InvestigationState) -> dict:
    start = time.perf_counter()

    if looks_like_nucleotide(state.raw_sequence):
        sequence_type = SequenceType.NUCLEOTIDE
        translated = translate_dna(state.raw_sequence)
        protein_sequence = translated
    else:
        sequence_type = SequenceType.PROTEIN
        translated = None
        protein_sequence = clean_sequence(state.raw_sequence)

    errors: list[str] = []
    if not protein_sequence:
        errors.append(
            "sequence_intake: could not derive a non-empty protein sequence from input"
        )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "sequence_intake",
        run_id=state.run_id,
        sequence_type=sequence_type.value,
        input_length=len(state.raw_sequence),
        normalized_length=len(protein_sequence),
    )

    trace = TraceEvent(
        run_id=state.run_id,
        node=NODE_NAME,
        duration_ms=duration_ms,
        status="error" if errors else "ok",
        input_summary=f"{len(state.raw_sequence)} raw characters",
        output_summary=f"sequence_type={sequence_type.value}, normalized_length={len(protein_sequence)}",
        errors=errors,
    )

    return {
        "sequence_type": sequence_type,
        "normalized_sequence": protein_sequence,
        "translated_sequence": translated,
        "residue_composition": residue_composition(protein_sequence),
        "mean_hydrophobicity": mean_hydrophobicity(protein_sequence),
        "mean_antigenicity": mean_antigenicity(protein_sequence),
        "errors": errors,
        "trace": [trace],
    }
