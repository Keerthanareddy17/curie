"""Example protein sequences with real accession IDs, for use as realistic test
inputs. Ported from Billie Gene's `src/data.ts` `PATHOGEN_PRESETS` (MIT-licensed;
see docs/ATTRIBUTION.md) — these are real reference sequences, not fabricated data,
so they were worth keeping even though the surrounding UI/dossier logic was not.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SampleSequence:
    title: str
    accession_id: str
    sequence: str


SARS_COV_2_SPIKE = SampleSequence(
    title="SARS-CoV-2 Spike Glycoprotein",
    accession_id="P0DTC2",
    sequence=(
        "MFVFLVLLPLVSSQCVNLTTRTQLPPAYTNSFTRGVYYPDKVFRSSVLHSTQDLFLPFYSNVTWFHAIH"
        "VSGTNGTKRFDNPVLPFNDGVYFASTEKSNIIRGWIFGTTLDSKTQSLLIVNNATNVVIKVCEFQFCND"
        "PFLGVYYHKNNKSWMESEFRVYSSANNCTFEYVSQPFLMDLEGKQGNFKNLREFVFKNIDGYFKIYSKH"
    ),
)

INFLUENZA_H5N1_HA1 = SampleSequence(
    title="Influenza A H5N1 Hemagglutinin HA1",
    accession_id="ABP38012",
    sequence=(
        "MEKIVLLFAIVSLVKSDQICIGYHANNSTEQVDTIMEKNVTVTHAQDILEKKHNGKLCDLDGVKPLILR"
        "DCSVAGWLLGNPMCDECLPVPEWSYIVEKDNPVNDLCYPGDFNDYEELKHLLSRINHFEKIQIIPKSSW"
    ),
)

SHORT_SYNTHETIC_PROTEIN = SampleSequence(
    title="Short synthetic test peptide",
    accession_id="",
    sequence="MELKRTFYNLAGAGDEVWKKTPLASVTRDATYPKTCKTTAK",
)

ALL_SAMPLES = [SARS_COV_2_SPIKE, INFLUENZA_H5N1_HA1, SHORT_SYNTHETIC_PROTEIN]
