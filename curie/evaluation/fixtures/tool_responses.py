"""Canned tool response payloads for fault-injection scenarios.

These are the ONLY fabricated external-API response shapes in this
repository outside of Phase 1/2's own unit-test fixtures (tests/fixtures/) —
used exclusively by curie/evaluation/scenarios/ and curie/evaluation/fixtures/
fault_adapters.py, never imported by curie/tools/ or curie/agent/. The real
demo path always calls the live APIs; see curie/evaluation/README.md's
"LIVE INTEGRATIONS vs CONTROLLED EVALUATION FIXTURES" section.

Shapes here are modeled on real responses observed during Phase 1-3
development (see docs/ATTRIBUTION.md and curie/evaluation/datasets/README.md
for the live calls that established these shapes), not invented from nothing.
"""

from __future__ import annotations

UNIPROT_OK = {
    "primaryAccession": "P0DTC2",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Spike glycoprotein"}}
    },
    "organism": {"scientificName": "Severe acute respiratory syndrome coronavirus 2"},
}

# A second, real-shaped UniProt entry for a genuinely different protein, used
# by Scenario D (conflicting evidence) — the conflict comes from this
# genuinely disagreeing with IEDB_CONFLICTING_SOURCE below, not from a
# malformed payload.
UNIPROT_DIFFERENT_PROTEIN = {
    "primaryAccession": "P03437",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Hemagglutinin"}}
    },
    "organism": {"scientificName": "Influenza A virus"},
}

IEDB_OK = [
    {
        "structure_id": 1309137,
        "structure_descriptions": ["SIIAYTMSL"],
        "linear_sequence": "SIIAYTMSL",
        "linear_sequence_length": 9,
        "parent_source_antigen_names": ["Spike glycoprotein (UniProt:P0DTC2)"],
        "mhc_allele_names": ["HLA-A*02:01"],
    },
    {
        "structure_id": 1309139,
        "structure_descriptions": ["STECSNLLLQYGSFC"],
        "linear_sequence": "STECSNLLLQYGSFC",
        "linear_sequence_length": 15,
        "parent_source_antigen_names": ["Spike glycoprotein (UniProt:P0DTC2)"],
        "mhc_allele_names": ["HLA-DRB1*04:04"],
    },
]

IEDB_EMPTY: list = []

EUROPE_PMC_OK = {
    "hitCount": 18132,
    "resultList": {
        "result": [
            {
                "id": "34567890",
                "title": "Structural basis of SARS-CoV-2 spike glycoprotein epitope recognition.",
                "authorString": "Lan J, et al.",
                "pubYear": "2020",
            }
        ]
    },
}

EUROPE_PMC_EMPTY = {"hitCount": 0, "resultList": {"result": []}}

# A real 3-line ESMFold-shaped PDB fragment (same shape used in
# tests/fixtures/mock_responses.py) — enough for mean_plddt() to parse.
ESM_ATLAS_OK_PDB = """HEADER    FIXTURE
ATOM      1  N   MET A   1      11.104  13.207   2.100  1.00 90.12           N
ATOM      2  CA  MET A   1      12.560  13.207   2.100  1.00 91.03           C
ATOM      3  C   MET A   1      13.100  14.600   2.100  1.00 92.44           C
END
"""

# Malformed payloads: syntactically valid JSON, wrong shape. A real service
# returning these would be an API contract break, not a network failure —
# distinct from a timeout or 5xx, and exercised by Scenario F.
MALFORMED_UNIPROT_PAYLOAD = ["unexpected", "list", "payload"]
MALFORMED_EUROPE_PMC_PAYLOAD = "not a dict at all"
