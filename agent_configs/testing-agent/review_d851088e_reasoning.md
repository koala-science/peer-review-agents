# Reasoning for Bibliography Audit - Paper d851088e

**Paper Title:** Harmful Overfitting in Sobolev Spaces
**Paper ID:** d851088e-cad0-44fe-abfc-2fb062136391

## Summary of Audit Findings

I conducted a systematic review of the bibliography (`references.bib`) and LaTeX sources for this submission. The paper provides a deep theoretical analysis of overfitting in Sobolev spaces, but the reference list is exceptionally cluttered with duplicate entries, outdated metadata, and capitalization issues that must be addressed to meet professional academic standards.

### 1. Extreme Bibliography Duplication
The bibliography contains an unusually high number of redundant entries that should be consolidated to ensure consistency and prevent corruption:
- **Bartlett et al. (2020)**: `doi:10.1073/pnas.1907378117` and `doi:10.1073/pnas.1907378117-DUPLICATE`.
- **Belkin et al. (2019)**: `belkin2019reconciling`, `belkin2019reconciling-DUPLICATE`, and `doi:10.1073/pnas.1903070116-DUPLICATE`.
- **Rudelson & Vershynin (2009)**: `sing_vals_random_mat`, `rudelson2009smallest`, and `smallest_sing_val`.
- **Vershynin (2018)**: `vershynin_2018` and `vershynin_2018-DUPLICATE`.
- **Montanari et al. (2023)**: `montanari2023universality`/`montanari2023universality-DUPLICATE` and `montanari2023generalization`/`montanari2023generalization-DUPLICATE`.
- **George et al. (2023)**, **Kornowski et al. (2023)**, **Frei et al. (2022)**, **Cao et al. (2022)**, **Kou et al. (2023)**, **Mei & Montanari (2019)**, **Liang et al. (2019)**, **Adlam & Pennington (2020)**, **Ji & Telgarsky (2020)**: All have corresponding `-OLD` or `-DUPLICATE` entries.

### 2. Outdated ArXiv Citations
Several cited preprints have already been formally published in major venues:
- **"Universality of max-margin classifiers"** (`montanari2023universality`) -> Published in **PNAS 2024**.
- **"The generalization error of max-margin linear classifiers..."** (`montanari2023generalization`) -> Published in **Annals of Statistics (2024)**.
- **"Bounds for the smallest eigenvalue of the NTK..."** (`karhadkar2024bounds`) -> Published in **Journal of Machine Learning Research (2024)**.
- **"A function space view of bounded norm infinite width relu nets..."** (`ongie2019function`) -> Published in **ICLR 2020**.
- **"Sobolev norm inconsistency of kernel interpolation"** (`yang2025sobolev`) -> Published in **ICLR 2025**.
- **"Noisy interpolation learning with shallow univariate ReLU networks"** (`joshi2023noisy`) -> Published in **NeurIPS 2023**.

### 3. Missing Capitalization Protection
The bibliography lacks curly brace `{}` protection for numerous technical acronyms and proper nouns. Affected terms include:
- **Acronyms:** ReLU, SGD, KKT, ODE, NTK, CNTK, JMLR, TMLR, PNAS, ICLR, ICML, NeurIPS, AAAI, AISTATS, VLDB, ACM, IEEE, SIAM, JSAIT, ISIT.
- **Proper Nouns:** Sobolev, Fournier, Gaussian, Lipschitz, Hilbert, Lebesgue, Bernoulli, Beta, Dirichlet, Karush, Kuhn, Tucker, Moore, Penrose, AlexNet, VGG19, CIFAR-10, Laplace, Poisson, Schrödinger.

### 4. Formatting and Metadata Errors
- **Non-standard Fields**: Widespread use of `nodoi`, `noeditor`, `nomonth`, `noDOI`, and `noissn` fields, which are non-standard and may interfere with some BibTeX styles.
- **LaTeX Encoding**: The `Schr$\backslash$" odinger` encoding is incorrect and will fail to render.

## Conclusion
A comprehensive cleanup of the bibliography to remove the massive number of duplicates and update preprints to their definitive versions is essential for the manuscript's academic rigor and professional presentation.
