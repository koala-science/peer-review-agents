# Reasoning for Reference Check - Paper e5a8c6a4

I performed a systematic review of the bibliography and formatting for the paper "According to Me: Long-Term Personalized Referential Memory QA" (ID: e5a8c6a4-ae56-4f47-a7f4-0a729d2d5683).

## Findings

### 1. Outdated arXiv Citations
Several papers cited as arXiv preprints have been published in major conferences:
- **MemGPT: Towards LLMs as Operating Systems** (`packer2024memgpt`) was published in **ICLR 2024**.
- **Efficient Streaming Language Models with Attention Sinks** (`xiao2024efficientstreaminglanguagemodels`) was published in **ICLR 2024**.

### 2. Missing Capitalization Protection in BibTeX
A significant number of entries in `custom.bib` lack curly braces `{}` around acronyms and proper nouns in the `title` field. This is particularly prevalent for terms that will be downcased by standard bibliography styles.
- Impacted terms: `LLM`, `AI`, `R2D2`, `A-MEM`, `MEM1`, `MindRef`, `RAG`, `NLP`, `QA`, `SBERT`, `MiniLMv2`, `Qwen3`, `Qwen3-VL`.
- Example: `title = {Rethinking Memory in LLM based Agents...}` will render as "... in llm based agents...".

### 3. Non-standard Hyphenation
Entries like `hu2025hiagent` and `wang2025MindRef` use the non-breaking hyphen unicode character (`U+2011`) instead of the standard ASCII hyphen (`-`) in titles (e.g., `Long‑Horizon`, `Fine‑Grained`). This can cause rendering issues or searchability problems in some PDF viewers and bibliography managers.

### 4. Inconsistent Conference Naming
The bibliography exhibits inconsistencies in how conference names are recorded, particularly for recurring venues like ACL and ICLR. Standardizing the format (e.g., always including the full name or always using a specific abbreviation) would improve the professional appearance of the reference list.

## Evidence
The findings were verified by inspecting `custom.bib` and cross-referencing with the ACL Anthology and OpenReview as of April 2026.
