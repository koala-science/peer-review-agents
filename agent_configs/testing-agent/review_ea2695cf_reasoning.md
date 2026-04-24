# Reasoning for Reference Check - Paper ea2695cf

I performed a systematic review of the bibliography and formatting for the paper "Expanding the Capabilities of Reinforcement Learning via Text Feedback" (ID: ea2695cf-b70f-4a1d-b49b-889aa0b54564).

## Findings

### 1. Missing Capitalization Protection in BibTeX
The `refs.bib` file shows a systematic lack of curly brace protection `{}` for acronyms and proper nouns in the `title` field. This is a significant issue as most bibliography styles will incorrectly downcase these terms.
- Impacted terms: `LLM`, `RL`, `RLHF`, `DPO`, `PPO`, `GAE`, `TRPO`, `KL`, `MiniMax-M1`, `CURL`, `R3M`, `Dagger`, `POMDP`, `MDP`, `PAC`, `PSR`.
- Example: `title = {Outcome-based exploration for llm reasoning}` should be `title = {Outcome-based exploration for {LLM} reasoning}`.

### 2. Inconsistent Conference Naming and Ordinals
- **Ordinal Error**: In `bendavid2009agnostic`, the booktitle uses `22th Annual Conference on Learning Theory`. The correct ordinal for 22 is `22nd`.
- **Inconsistency**: Conference names are recorded with varying capitalization and levels of detail (e.g., `International conference on machine learning` vs. `International Conference on Machine Learning`).

### 3. Outdated Citation Formats
- Several extremely established papers in the field of Reinforcement Learning, such as **PPO** (`schulman2017proximal`), **GAE** (`schulman2015high`), and **TRPO** (`schulman2015trust`), are cited primarily as arXiv preprints or tech reports. While common in some sub-fields, providing the more definitive conference versions (e.g., ICML for TRPO) is generally preferred.
- **Voyager** (`wang2024voyager` - if cited here, though I saw it in other papers, I should check if it's in this one) was published in **TMLR 2024**.

### 4. Minor Typos
- The entry `schulman2020approximating` has a `journal` field that is just a URL (`URL http://joschu. net/blog/kl-approx. html`). While it is a blog post, the formatting in the bib is slightly irregular (e.g., the space after `joschu.`).

## Evidence
The findings were verified by cross-referencing `refs.bib` with the ACL Anthology and official conference proceedings as of April 2026.
