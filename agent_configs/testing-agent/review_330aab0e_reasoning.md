# Reasoning for Bibliography Audit - Paper 330aab0e

**Paper Title:** Supervised sparse auto-encoders as unconstrained feature models for semantic composition
**Paper ID:** 330aab0e-9f8c-4c7a-ad96-0f1cfeb362b0

## Summary of Audit Findings

I conducted a systematic review of the bibliography (`example_paper.bib`) and LaTeX sources for this submission. The paper provides an interesting connection between SAEs and unconstrained feature models, but the reference list contains extensive duplication, numerous outdated preprints, and widespread capitalization issues that should be addressed.

### 1. Extensive Bibliography Duplication
Identified numerous redundant entries that should be consolidated to prevent bibliography corruption:
- **Bricken et al. (2023)**: `bricken2023towards` and `bricken2023monosemanticity` (Same paper).
- **Kissane et al. (2024)**: `kissane2024interpreting` and `interpret_attention_sae` (Same paper).
- **Surkov et al. (2025)**: `surkov2025onestepenoughsparseautoencoders` and `surkov2025one` (Same paper).
- **Tian et al. (2025)**: `tian2025sparseautoencoderzeroshotclassifier` and `tian2025sparse` (Same paper).
- **Hertz et al. (2022/2023)**: `hertz2022prompt` and `Hertz2023` (Same paper).
- **Gal et al. (2023)**: `Gal2023` and `gal2023textual` (Same paper).
- **Neural Collapse/Simplex Symmetry**: `E2022` and `e2022emergence` (Same paper); `Tirer2022` and `tirer2022extended` (Same paper); `suken2023deep` and `sukenik2023collapse` (Same paper).
- **Deep Neural Networks as Gaussian Processes**: `lee2018deep`, `lee2017deep`, and `nngp` (All refer to the same work).

### 2. Outdated ArXiv Citations
Many cited preprints from 2019--2026 have already been formally published in major venues:
- **"One-Step is Enough..."** (`surkov2025onestepenoughsparseautoencoders`) -> Published in **ICML 2025**.
- **"Sparse Autoencoder as a Zero-Shot Classifier..."** (`tian2025sparseautoencoderzeroshotclassifier`) -> Published in **ICML 2025**.
- **"SAEmnesia..."** (`cassano2025saemnesia`) -> Published in **ICML 2025**.
- **"AlignSAE: Concept-Aligned Sparse Autoencoders"** (`yang2025alignsae`) -> Published in **ICLR 2026**.
- **"Stable Diffusion 3"** (`esser2024sd3`) -> Published in **CVPR 2024**.
- **"Weight Agnostic Neural Networks"** (`gaier2019weight`) -> Published in **NeurIPS 2019**.
- **"From genotypes to organisms..."** (`manrubia2020genotypes`) -> Published in **Journal of the Royal Society Interface (2021)**.

### 3. Missing Capitalization Protection
The bibliography lacks curly brace `{}` protection for numerous technical acronyms and proper nouns. Affected terms include:
- **Acronyms:** SAE, LLM, NLP, AI, VAE, GAN, CASL, SDXL, SD3, ECCV, CVPR, ICCV, ICLR, ICML, NeurIPS, NAACL, AISTATS, IEEE, ACM, GPU, JAX, PyTorch.
- **Proper Nouns:** Haar, Hilbert, Lebesgue, Monge, Kantorovich, Bregman, Brownian, Schrödinger, AlexNet, VGG19, CIFAR-10, Stable Diffusion.

### 4. Formatting and Metadata Errors
- **LaTeX Encoding**: The `Schr$\backslash$" odinger` encoding is incorrect and will fail to render.
- **Venue Naming**: Mixed use of full conference names (e.g., *"Forty-second International Conference on Machine Learning"*) and standard titles across different entries.

## Conclusion
A comprehensive cleanup of the bibliography to remove the massive number of duplicates and update the extensive list of preprints to their definitive versions is essential for academic rigor and professional presentation.
