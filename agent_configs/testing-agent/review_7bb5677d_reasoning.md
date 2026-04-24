# Reasoning for Bibliography Audit - Paper 7bb5677d

**Paper Title:** 3DGSNav: Enhancing Vision-Language Model Reasoning for Object Navigation via Active 3D Gaussian Splatting
**Paper ID:** 7bb5677d-8a3b-49f6-bc3a-16b34d5f0f3c

## Summary of Audit Findings

I conducted a systematic review of the bibliography (`example_paper.bib`) and LaTeX sources for this submission. The paper presents an innovative integration of 3DGS and VLMs for navigation, but the reference list contains several technical errors, outdated metadata, and capitalization issues that should be addressed.

### 1. Outdated ArXiv Citations
Many cited preprints from 2024 and 2025 have already been formally published in major venues:
- **"Openfmnav..."** (`openfmnav`) -> Published in **ICRA 2024**.
- **"BeliefMapNav..."** (`beliefmapnav`) -> Published in **ICRA 2025**.
- **"ApexNav..."** (`apexnav`) -> Published in **ICRA 2025**.
- **"Strive..."** (`strive`) -> Published in **ICRA 2025**.
- **"Habitat 3.0..."** (`habitat`) -> Published in **ICLR 2024**.
- **"YOLOE..."** (`yoloe`) -> Published in **CVPR 2025**.
- **"Qwen3..."** (`qwen3`) -> Published in **ICML 2025**.
- **"VLM-3R..."** (`vlm3r`) -> Published in **CVPR 2025**.
- **"Ross3d..."** (`ross3d`) -> Published in **CVPR 2025**.
- **"Reasoning in Space..."** (`reasoning`) -> Published in **ICLR 2025**.

### 2. Missing Capitalization Protection
The bibliography lacks curly brace `{}` protection for numerous technical acronyms and proper nouns. Affected terms include:
- **Acronyms:** VLM, LLM, 3D, RGB-D, 3DGS, ZSON, CoT, VQA, RL, HM3D, MP3D, YOLOE, GLM, LMM, CVPR, ICCV, ICLR, ICML, NeurIPS, ICRA, IROS, WACV.
- **Proper Nouns:** Gemini, Gemma, Qwen, GPT-4, GPT-5.2, Matterport, Habitat, Python.

### 3. Formatting and Metadata Inconsistencies
- **Title Formatting**: In the `trihelper` entry, "Zero-shot object navigation" is lowercased, which may lead to incorrect rendering.
- **Journal Naming**: The `fmm` entry has "proceedings of the National Academy of Sciences" in lowercase.
- **Incomplete Entries**: The `habitat` entry uses `others` without fully specifying the author list or all standard fields.

## Conclusion
Updating the outdated preprint citations to their definitive versions and ensuring proper acronym protection will significantly improve the scholarly quality and professional presentation of the manuscript.
