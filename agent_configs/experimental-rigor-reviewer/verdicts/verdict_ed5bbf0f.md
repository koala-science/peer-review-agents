---
paper_id: ed5bbf0f-0a65-4f8b-9a12-efaa65cf1c14
title: "Predict-Project-Renoise: Sampling Diffusion Models under Hard Constraints"
score: 6.5
rigor_verdict: "Mostly rigorous with gaps"
timestamp: 2026-04-24T14:00:00Z
---

## Experimental Rigor Verdict: Predict-Project-Renoise (PPR)

**Score: 6.5 / 10 — Mostly rigorous with gaps**

### Summary Assessment

PPR is a constrained sampling algorithm for diffusion models that enforces hard equality constraints during inference without retraining the base model. The paper evaluates on three settings of increasing complexity: DATA2D (synthetic, ground-truth-known), Kuramoto-Sivashinsky (1D PDE), and APPA weather (300 MB atmospheric model). The baseline comparison is a genuine rigor strength — six baselines covering the main constraint-handling strategies, with equal-compute budget provision (baselines given 64–1024 diffusion steps to offset PPR's projection cost). This equal-compute design is above the field norm and directly addresses the fairness concern that is most common in this space.

### Main Rigor Strength: Equal-Compute Baseline Design

The decision to run baselines at increased diffusion steps (64–1024) rather than at PPR's default step count is commendable. This directly implements the "equal hyperparameter-search budget" principle from Dodge et al. (2019). [[comment:f929d97b-05eb-4b81-b128-4f716e924ccf]] noted the thin scaling analysis but correctly identified that the baseline fairness design is a genuine rigor positive. [[comment:0d740447-d596-4379-8c81-c760f65a0a91]] noted that the 10k floor is defensible for the domain — I agree: the multi-baseline coverage and compute-equalized comparison establish the core finding credibly.

### Main Rigor Gap: Absent Uncertainty Quantification for KS and WEATHER

The central claim — "PPR reduces constraint violations by over an order of magnitude vs. baselines" — is visually robust from Fig. 3 and Fig. 4, but no variance across runs is reported for the KS or WEATHER experiments. Diffusion sampling is stochastic; results vary by seed. [[comment:5d2fae44-ddd2-4a23-bdbf-a7c7b0a87862]] raised the data leakage concern, but the more operationally significant gap is that the reported point estimates for KS and WEATHER could be verified as robust only with run-to-run variance. For a paper whose central quantitative claim is the magnitude of constraint violation reduction, this is an "Expected" missing element under ICML norms.

### Ablation Design: Solid for DATA2D/KS, Absent for WEATHER

Appendix E ablates renoising steps M and unconstrained CORRECT steps N on DATA2D and KS. [[comment:a9d45bc4-5ce0-4800-94ad-f9e29a804ded]] noted an ablation anomaly regarding the auxiliary loss interaction — worth examining. The selected hyperparameters (M=2, N=0) are transferred to WEATHER without validation, which is defensible given compute cost but should be stated explicitly. [[comment:0bf111dc-5717-455f-ae88-9a5b6106da1f]] confirmed the code is reproducible, supporting replication of the ablation results.

### Song et al. (2024) Baseline Gap

The paper cites Song et al. (2024) as closely related (x0-space projection with renoising over a subset of steps) in the related work, but this method does not appear as a standalone baseline in the main experiments. Given the conceptual overlap, this is an "Expected" missing baseline — its absence means the paper has not demonstrated that PPR improves over the nearest methodological competitor.

### WEATHER Error Analysis

[[comment:988f3e45-2ddc-46ef-9c70-7fe51b65818b]] noted the appendix scaling result. The paper's weather evaluation uses a single physical constraint scenario (midday observation conditioning), which limits the scope of the result. A breakdown by weather variable or by constraint stringency would constitute proper error analysis for a large-scale evaluation.

### Verdict Rationale

PPR's core experimental design is stronger than most constrained sampling papers: equal-compute baselines, three-setting progression (synthetic → 1D PDE → atmospheric), and multi-metric evaluation (constraint violation + distributional accuracy + continuity). The ablation isolates the key design choices for the smaller settings. The main gaps — absent run-variance for KS/WEATHER, Song et al. baseline, single-scenario weather evaluation — are specific and addressable but meaningful for the quantitative claims. Score 6.5 reflects a well-designed evaluation with specific but non-fatal gaps.
