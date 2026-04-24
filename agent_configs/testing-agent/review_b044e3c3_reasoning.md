# Reasoning for Reference Check - Paper b044e3c3

I performed a systematic review of the bibliography and formatting for the paper "A Unified SPD Token Transformer Framework for EEG Classification: Systematic Comparison of Geometric Embeddings" (ID: b044e3c3-4a8e-4a74-a3b8-13584deba079).

## Findings

### 1. Significant Attribution and Metadata Error
The entry for **FBCNet** (`ingolfsson2021fbconet`) contains a major error. It attributes the paper to *Ingolfsson et al.* and lists it as a 2021 IEEE SMC conference paper. However, **FBCNet** was actually authored by **Ravikiran Mane et al.** and is primarily cited as an **arXiv preprint (2104.01233)**. It appears the metadata from the `ingolfsson2020eegtcnet` entry was incorrectly duplicated.

### 2. Outdated Publication Details
- **ManifoldNet** (`chakraborty2020manifoldnet`) was formally published in **IEEE Transactions on Pattern Analysis and Machine Intelligence (TPAMI)** in **2022** (Volume 44, Issue 2). The current bib entry lists it as "Published online 2020".

### 3. Missing Capitalization Protection in BibTeX
Many domain-specific acronyms in titles are missing curly brace protection `{}`. This will cause them to be rendered in lowercase by many bibliography styles, which is incorrect for technical terms.
- Impacted terms: `SPD`, `EEG`, `BCI`, `MAtt`, `LMDA-Net`, `MAMEM`, `DPR`, `FBCNet`, `EEG-TCNet`, `SPDNet`, `DeepKSPD`, `ManifoldNet`.

### 4. Minor Inconsistencies
- The entry `barachant2013multiclass` has the key `2013` but the `year` field is `2012`. While it may have been published online in 2011/2012, the key mismatch is slightly confusing.
- Conference names like `Proceedings of the AAAI Conference on Artificial Intelligence` and `Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition` are used correctly, but standardizing the use of "IEEE/CVF" for CVPR and other similar details would improve consistency.

## Evidence
The findings were verified by cross-referencing `REFERENCES.bib` with the IEEE Xplore Digital Library, Google Scholar, and arXiv as of April 2026.
