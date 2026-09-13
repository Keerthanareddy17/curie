/** Parses real counts out of real PDB text — mirrors curie/tools/esm_atlas.py's
 * mean_plddt() column reading, so the numbers shown in the UI are read from
 * the actual structure, never invented. */
export function summarizePdb(pdbText: string): { residues: number; atoms: number } {
  const atomLines = pdbText.split("\n").filter((l) => l.startsWith("ATOM"));
  const residueIds = new Set(atomLines.map((l) => l.substring(22, 26).trim()));
  return { residues: residueIds.size, atoms: atomLines.length };
}
