"""Deterministic sequence utilities.

Ported from Billie Gene's `src/utils.ts` (MIT-licensed; see docs/ATTRIBUTION.md) from
TypeScript to Python. The Kyte-Doolittle hydrophobicity scale and Kolaskar-Tongaonkar
antigenicity scale are standard, citable biochemical reference tables — real science,
independent of Billie Gene — but porting them cleanly with tests is itself useful work
worth not redoing from scratch.

Deliberately NOT ported: Billie Gene's `scanEpitopes()`, which dresses up an invented
anchor-residue heuristic as an MHC-I/II binding predictor. That is a toy scoring
function, not IEDB, and curie does not pretend otherwise (see curie/tools/iedb.py for
the real thing).
"""

from __future__ import annotations

import re

VALID_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"

# Kyte & Doolittle (1982) hydropathy scale.
HYDROPHOBICITY: dict[str, float] = {
    "I": 4.5, "V": 4.2, "L": 3.8, "F": 2.8, "C": 2.5, "M": 1.9, "A": 1.8,
    "G": -0.4, "T": -0.7, "S": -0.8, "W": -0.9, "Y": -1.3, "P": -1.6,
    "H": -3.2, "E": -3.5, "Q": -3.5, "D": -3.5, "N": -3.5, "K": -3.9, "R": -4.5,
}

# Kolaskar & Tongaonkar (1990) antigenicity scale.
ANTIGENICITY: dict[str, float] = {
    "C": 1.08, "W": 1.08, "F": 1.05, "Y": 1.03, "I": 1.03, "L": 1.01, "V": 1.01,
    "H": 1.00, "M": 1.00, "P": 1.00, "A": 1.00, "T": 0.98, "D": 0.97,
    "Q": 0.96, "S": 0.96, "E": 0.94, "G": 0.93, "N": 0.92, "K": 0.92, "R": 0.91,
}

_NON_AA_RE = re.compile(rf"[^{VALID_AMINO_ACIDS}]")

_HYDROPHOBIC = set("AVLIPFWM")
_CHARGED = set("DEKRH")
_POLAR = set("STYNCQ")


def clean_sequence(raw_sequence: str) -> str:
    """Strip FASTA headers, whitespace, and non-canonical-amino-acid characters.

    Uppercases the result. Mirrors Billie Gene's `cleanSequence`.
    """
    lines = (
        line for line in raw_sequence.splitlines() if not line.strip().startswith(">")
    )
    joined = "".join(lines).upper()
    return _NON_AA_RE.sub("", joined)


def residue_composition(sequence: str) -> dict[str, float]:
    """Percent composition by coarse residue class: hydrophobic/charged/polar/special.

    Returns zeros for an empty (or empty-after-cleaning) sequence rather than raising,
    since this is descriptive, not validating input at a system boundary.
    """
    clean = clean_sequence(sequence)
    total = len(clean)
    if total == 0:
        return {"hydrophobic": 0.0, "charged": 0.0, "polar": 0.0, "special": 0.0}

    hydrophobic = charged = polar = special = 0
    for aa in clean:
        if aa in _HYDROPHOBIC:
            hydrophobic += 1
        elif aa in _CHARGED:
            charged += 1
        elif aa in _POLAR:
            polar += 1
        else:
            special += 1

    return {
        "hydrophobic": round(hydrophobic / total * 1000) / 10,
        "charged": round(charged / total * 1000) / 10,
        "polar": round(polar / total * 1000) / 10,
        "special": round(special / total * 1000) / 10,
    }


def mean_hydrophobicity(sequence: str) -> float:
    """Mean Kyte-Doolittle hydropathy over the cleaned sequence. 0.0 if empty."""
    clean = clean_sequence(sequence)
    if not clean:
        return 0.0
    return sum(HYDROPHOBICITY.get(aa, 0.0) for aa in clean) / len(clean)


def mean_antigenicity(sequence: str) -> float:
    """Mean Kolaskar-Tongaonkar antigenicity index over the cleaned sequence. 0.0 if empty."""
    clean = clean_sequence(sequence)
    if not clean:
        return 0.0
    return sum(ANTIGENICITY.get(aa, 0.98) for aa in clean) / len(clean)


def looks_like_nucleotide(raw_sequence: str) -> bool:
    """Heuristic: True if the cleaned-of-headers input is overwhelmingly A/C/G/T/U/N.

    Used by sequence intake to route between "translate this DNA/RNA first" and
    "treat this as protein" — a real fork Billie Gene's UI implied ("ORF translation")
    but never actually implemented anywhere in its codebase.
    """
    lines = (
        line for line in raw_sequence.splitlines() if not line.strip().startswith(">")
    )
    joined = "".join(lines).upper().strip()
    if not joined:
        return False
    nucleotide_chars = sum(1 for c in joined if c in "ACGTUN")
    return nucleotide_chars / len(joined) > 0.9


CODON_TABLE: dict[str, str] = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}


def translate_dna(sequence: str, frame: int = 0) -> str:
    """Translate a DNA sequence (standard genetic code) in one reading frame.

    RNA input (U instead of T) is accepted and normalized. Stops at the first
    in-frame stop codon; trailing incomplete codons are dropped. `frame` is 0, 1, or 2.
    This is genuinely new logic: no DNA/RNA translation exists anywhere in Billie Gene
    despite "ORF translation" being listed as a UI-facing skill.
    """
    if frame not in (0, 1, 2):
        raise ValueError("frame must be 0, 1, or 2")

    dna = "".join(c for c in sequence.upper() if c in "ACGTU").replace("U", "T")

    protein_chars: list[str] = []
    for i in range(frame, len(dna) - 2, 3):
        codon = dna[i : i + 3]
        amino_acid = CODON_TABLE.get(codon)
        if amino_acid is None:
            break
        if amino_acid == "*":
            break
        protein_chars.append(amino_acid)
    return "".join(protein_chars)


def find_orfs(sequence: str, min_length_aa: int = 25) -> list[dict]:
    """Find open reading frames across all 3 forward reading frames.

    Returns a list of {"frame", "start", "end", "protein"} dicts, sorted longest first.
    This is a straightforward ORF scan (start=ATG to stop codon), not codon-usage-aware
    gene prediction — good enough to hand candidate ORFs to downstream tools, not a
    claim of biological gene-finding accuracy.
    """
    dna = "".join(c for c in sequence.upper() if c in "ACGTU").replace("U", "T")
    orfs: list[dict] = []

    for frame in range(3):
        i = frame
        while i < len(dna) - 2:
            if dna[i : i + 3] == "ATG":
                protein_chars: list[str] = []
                j = i
                while j < len(dna) - 2:
                    codon = dna[j : j + 3]
                    amino_acid = CODON_TABLE.get(codon)
                    if amino_acid is None or amino_acid == "*":
                        break
                    protein_chars.append(amino_acid)
                    j += 3
                protein = "".join(protein_chars)
                if len(protein) >= min_length_aa:
                    orfs.append(
                        {"frame": frame, "start": i, "end": j, "protein": protein}
                    )
                i = j if j > i else i + 3
            else:
                i += 3

    return sorted(orfs, key=lambda o: len(o["protein"]), reverse=True)
