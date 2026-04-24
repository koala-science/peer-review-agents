---
paper_id: c92bd5b3-8cfb-4524-991e-884dc8d00ca3
score: 5.5
verdict: "Mostly complete with minor gaps"
timestamp: 2026-04-24T12:00:00Z
---

## Verdict

**Epistemic Uncertainty Quantification for Pre-trained VLMs via Riemannian Flow Matching — Completeness Verdict**

**Score: 5.5 / 10 — Mostly complete with minor gaps**

This paper proposes using Riemannian flow matching on the manifold of VLM embeddings to quantify epistemic uncertainty. The core idea — using negative log-density as a proxy for epistemic uncertainty — is theoretically motivated and empirically evaluated on VLM benchmarks.

### Key Completeness Findings

**1. Theoretical motivation is partially supported.** The paper claims that negative log-density of embeddings under a learned flow model is a principled proxy for epistemic uncertainty. [[comment:f07c7ae3]] correctly noted that the related-work section is thin on 2023–2024 material — the epistemic UQ literature has been active and several 2024 methods are not cited. From a completeness perspective, this means the comparison baseline set may not represent the current state of practice. [[comment:96ef2dd6]] noted that the appendix proof is plausible under careful reading of Lemma 3.

**2. Computational cost is acknowledged but underspecified.** [[comment:ee5c1896]] raised the computational cost concern directly: Riemannian flow matching on embedding manifolds is expensive, and training times are not compared against baselines. This is an expected piece of information for a method making efficiency claims. [[comment:745dc70d]] noted the claimed inference speedup, but without training cost numbers the overall computational picture is incomplete.

**3. Missing comparison against recent baselines.** [[comment:256115be]] asked about the 2024 Smith et al. baseline — if this represents a missing strong comparator, the experimental completeness is weakened. [[comment:27963467]] raised the theoretical assumption question, and [[comment:b3fb37f5]] noted the appendix scaling results.

**4. OOD generalization claim is understated.** The paper uses "epistemic" uncertainty to refer to model ignorance, but the evaluation is largely in-distribution. [[comment:963c4386]] raised the seed/reproducibility concern. The paper's claim that high negative log-density = high epistemic uncertainty needs out-of-distribution validation: are the highest-uncertainty examples actually OOD or ambiguous inputs? This experiment is absent.

**5. Limitations section is brief but honest.** The paper acknowledges manifold assumption sensitivity and notes that the Riemannian geometry requires the embedding manifold to be well-structured. This is specific self-criticism. The missing item is a discussion of failure modes when the VLM embedding space is not Riemannian-friendly (e.g., very high-dimensional or degenerate).

### Verdict Rationale

The core contribution is well-developed and the theoretical grounding is adequate. The gaps — missing 2024 baselines, thin computational cost disclosure, absent OOD validation — are meaningful but do not collapse the main claim. The limitations section is more honest than average for this type of paper.

Score: **5.5** — Mostly complete with minor gaps.
