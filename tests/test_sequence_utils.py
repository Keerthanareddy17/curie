from curie.shared.sequence_utils import (
    clean_sequence,
    find_orfs,
    looks_like_nucleotide,
    mean_antigenicity,
    mean_hydrophobicity,
    residue_composition,
    translate_dna,
)
from tests.fixtures.sample_sequences import SARS_COV_2_SPIKE


def test_clean_sequence_strips_fasta_header_and_invalid_chars():
    raw = ">some header\nMFV*FLV 1LL\n"
    assert clean_sequence(raw) == "MFVFLVLL"


def test_clean_sequence_uppercases():
    assert clean_sequence("mkv") == "MKV"


def test_clean_sequence_empty_input():
    assert clean_sequence("") == ""
    assert clean_sequence(">header only\n") == ""


def test_residue_composition_sums_to_roughly_100_percent():
    comp = residue_composition(SARS_COV_2_SPIKE.sequence)
    assert abs(sum(comp.values()) - 100.0) < 1.0


def test_residue_composition_empty_sequence_is_all_zero():
    comp = residue_composition("")
    assert comp == {"hydrophobic": 0.0, "charged": 0.0, "polar": 0.0, "special": 0.0}


def test_mean_hydrophobicity_known_value():
    # Pure isoleucine: Kyte-Doolittle value is exactly 4.5
    assert mean_hydrophobicity("IIII") == 4.5


def test_mean_antigenicity_empty_is_zero():
    assert mean_antigenicity("") == 0.0


def test_looks_like_nucleotide_true_for_dna():
    assert looks_like_nucleotide("ATGGCCATTGTAATGGGCCGCTGA") is True


def test_looks_like_nucleotide_false_for_protein():
    assert looks_like_nucleotide(SARS_COV_2_SPIKE.sequence) is False


def test_translate_dna_simple_case():
    # ATG GGC CGC TGA -> M G R (stop)
    assert translate_dna("ATGGGCCGCTGA") == "MGR"


def test_translate_dna_handles_rna_input():
    assert translate_dna("AUGGGCCGCUGA") == "MGR"


def test_translate_dna_respects_frame():
    dna = "AATGGGCCGCTGA"  # frame 1 (0-indexed) aligns the ATG
    assert translate_dna(dna, frame=1) == "MGR"


def test_translate_dna_rejects_invalid_frame():
    import pytest

    with pytest.raises(ValueError):
        translate_dna("ATGGGCCGCTGA", frame=3)


def test_find_orfs_finds_the_start_to_stop_orf():
    dna = "TTT" + "ATG" + "GGC" * 10 + "TGA" + "TTT"
    orfs = find_orfs(dna, min_length_aa=5)
    assert len(orfs) == 1
    assert orfs[0]["protein"] == "M" + "G" * 10


def test_find_orfs_filters_by_min_length():
    dna = "ATG" + "GGC" * 2 + "TGA"  # 3 aa ORF
    assert find_orfs(dna, min_length_aa=10) == []
