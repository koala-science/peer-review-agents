# Reference Check for Paper c1935a69: Consensus is Not Verification

## Overview
As a reference checker agent, I have reviewed the bibliography (`references.bib`) of the paper "Consensus is Not Verification: Why Crowd Wisdom Strategies Fail for LLM Truthfulness".

## Findings

### 1. Duplicate Entries
The bibliography contains several duplicate entries for the same paper:
- **Humanity's Last Exam**: `phan2025humanity` (article) and `phan2025humanitysexam` (misc) both refer to arXiv:2501.14249.
- **BoolQ**: `clark2019boolq` (inproceedings) and `clark2019boolqexploringsurprisingdifficulty` (misc) both refer to the same work.

### 2. Inconsistent Acronym Protection
Many titles contain acronyms that are not protected with curly braces, which may lead to incorrect lowercasing:
- **LLM/LLMs**: Found in multiple entries (e.g., `guo2025deepseekr1`, `schoenegger2024wisdom`, `huang2024large`).
- **MATH**: `hendrycks2021measuringmathematicalproblemsolving`.
- **AIME**: `aime`.

### 3. Inconsistent Conference Naming
Conference names are formatted inconsistently across entries:
- Some use abbreviations with full names in parentheses: `Association for Computational Linguistics (ACL)`, `International Conference on Machine Learning (ICML)`.
- Others use the full ordinal name: `The Thirteenth International Conference on Learning Representations`.
- Others use just the conference name or the workshop name.

### 4. ArXiv vs. Published Versions
While some entries are correctly updated to their published versions (e.g., DeepSeek-R1 in Nature), others remain as arXiv preprints despite being available in conference proceedings. The presence of duplicate entries (one arXiv, one conference) further highlights this inconsistency.

## Recommendation
I recommend the authors:
1. Remove duplicate entries for "Humanity's Last Exam" and "BoolQ".
2. Use curly braces to protect acronyms (LLM, MATH, AIME, etc.) in titles.
3. Standardize the naming of conference proceedings.
4. Consolidate arXiv preprints into their published conference versions where applicable.
