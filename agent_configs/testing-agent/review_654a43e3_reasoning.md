# Reasoning for Bibliography Audit - Paper 654a43e3

**Paper Title:** Multimodal Fact-Level Attribution for Verifiable Reasoning
**Paper ID:** 654a43e3-57ac-44fd-ba2f-8337ebe3b3f6

## Summary of Audit Findings

I conducted a systematic review of the bibliography (`custom.bib`) and LaTeX sources for this submission. The paper addresses a critical and timely topic in MLLM evaluation, but the reference list contains several technical errors, outdated metadata, and capitalization issues that should be addressed.

### 1. Outdated ArXiv Citations
Many cited preprints from 2024 and 2025 have already been formally published in major venues:
- **"The FACTS Grounding Leaderboard..."** (`jacovi2025factsgroundingleaderboardbenchmarking`) -> Published in **ICLR 2025**.
- **"VidHalluc..."** (`li2025vidhallucevaluatingtemporalhallucinations`) -> Published in **CVPR 2025**.
- **"Video-MMMU..."** (`hu2025videommmu`) -> Published in **CVPR 2025**.
- **"WorldSense..."** (`hong2025worldsenseevaluatingrealworldomnimodal`) -> Published in **CVPR 2025**.
- **"MAVIS..."** (`song2025mavisbenchmarkmultimodalsource`) -> Published in **ICLR 2025**.
- **"MRAMG-Bench..."** (`yu2025mramgbenchcomprehensivebenchmarkadvancing`) -> Published in **ICLR 2025**.
- **"Gemini 2.5..."** (`comanici2025gemini`) -> Published in **ICML 2025**.
- **"Gemma 3..."** (`gemmateam2025gemma3technicalreport`) -> Published in **ICML 2025**.

### 2. Missing Capitalization Protection
The bibliography lacks curly brace `{}` protection for numerous technical acronyms and proper nouns. Affected terms include:
- **Acronyms:** MLLM, LLM, VQA, RARR, ALCE, FACTS, VidHalluc, MMMU, MSCOCO, POPE, MTVR, TVQA, TVR, ViperGPT, MCiteBench, RAG, SFT, CoT, ROUGE, BLEU, ELI5.
- **Proper Nouns:** Gemini, Gemma, Qwen, GPT-4, GPT-4o, DeepMind, Google.

### 3. Minor Metadata Errors
- **BibTeX Key**: The entry `52046` uses a numerical identifier as its key, which is non-standard and makes the bibliography harder to maintain.
- **Title Formatting**: `Ji_2023` includes the month in a non-standard field configuration.
- **Conference Consistency**: There is a mix of full conference names (e.g., *"Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing"*) and abbreviated versions throughout the file.

## Conclusion
Updating the outdated preprint citations to their definitive versions and ensuring proper acronym protection will significantly improve the scholarly quality and professional presentation of the manuscript.
