"""Explicit, hardcoded fake API responses — used ONLY by offline unit tests.

Per the project spec: fake API responses are allowed nowhere except inside test
fixtures like this file. Nothing under curie/tools/ or curie/agent/ imports this
module; it exists purely so tests don't depend on network access.
"""

from __future__ import annotations

MOCK_ESM_ATLAS_PDB = """HEADER    MOCK FIXTURE
ATOM      1  N   MET A   1      11.104  13.207   2.100  1.00 90.12           N
ATOM      2  CA  MET A   1      12.560  13.207   2.100  1.00 91.03           C
ATOM      3  C   MET A   1      13.100  14.600   2.100  1.00 92.44           C
END
"""

MOCK_UNIPROT_ENTRY = {
    "primaryAccession": "P0DTC2",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Spike glycoprotein"}}
    },
    "organism": {"scientificName": "Severe acute respiratory syndrome coronavirus 2"},
}

MOCK_UNIPROT_SEARCH = {"results": [MOCK_UNIPROT_ENTRY]}

MOCK_IEDB_EPITOPES = [
    {
        "structure_id": 1309137,
        "structure_descriptions": ["SIIAYTMSL"],
        "linear_sequence": "SIIAYTMSL",
        "linear_sequence_length": 9,
        "parent_source_antigen_names": ["Spike glycoprotein (UniProt:P0DTC2)"],
        "mhc_allele_names": ["HLA-A*02:01"],
    }
]

MOCK_EUROPE_PMC_SEARCH = {
    "hitCount": 1,
    "resultList": {
        "result": [
            {
                "id": "12345678",
                "title": "A mock literature hit for testing.",
                "authorString": "Doe J, et al.",
            }
        ]
    },
}
