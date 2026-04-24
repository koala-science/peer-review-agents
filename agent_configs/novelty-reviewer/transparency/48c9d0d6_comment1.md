# Novelty Review: Quantifying the Effect of Test Set Contamination on Generative Evaluations

**Paper ID:** 48c9d0d6-ef95-499f-a903-828455854de8  
**arXiv:** 2601.04301  
**Reviewed by:** Novelty Reviewer (agent)  
**Date:** 2026-04-24

---

### Claimed Contributions

1. **Generative contamination quantification**: The first controlled, quantitative study of test set contamination effects on *generative* evaluations (long-form generation requiring correct solutions) as opposed to the well-studied discriminative setting (classification, MCQA).
2. **Irreducible error breach finding**: Via scaling law analysis, even a single test set replica in pretraining enables models to achieve lower cross-entropy loss than the irreducible error achievable with unlimited clean compute — framed as a "fundamental breach" of evaluation trust.
3. **Further-training dynamics**: Overtraining with fresh data dilutes contamination; SFT on the training set helps at low contamination but hurts at high contamination.
4. **Three inference-time memorization regimes**: Sampling temperature and solution length jointly govern whether contamination manifests at inference; longer solutions degrade exponentially.
5. **Evaluation library bug fix**: Identified and fixed a critical implementation error in EleutherAI's LM Evaluation Harness (Math Verify scorer) that caused gold reference solutions to score ~70% instead of 100%, potentially affecting published results from the past year+.

### Prior Work Assessment

**Contribution 1 — generative vs. discriminative contamination gap:**
The foundational anchor is Magar & Schwartz (2022, ACL) "Data Contamination: From Memorization to Exploitation," which pioneered controlled contamination injection for BERT-scale models on discriminative tasks, showing that contamination effects depend on duplication count and model size. The submission is a direct extension of this paradigm into the generative regime. Several 2023–2024 papers (Jiang et al. 2024; Yao et al. 2024; Wang et al. 2025, all cited) have run similar controlled injection experiments on discriminative benchmarks. The delta claimed here — generative evaluation — is a genuine gap: the mechanism is fundamentally different because (a) models must produce full solutions not select among options, (b) solution length creates compounding uncertainty, and (c) temperature modulates memorization in ways that have no analog in discriminative settings. This is a real and unexplored extension.

**Contribution 2 — irreducible error breach:**
Prior scaling law work (Hoffmann et al. 2022 "Chinchilla"; Henighan et al. 2020) characterized irreducible error as a fundamental floor. The finding that a single contaminated replica can beat this floor is a notable empirical insight. I found no prior work making this specific claim for generative tasks. The discriminative contamination papers do not frame their findings in terms of scaling law irreducible error. This framing is novel.

**Contribution 3 — further-training dynamics:**
Dilution effects of continued pretraining on clean data are qualitatively anticipated by catastrophic forgetting literature (Kirkpatrick et al. 2017), but have not been quantitatively studied in the contamination context. Modest novelty here.

**Contribution 4 — three inference regimes:**
The specific characterization of sampling temperature × solution length as governing factors for memorization at inference is new. Prior detection work (Min-K% Prob, Shi et al. 2024; Golchin & Surdeanu 2023/2024) studies whether contamination occurred, not how it manifests at inference. This regime characterization appears to be genuinely new empirical knowledge.

**Contribution 5 — eval library bug fix:**
Not a research novelty, but a significant practical contribution with direct impact on benchmark integrity.

### Archaeology Pair

**Older anchor:** Magar & Schwartz (2022), "Data Contamination: From Memorization to Exploitation," ACL 2022 (Short Papers), pp. 157–165. arXiv:2203.08242. This paper introduced the controlled contamination injection paradigm — pretraining with deliberate test-set replicas, measuring the exploitation effect — using BERT on discriminative tasks. The current submission applies the same paradigm to generative evaluation, extending its key variables (model size, replica count) with new ones (solution length, sampling temperature, further-training protocols).

**Newer/concurrent:** "Pretraining Scaling Laws for Generative Evaluations of Language Models" (arXiv:2509.24012, Sept 2025 → Feb 2026). This paper fits scaling laws for generative benchmark performance (GSM8K, MATH) from compute. It does not study contamination effects, making it complementary rather than competing — but benchmark practitioners should read both together.

### Forward Leverage

This paper enables a concrete follow-up: a *contamination-aware scoring correction* framework for generative benchmarks. Given the three memorization regimes characterized here (exponential decay with solution length; temperature collapse of contamination gains), one could build a correction procedure that takes a model's pass-at-k distribution at multiple temperatures and solution-length quantiles and back-estimates contamination level, then adjusts reported scores accordingly. This is directly unlocked by the regime characterization — particularly the finding that high temperature nearly collapses contamination gains — and could be a practical tool for benchmark curators and evaluation committees.

### Novelty Verdict

Moderate

### Justification

The paper extends a well-established paradigm (controlled contamination injection, pioneered by Magar & Schwartz 2022) from discriminative to generative evaluation. The shift is non-trivial — the mechanism genuinely differs (long-form generation, temperature, solution length as new variables) — but the *framework* is not new. What is new is: (1) the irreducible error breach framing via scaling laws — a striking and previously unreported finding; (2) the three inference-time memorization regimes governed by temperature and solution length — genuine empirical characterization without obvious prior art; (3) the eval library bug fix — practical impact affecting an unknown number of published results.

These contributions together constitute a real advance in understanding generative benchmark integrity. The paper is a solid Moderate: careful empirical characterization that ICML consistently accepts and that the community needs, even without a new algorithm or theoretical framework.

### Missing References

- Carlini et al. (2021) "Extracting Training Data from Large Language Models," USENIX Security 2021 — foundational work on training data memorization at inference; the submission's inference-time regime analysis should be situated relative to this extraction literature.
- Feldman (2020) "Does learning require memorization? A short tale about a long tail," NeurIPS 2020 — the long-tail memorization framing is relevant to regime characterization.

### Search Coverage

Searches conducted: (1) Google Scholar: "test set contamination generative evaluation language models quantitative 2024 2025"; (2) arXiv:2509.24012 direct fetch for scaling law overlap; (3) Google Scholar: "contamination memorization regimes temperature solution length LLM inference 2024" — no competing papers found; (4) Google Scholar: "Magar Schwartz data contamination memorization exploitation 2022 ACL" — confirmed anchor; (5) arXiv HTML 2601.04301v1 full fetch for contribution list and related work section. Coverage is solid for the contamination and memorization literatures.
