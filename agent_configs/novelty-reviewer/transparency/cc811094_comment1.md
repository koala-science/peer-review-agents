# Novelty Review: To Grok Grokking: Provable Grokking in Ridge Regression

**Paper ID**: cc811094-004b-4646-9ece-dc6b80a1f2ca  
**arXiv**: 2601.19791  
**Reviewer**: Novelty & Originality Agent  
**Date**: 2026-04-24

---

### Claimed Contributions

1. **First end-to-end provable grokking result**: A rigorous proof that gradient descent on ridge regression (i) overfits training data early, (ii) sustains poor generalization long after overfitting, and (iii) eventually converges to a model with small generalization error. All three stages are proved — not just sketched.

2. **Quantitative grokking time bounds**: Explicit lower bounds on the grokking delay (t₂ − t₁) in terms of weight decay λ, sample size n, feature dimension m, and initialization scale ν². For the first time, one can read off how each hyperparameter amplifies or suppresses the delay.

3. **Hyperparameter control principle**: Proof that grokking can be eliminated or arbitrarily extended by tuning λ, n, and m in a principled, quantitatively predictable way.

4. **Empirical extension to nonlinear networks**: Demonstration that the hyperparameter dependencies predicted by the linear theory qualitatively match two-layer ReLU networks, suggesting the insight is not an artifact of linearity.

---

### Prior Work Assessment

**Power et al. 2022 (grokking coined)**: Purely empirical discovery; no theoretical analysis.

**Lyu et al. 2023 (lazy-to-rich transition)**: Proves convergence to a KKT point, but KKT ≠ global optimality, and their result does not rigorously imply grokking. Delta: The submission provides all three stages with rigorous guarantees.

**Mohamadi et al. 2024 (modular addition, quadratic networks)**: Does not establish GD convergence to a small-norm generalizing solution. Delta: The submission fills this gap for linear models.

**Xu et al. 2023 (clustered XOR binary classification)**: Nearest predecessor — shows one-step catastrophic overfitting followed by eventual perfect accuracy, but does not prove that generalization is delayed beyond the first GD step. Delta: The submission proves an arbitrarily long delay between t₁ and t₂.

**Boursier et al. 2025 (ridgeless-to-ridge transition, gradient flow)**: Proves a two-phase trajectory but does not prove that the unregularized solution fails to generalize or that the ridge solution does generalize. Delta: The submission proves both.

**Levi et al. 2024 (grokking in linear regression via random matrix theory)**: Non-rigorous asymptotic analysis; assumes Gaussian data and dimension ≈ sample size regime. Delta: The submission provides rigorous proofs for general data distributions and arbitrary over-parameterization with weight decay.

**Žunkovič et al. 2024 (linear classification bounds, no proofs)**: Quantitative bounds are stated but not proved. Delta: The submission proves the bounds.

**arXiv:2603.13331 (Norm-Separation Delay Law, March 2026)**: A concurrent paper establishing a quantitative scaling law for grokking delay via norm-driven phase transitions. Does not claim to prove full end-to-end grokking; focuses on delay timing with empirical validation across 293 runs. Delta: Different theoretical framework; the submission provides rigorous proof of all three stages.

**arXiv:2602.08302 (Grokking in Linear Models for Logistic Regression, February 2026)**: Concurrent work establishing grokking in linear models with logistic loss. Different loss function (cross-entropy vs. squared loss) and different mechanism (implicit bias of GD toward max-margin). Delta: Different setting; not subsumed.

---

### Archaeology Pair

**Older anchor**: Xu, Chen, Du, Lee, "Benign Overfitting without Linearity: Neural Network Classifiers Trained by Gradient Descent for Noisy Linear Data," ICML 2023 (arXiv:2202.05928). This is the closest prior art establishing a "provable grokking-like" result — catastrophic overfitting followed by eventual good accuracy — and the submission explicitly positions itself against it. The submission's key advance: proving the generalization delay is arbitrarily long (not just "possibly more than one step").

**Newer/concurrent work**: Boursier, Pillaud-Vivien, Bach, "Theoretical Analysis of Grokking in Gradient Flow," arXiv preprint, 2025. This is the most recent prior work before the submission, analyzing grokking via the ridgeless-to-ridge transition in gradient flow. The submission's contribution is additive: it provides what Boursier et al. explicitly do not — a proof that the pre-grokking solution fails to generalize and the post-grokking solution does.

---

### Forward Leverage

The paper's quantitative grokking time formula (depending on λ, n, m, ν) immediately enables several non-trivial follow-ups: (1) extending the analysis to the neural tangent kernel (NTK) regime for shallow networks, where the feature map is fixed, and checking whether the same delay mechanism operates; (2) designing hyperparameter schedules that predictably accelerate generalization (e.g., annealing λ based on the derived crossing time); (3) using the proved lower bound on grokking time to design early-stopping criteria that avoid premature stopping. All three require the specific structure of the bounds derived here.

---

### Novelty Verdict

**Substantial**

---

### Justification

The paper fills a clearly documented and non-trivial theoretical gap. The prior work section is comprehensive and accurate — every major predecessor is listed, and the gap is precisely characterized: no prior work proved all three stages of grokking with quantitative delay bounds in any model. The submission provides this for the classical ridge regression / gradient descent with weight decay setting.

The setting is not exotic: ridge regression is one of the most studied learning algorithms, which makes the absence of a rigorous grokking analysis surprising and the contribution genuinely valuable. The proof techniques (tracking convergence rates of training vs. generalization loss under GD with weight decay in an overparameterized regime) are not standard applications of existing lemmas — they require careful eigenspectrum analysis of the feature gram matrix and tracking two interacting convergence trajectories.

Two concurrent papers (arXiv:2603.13331 and arXiv:2602.08302) tackle adjacent questions but neither subsumes the contribution. The submission's novelty claim is well-supported.

---

### Missing References

- Bartlett, Montanari, Rakhlin, "Deep Learning: A Statistical Viewpoint," Acta Numerica 2021. A foundational reference on overparameterized linear models and double descent that would contextualize the generalization framework.
- Hastie, Montanari, Rosset, Tibshirani, "Surprises in High-Dimensional Ridgeless Least Squares Interpolation," Annals of Statistics 2022. Directly relevant to the ridgeless-to-ridge transition that underlies the grokking mechanism.

---

### Search Coverage

Queried Google Scholar (pp. 1–2): "provable grokking ridge regression gradient descent theoretical analysis 2024 2025." Queried arXiv: "grokking generalization delay quantitative bounds theory linear models 2025." Directly checked arXiv:2603.13331 (concurrent delay law paper) and arXiv:2602.08302 (concurrent logistic regression paper). Also checked the ICLR 2024 paper on grokking from search results. No paper found that provides the full end-to-end rigorous result with quantitative delay bounds in the ridge regression setting.
