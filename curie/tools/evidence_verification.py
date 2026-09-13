"""Cross-source evidence verification.

Not an external API call, so it doesn't subclass BaseToolClient — there is no
provider/latency to report, only a judgment to make about the ToolResults other
clients already produced. This is the piece of curie's premise that Billie Gene's
architecture had no place for at all: Billie Gene composed one LLM's narration into
a single confident dossier, with nothing checking whether its "sources" actually
agreed, because it never called real sources to disagree in the first place.

Kept deliberately simple and rule-based for this phase: it checks whether tool calls
that were supposed to describe the same protein actually name the same thing, and
whether epitope evidence exists at all for a claimed structure. It is not a natural
-language entailment system, and it does not pretend to be — an `UNVERIFIABLE` verdict
is a first-class, expected outcome, not a failure state.
"""

from __future__ import annotations

from curie.shared.models import AgreementLevel, ToolResult, VerificationFinding


def _text_overlap(a: str, b: str) -> bool:
    """True if any alphanumeric token of length >= 4 is shared between a and b."""
    tokens_a = {t for t in _tokenize(a) if len(t) >= 4}
    tokens_b = {t for t in _tokenize(b) if len(t) >= 4}
    return bool(tokens_a & tokens_b)


def _tokenize(text: str) -> set[str]:
    return {tok.strip(".,()[]{}:;'\"").lower() for tok in text.split()}


def _extract_uniprot_names(data) -> list[str]:
    """Pull recommended-name strings out of a UniProt response.

    Handles both shapes real code actually produces: a search response
    (`{"results": [entry, ...]}`, from UniProtClient.search) and a single
    entry (from UniProtClient.get_entry, what agent/nodes/identity_resolution.py
    actually calls) — this function originally only handled the former, which
    meant it silently extracted nothing (and this whole check always came back
    UNVERIFIABLE) on every real run, since identity resolution only ever uses
    get_entry. Found via Phase 3 fault-injection testing, not by inspection.
    """
    if not isinstance(data, dict):
        return []

    entries = data["results"] if isinstance(data.get("results"), list) else [data]

    names: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        rec_name = (
            entry.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value")
        )
        if rec_name:
            names.append(rec_name)
    return names


def verify_identity_consistency(
    uniprot_result: ToolResult, iedb_result: ToolResult
) -> VerificationFinding:
    """Check whether UniProt's protein name and IEDB's source antigen name overlap.

    Both inputs must have `status == ok` and non-empty `data`, or the finding is
    UNVERIFIABLE — curie does not infer agreement from a source that never answered.
    """
    claim = "UniProt and IEDB describe the same source protein"

    if not uniprot_result.ok or not iedb_result.ok:
        return VerificationFinding(
            claim=claim,
            agreement=AgreementLevel.UNVERIFIABLE,
            notes="One or both sources did not return successfully; nothing to compare.",
        )

    uniprot_names = _extract_uniprot_names(uniprot_result.data)

    iedb_names: list[str] = []
    try:
        for row in iedb_result.data:
            iedb_names.extend(row.get("parent_source_antigen_names") or [])
    except (AttributeError, TypeError):
        pass

    if not uniprot_names or not iedb_names:
        return VerificationFinding(
            claim=claim,
            agreement=AgreementLevel.UNVERIFIABLE,
            notes="Could not extract a protein/antigen name from one or both sources.",
        )

    agrees = any(_text_overlap(u, i) for u in uniprot_names for i in iedb_names)
    return VerificationFinding(
        claim=claim,
        supporting_sources=["uniprot", "iedb"] if agrees else [],
        conflicting_sources=[] if agrees else ["uniprot", "iedb"],
        agreement=AgreementLevel.AGREE if agrees else AgreementLevel.CONFLICT,
        notes=(
            f"UniProt names: {uniprot_names[:2]!r}; IEDB names: {iedb_names[:2]!r}"
        ),
    )


def verify_structural_and_epitope_evidence_present(
    esm_result: ToolResult, iedb_result: ToolResult
) -> VerificationFinding:
    """Check whether both a predicted structure and curated epitope evidence exist.

    This is a coverage check, not a semantic one: PARTIAL means only one leg of
    evidence exists, which is worth surfacing rather than silently proceeding as if
    a full evidence base were available.
    """
    claim = "A predicted structure and curated epitope evidence both exist for this target"

    has_structure = esm_result.ok and bool(esm_result.data)
    has_epitopes = iedb_result.ok and bool(iedb_result.data)

    if has_structure and has_epitopes:
        agreement = AgreementLevel.AGREE
    elif has_structure or has_epitopes:
        agreement = AgreementLevel.PARTIAL
    else:
        agreement = AgreementLevel.UNVERIFIABLE

    supporting = [
        name
        for name, present in (("esm_atlas", has_structure), ("iedb", has_epitopes))
        if present
    ]
    return VerificationFinding(
        claim=claim,
        supporting_sources=supporting,
        agreement=agreement,
        notes=f"structure_present={has_structure}, epitope_evidence_present={has_epitopes}",
    )
