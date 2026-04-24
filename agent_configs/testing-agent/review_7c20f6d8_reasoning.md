# Reasoning for Bibliography Audit - Paper 7c20f6d8

**Paper Title:** Conversational Behavior Modeling Foundation Model With Multi-Level Perception
**Paper ID:** 7c20f6d8-8c96-476b-bfae-a08fd8fc2d71

## Summary of Audit Findings

I conducted a systematic review of the bibliography (`main.bib`) and LaTeX sources for this submission. The paper addresses a complex problem in full-duplex dialogue, but the reference list contains numerous duplicate entries, outdated metadata, and capitalization issues that should be addressed.

### 1. Duplicate BibTeX Entries
Identified several redundant entries that should be consolidated:
- **T5**: `raffel2020exploring` and `raffel2023exploringlimitstransferlearning` (Same paper).
- **dGSLM**: `dgslm` and `arxiv:2203.16502` (Both refer to *"Generative Spoken Dialogue Language Modeling"*).
- **VAP**: `vap` and `arxiv:2410.15929` (Both refer to *"Yeah, Un, Oh: Continuous and Real-time Backchannel Prediction..."*).
- **GPT-4**: `achiam2023gpt` and `openai2023gpt` (Both refer to the GPT-4 Technical Report).
- **AdamW**: `loshchilov2019decoupled` and `loshchilov2017decoupled` (Same paper).

### 2. Outdated ArXiv Citations
Many cited preprints have been formally published in major venues:
- **Moshi** (`defossez2024moshi`) -> Published in **ICML 2025**.
- **Theory of Mind** (`sclar2024exploretom`) -> Published in **ICLR 2025**.
- **Spoken Question Answering** (`nachmani2023spoken`) -> Published in **NeurIPS 2023**.
- **GSQA** (`shih2023gsqa`) -> Published in **ICASSP 2024**.
- **Air-bench** (`yang2024air`) -> Published in **ACL 2024**.
- **Advancing LLMs** (`lin2024advancing`) -> Published in **ACL 2024**.
- **Emphasized Sentences in Dialogue** (`lin2024can`) -> Published in **ACL 2024**.
- **Graph Chain-of-Thought** (`jin2024graph`) -> Published in **ICLR 2025**.
- **HGoT** (`fang2024hgot`) -> Published in **ACL 2024**.

### 3. Missing Capitalization Protection
The bibliography lacks curly brace `{}` protection for numerous technical acronyms and proper nouns. Affected terms include:
- **Acronyms:** GPT, LLM, VLM, RL, SFT, CoT, GoT, ASR, ICASSP, IEEE, ACM, AAAI, EMNLP, ACL, NAACL, SIGDIAL, NeurIPS, T5, AdamW, BERT, ROUGE, BLEU, ROC, AUC, NLP, AI.
- **Proper Nouns:** Theory of Mind, Switchboard, LibriSpeech, Moshi, HuBERT, VoxDialogue, CANDOR.

### 4. Minor Metadata Errors
- **Misspelling**: The key `arvix:2510.07355` contains a typo (`arvix` instead of `arxiv`).
- **Inconsistent Field**: `openai2023gpt` uses `journal={View in Article}`, which is non-standard.

## Conclusion
Addressing these duplicates, updating preprints to their definitive versions, and ensuring proper acronym protection will significantly enhance the scholarly quality and professional presentation of the manuscript.
