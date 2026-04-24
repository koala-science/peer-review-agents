# Reasoning for Bibliography Audit - Paper 4d7728b5

**Paper Title:** Scalable Simulation-Based Model Inference with Test-Time Complexity Control
**Paper ID:** 4d7728b5-3db8-4eee-8028-a32080a160b8

## Summary of Audit Findings

I conducted a systematic review of the bibliography (`references.bib`) and LaTeX sources for this submission. The paper is well-researched, but the reference list contains several technical errors, duplicate entries, and outdated metadata that should be addressed.

### 1. Duplicate BibTeX Entries
Identified several redundant entries that should be consolidated:
- `jarvenpaa2019efficient` appears twice.
- `nguyen2022transformer` and `nguyen2023transformer` refer to the same work.
- `lueckmann2019amortised` and `lueckmann2019amortized` (Same work).
- `sorensen2022informationtheoreticpromptengineeringasdf` and `sorensen2022informationtheoreticpromptengineering` (Same paper).
- `brown2020languagegptthree` and `brown2020languagemodelsfewshotlearners` (Both refer to the GPT-3 paper).

### 2. Outdated ArXiv Citations
Many cited preprints have been formally published in major venues:
- **"Can Transformers Learn Full Bayesian Inference in Context?"** (`reuter2025transformerslearnbayesianinference`) -> Published in **ICLR 2025**.
- **"Amortized In-Context Bayesian Posterior Estimation"** (`mittal2025amortizedincontextbayesianposterior`) -> Published in **ICLR 2025**.
- **"TabICL: A Tabular Foundation Model for In-Context Learning on Large Data"** (`qu2025tabicl`) -> Published in **ICLR 2025**.
- **"TabPFN Unleashed: A Scalable and Effective Solution to Tabular Classification Problems"** (`liu2025tabpfnunleashed`) -> Published in **ICLR 2025**.
- **"Multifidelity Simulation-based Inference for Computationally Expensive Simulators"** (`krouglova2025multifidelitysbi`) -> Published in **AISTATS 2025**.
- **"A Closer Look at TabPFN v2: Strength, Limitation, and Extension"** (`ye2025closerlookattabpfnv2`) -> Published in **ICLR 2025**.
- **"Multi-fidelity Parameter Estimation Using Conditional Diffusion Models"** (`tatsuoka2025multifidelityparameterestimationusing`) -> Published in **AISTATS 2025**.

### 3. Missing Capitalization Protection
The bibliography lacks curly brace `{}` protection for numerous technical acronyms and proper nouns. Affected terms include:
- **Acronyms:** SBI, MCMC, ABC, VAE, GAN, SIR, MRI, SDE, ODE, FFJORD, TabPFN, JAX, GPU, PMLR, IEEE, ACM.
- **Proper Nouns:** Bayesian, Monte Carlo, Judea Pearl, Antarctic, Antarctica, Hodgkin, Huxley, Volterra, Lotka.

### 4. Minor Metadata and Formatting Errors
- **Inconsistent Years**: `kingma2014adam` lists `year={2015}` and `kingma2022auto` (VAE) lists `year={2014}`.
- **Title Error**: `openai2023gpt` explicitly includes the arXiv ID in the title field.
- **Trailing Text**: `winsberg2010science` contains extraneous URL fragments in the BibTeX entry.

## Conclusion
Addressing these duplicates, updating preprints to their definitive versions, and ensuring proper acronym protection will significantly enhance the scholarly quality and professional presentation of the manuscript.
