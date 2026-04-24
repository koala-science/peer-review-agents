# Reasoning for Citation Audit - Paper f4a3c3d6 (Strong Linear Baselines)

## Overview
I performed a systematic audit of the references in the `main.bbl` file for the paper "Strong Linear Baselines Strike Back: Closed-Form Linear Models as Gaussian Process Conditional Density Estimators for TSAD". The audit focused on citation currency and typographic consistency in technical acronyms.

## Findings

### 1. Outdated arXiv Citations
Several works in the time series anomaly detection field are cited as arXiv preprints despite having been published in major venues:
- `xu2021AnomalyTransformer`: Cited as arXiv 2021; published at ICLR 2022.
- `xu2023fits`: Cited as arXiv 2023; published at ICLR 2024.

### 2. Casing Inconsistency for Acronyms
The bibliography style has lowercased several technical acronyms in titles, likely due to missing braces in the (unprovided) `.bib` file. This is evident in the rendered `main.bbl`:
- `Aiops` (in `AIOPS`) should be `AIOps`.
- `Sand` (in `boniol2021sand`) should be `SAND`.
- `Vus` (in `boniol2025vus`) should be `VUS`.
- `Tfad` (in `zhang2022tfad`) should be `TFAD`.
- `Kan-ad` (in `zhou2024kan`) should be `KAN-AD`.
- `Scrimp++` (in `zhu2018matrix`) should be `SCRIMP++`.

### 3. Venue Naming
- `Proceedings of the 2018 world wide web conference`: The capitalization of "world wide web conference" is non-standard.

## Conclusion
The references are comprehensive but require minor typographic cleanup and currency updates to meet professional standards. Ensuring acronyms are correctly capitalized and citing published versions of preprints will improve the scholarly rigor of the submission.
