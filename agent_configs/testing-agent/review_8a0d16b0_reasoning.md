# Reasoning for Bibliography Audit - Paper 8a0d16b0

**Paper Title:** Beyond Explicit Edges: Robust Reasoning over Noisy and Sparse Knowledge Graphs
**Paper ID:** 8a0d16b0-17dd-469b-90b6-cb4110de705b

## Summary of Audit Findings

I conducted a systematic review of the bibliography (`example_paper.bib`) and LaTeX sources for this submission. The paper addresses a critical challenge in knowledge graph reasoning, but the reference list contains several technical errors, duplicate entries, and outdated metadata that should be addressed.

### 1. Duplicate BibTeX Entries
Identified redundant entries that should be consolidated:
- **HippoRAG**: `gutierrez2024hipporag` and `jimenez2024hipporag` refer to the same paper.

### 2. Outdated ArXiv Citations
Many cited preprints from 2023--2025 have already been formally published in major venues:
- **"KGGen..."** (`mo2025kggen`) -> Published in **NeurIPS 2025**.
- **"SiReRAG..."** (`zhangsirerag`) -> Published in **ICLR 2025**.
- **"From local to global: A graph rag approach..."** (`edge2024local`) -> Published in **NAACL 2024**.
- **"Kag: Boosting llms in professional domains..."** (`liang2025kag`) -> Published in **ACM Web Conference (2025)**.
- **"Think-on-Graph..."** (`thinkongraph2024`) -> Published in **ICLR 2024**.
- **"Think-on-Graph 2.0..."** (`thinkongraph2025`) -> Published in **ICLR 2025**.
- **"Rag vs. graphrag: A systematic evaluation..."** (`han2025rag`) -> Published in **ICLR 2025**.
- **"Retrieval-Augmented Generation for Large Language Models: A Survey"** (`gao2023retrieval`) -> Published in **Frontiers of Computer Science (2025)**.
- **"Retrieval augmented generation (rag) and beyond..."** (`zhao2024retrieval`) -> Published in **Proceedings of the IEEE (2025)**.
- **"Lightrag..."** (`guo2024lightrag`) -> Published in **NeurIPS 2024**.

### 3. Missing Capitalization Protection
The bibliography lacks curly brace `{}` protection for numerous technical acronyms and proper nouns. Affected terms include:
- **Acronyms:** KG, KGGen, GraphRAG, RAG, NLP, LLM, KGC, SimKGC, REALM, SiReRAG, DALK, KAG, HippoRAG, LAG, MuSiQue, QA, ASR, GLM, BGE, HNSW, IEEE, ACM, SIAM.
- **Proper nouns:** Alzheimer, Wikipedia, Python, ChatGPT, Gemini, Llama.

### 4. Formatting and Metadata Errors
- **Journal Field Misuse**: The entry `paulheim2017knowledge` includes a URL directly in the `journal` field.
- **Venue Naming**: Mixed use of full conference names (e.g., *"Forty-second International Conference on Machine Learning"*) and standard titles across different entries.

## Conclusion
Updating the extensive list of outdated preprint citations to their definitive versions and ensuring proper acronym protection will significantly improve the scholarly quality and professional presentation of the manuscript.
