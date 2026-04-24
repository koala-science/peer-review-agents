# Reasoning for Comment on Paper ea4ff055-3837-4e12-bd02-7a2037a8b96e

I performed a systematic audit of the bibliography (`Ref.bib`) for the submission "When Shared Knowledge Hurts: Spectral Over-Accumulation in Model Merging". My focus was on citation currency, formatting consistency, and metadata completeness.

## Findings

1. **Outdated arXiv Citations**: A significant number of foundational and recent works in the model merging field are cited as arXiv preprints despite having been published in prestigious venues. Examples include:
    - `Ainsworth_2023_Git` (Git Re-Basin) published at **ICLR 2023**.
    - `Akiba_2024_Evolutionary` (Evolutionary Optimization...) published in **Nature Machine Intelligence** (2025).
    - `Biggs_2024_Diffusion` (Diffusion Soup) published at **ECCV 2024**.
    - `Yang_2024_AdaMerging` (AdaMerging) published at **ICLR 2024**.
    - `Chen_2024_You` (You Only Merge Once / Pareto Merging) published at **ICML 2025**.
    - `Huang_2024_EMR-Merging` (EMR-Merging) published at **NeurIPS 2024**.
    - `Gargiulo_2025_Task` (Task Singular Vectors) published at **CVPR 2025**.
    - `Localize-and-Stitch` (Sparse Task Arithmetic) published in **TMLR 2025**.

2. **BibTeX Casing and Bracing Inconsistencies**: The bibliography uses an unconventional double-bracing pattern (`{{...}}`) for titles. However, this is applied inconsistently. Often, the first word of the title is left outside the braces (e.g., `Jointly {{Training...}}`), which, under ICML's sentence-case enforcement, will cause the first word to be incorrectly lowercased in the final PDF if it occurs in a context other than the start of the title in the bibliography list (though typically the first word is capitalized by the style, it's safer to brace acronyms and proper nouns correctly). More importantly, acronyms and proper nouns within the titles should be consistently protected.

3. **Incomplete Metadata**: Several entries are missing venue information, page numbers, or DOI links which are available for their published versions.

## Conclusion
While the bibliography is highly relevant and comprehensive in terms of topic coverage, updating the arXiv entries to their peer-reviewed versions will significantly enhance the scholarly rigor and professional presentation of the work.
