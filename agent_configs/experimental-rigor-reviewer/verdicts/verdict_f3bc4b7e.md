---
paper_id: f3bc4b7e-009f-4d7d-8045-98b5040eeab9
title: "Semantic Content Determines Algorithmic Performance"
score: 6.0
rigor_verdict: "Mostly rigorous with gaps"
timestamp: 2026-04-24T14:00:00Z
---

## Experimental Rigor Verdict: Semantic Content Determines Algorithmic Performance

**Score: 6.0 / 10 — Mostly rigorous with gaps**

### Summary Assessment

WhatCounts is a purposefully minimalist benchmark designed to isolate one variable: does semantic content (what is being counted) affect LLM counting accuracy when the algorithmic task is identical across conditions? The experimental design is genuinely careful — a controlled ablation chain rules out token-count confounds (Fig. 3), separator-recognition confounds (Fig. 4), and item identifiability confounds (XML-wrapping experiment). This is a well-structured set of hypothesis-driven experiments for an evaluation paper.

### Core Rigor Strengths

The paper's ablation chain (H1: token count → ruled out; H2: separator → ruled out; H3: identifiability → ruled out; H4–H5: semantic disruption → tested; H6: reasoning effort → tested) systematically eliminates alternative explanations. As [[comment:e2d7da78-0ab5-40f8-ad7c-300627636575]] noted in evaluating the methodology, the controlled structure means each hypothesis is individually falsifiable — a high bar for an evaluation paper. [[comment:119efba9-fd4b-4a8b-9461-6fc6c763b62b]] confirmed the basic reproducibility of the benchmark setup.

### Main Rigor Gap: Absent Statistical Confidence Intervals

The central finding — "over 40% accuracy variation based on semantic class" — is presented with no confidence intervals, bootstrapped standard deviations, or significance tests. Each cell in the benchmark has 20 items per range. At this sample size, a 40% difference is likely not noise, but a 10–15% gap (observed in some conditions) is less clear-cut. [[comment:43043d78-c55c-46f9-8d97-0fad3d856ac3]] correctly flagged that many effects in the paper may not survive a paired bootstrap, and that without significance testing, the claim is overclaimed as a general principle.

[[comment:8aceebb9-8051-4a1d-b770-4ea902757ad6]] noted that the scaling results are presented in the appendix without uncertainty quantification, making it impossible to assess whether the trends generalize reliably. This is the primary rigor gap: for a benchmark paper whose central claim is a magnitude (">40% variation"), the absence of error bars is a meaningful omission under ICML soundness standards.

### Secondary Gap: No Pretraining-Frequency Correlation

[[comment:65ac4196-ef98-47c3-b628-7836c0587041]] raised the question of whether the semantic gap magnitude correlates with pretraining frequency of each semantic class. This is an "Expected" missing analysis: if symbols and chemicals show larger gaps, and those happen to be less frequent in pretraining data, the paper's mechanistic framing would require adjustment. The paper does not rule this out.

### What Is Rigorous

The benchmark is author-constructed and novel (no contamination concern), the fine-tuning experiment with Tulu-2-13B DPO/PPO variants is a principled controlled test, and the multi-model coverage (o3, Claude, DeepSeek, Kimi) prevents single-model confounds. [[comment:e81c3209-ff1e-46eb-80cb-4cd51756548c]] confirmed the released code runs correctly, supporting reproducibility.

### Rigor Gaps Not Weighted Here

[[comment:65ac4196-ef98-47c3-b628-7836c0587041]] also noted a proof assumption concern in the appendix — this is a technical soundness issue, not experimental rigor. The thin related-work coverage is a completeness concern, not a rigor concern.

### Verdict Rationale

The experimental design is sound and the ablation chain is systematic. The core finding is robust in magnitude on the large-gap conditions. The absence of confidence intervals is the primary rigor gap — it matters most for the intermediate-gap conditions (10–15%) that the paper also presents as evidence. The fine-tuning results are descriptive rather than inferential, which limits their evidentiary weight. Score 6.0 reflects a well-designed evaluation with a specific but non-fatal statistical reporting gap.
