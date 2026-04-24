# Reasoning for Citation Audit - Paper 65af1f63 (RAD)

## Overview
I performed a systematic audit of the bibliography file (`main.bib`) for the paper "Is Training Necessary for Anomaly Detection?". The goal was to identify outdated citations, formatting inconsistencies, and BibTeX errors that affect the final presentation of the references.

## Findings

### 1. Outdated arXiv Citations
Several foundational works in vision transformers and self-supervised learning are cited as arXiv preprints despite having been published in major conferences/journals by early 2026:
- `bao2021beit` (BEiT v1): Cited as arXiv 2021; published at ICLR 2022.
- `peng2022beit` (BEiT v2): Cited as arXiv 2022; published at ICLR 2023.
- `zhou2021ibot` (iBOT): Cited as arXiv 2021; published at ICLR 2022.
- `oquab2023dinov2` (DINOv2): Cited as arXiv 2023; published at TMLR 2024.

### 2. BibTeX Casing and Bracing
The ICML bibliography style (`icml2026.bst`) enforces sentence case for titles. Many method acronyms and proper nouns are not enclosed in braces `{}` and will thus be incorrectly lowercased in the rendered PDF:
- `MVTec AD` in `bergmann2019mvtec` will become "Mvtec ad".
- `Mambaad` in `he2024mambaad` should be `{MambaAD}`.
- `Draem` in `zavrtanik2021draem` should be `{DRAEM}`.
- `Pni` in `bae2023pni` should be `{PNI}`.
- `Univad` in `gu2025univad` should be `{UniVAD}`.
- `Dinomaly` in `guo2025dinomaly` should be `{Dinomaly}` (or similar).
- `Destseg` in `zhang2023destseg` should be `{DeSTSeg}`.

### 3. Venue Naming Inconsistency
There are inconsistencies in how major conferences are named across entries:
- `Proceedings of the Computer Vision and Pattern Recognition Conference` (in `gu2025univad` and `guo2025dinomaly`) is non-standard.
- `Proceedings of the IEEE/CVF conference on computer vision and pattern recognition` (in `wyatt2022anoddpm`) uses lowercase for "conference...".
- Standardizing to `Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)` would be more professional.

## Conclusion
The bibliography is technically sound but requires minor curation to reach professional publication standards. Correcting these citations will improve the scholarly rigor of the submission.
