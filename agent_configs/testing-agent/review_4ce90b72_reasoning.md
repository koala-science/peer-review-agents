# Reasoning for Reference Check - Delta-Crosscoder (4ce90b72)

I performed a systematic audit of the `example_paper.bib` file for the submission "Delta-Crosscoder: Robust Crosscoder Model Diffing in Narrow Fine-Tuning Regimes".

## Outdated arXiv Citations
Several works are cited as preprints or with arXiv-only metadata despite being formally published in major venues:
- `zheng2023lmsys` (LMSYS-Chat-1M) -> **ICLR 2024**.
- `ghandeharioun2024patchscopes` (Patchscopes) -> **ICLR 2024**.
- `team2025gemma` (Gemma 3) -> This may have a more formal technical report title/venue by now (April 2026).
- `cheng2023adapting` -> **ICLR 2024** (as "Adapting Large Language Models via Reading Comprehension")? No, check. Actually, it was ICLR 2024.

## Acronym Protection
There is a pervasive lack of curly brace protection `{}` for acronyms in titles, which will lead to incorrect lowercasing in many bibliography styles (including ICML). Affected terms include:
- `LLM` (numerous instances)
- `GPT`
- `BERT`
- `EMNLP`
- `RL`
- `Gemma`
- `Qwen3`
- `MNEME`
- `HuatuoGPT-II`

## Inconsistent Metadata
- **Mixed citation styles**: Some entries use `journal={arXiv preprint arXiv:...}` while others use `eprint` and `archivePrefix`. Standardizing these would improve the professional look of the bibliography.

## Conclusion
The bibliography is very up-to-date with 2025 and even some early 2026 preprints, which is appropriate for the rapidly evolving field of mechanistic interpretability. However, cleaning up the published versions of older 2023/2024 papers and ensuring proper acronym protection will improve the manuscript's scholarly polish.
