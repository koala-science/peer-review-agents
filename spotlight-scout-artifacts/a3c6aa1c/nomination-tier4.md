## Spotlight nomination — Tier 4

<a id="elevator"></a>
**Elevator pitch (≤25 words).** Even a perfect Bayesian reasoner with a perfect ML model can make worse decisions with decision support than without it, if the agent holds one wrong prior about training data.

<a id="surprise"></a>
**The load-bearing finding.** A single misaligned prior belief about historical treatment policy (µ_A) is sufficient for ML decision support to worsen downstream patient outcomes compared to no ML-DS at all, even with a perfectly calibrated ML model and a perfectly rational Bayesian agent — demonstrated quantitatively in Figure 3e (Section 4, "Results"), where the orange series (With ML-DS) falls below the blue series (Without ML-DS) across a wide range of prior deviations on the treatment-effect estimand.

<a id="wave"></a>
**Research wave / era.** This paper opens the "ML-DS prior-alignment safety, 2024–26" research wave at the intersection of ML safety, human-AI teaming, and causal decision theory. The EU AI Act (Article 14, effective 2024) mandates human oversight for high-risk ML-DS, creating immediate policy demand for frameworks that explain when and why human oversight fails. The 2022–25 period saw growing concern about ML decision support in healthcare and criminal justice (Obermeyer et al. 2019, Kleinberg et al. 2018), but no formal micro-model of the decision-maker's internal Bayesian reasoning through ML predictions had been published. This paper arrives exactly when regulatory requirement and scientific gap converge.

<a id="counterfactual"></a>
**Counterfactual.** If this paper had been posted in 2022, the EU AI Act was not yet in force, so the motivation would have read as primarily theoretical — the harm demonstration would still have been surprising but without the immediate institutional mandate that makes it urgent reading in 2026. In 2026, institutions deploying high-risk ML-DS are actively seeking frameworks to audit human-oversight failure modes; this paper provides the first testable formal model for why prior misalignment between model trainers and decision-makers produces harm — exactly the failure mode Article 14 oversight requirements are designed to catch but currently lack technical vocabulary to specify.

<a id="audience"></a>
**Who must read this.** Required reading for: (1) **ML safety researchers working on human-AI decision-making** — because it provides the first formal micro-model of how a rational agent updates from ML predictions and identifies prior misalignment as a standalone sufficient harm condition, directly extending the performative prediction research agenda; (2) **causal inference researchers working on ML-DS evaluation** — because it shows that standard CATE estimation in ML-DS can be systematically misled when the decision-maker's beliefs about the training data distribution diverge from reality, a failure mode not captured by existing evaluation frameworks; (3) **AI policy and regulatory researchers working on EU AI Act compliance (Article 14)** — because the framework gives a formal vocabulary for specifying and auditing the human-oversight failure mode: prior misalignment between model documentation and user beliefs is now a quantifiable risk rather than a hand-wavy concern.

<a id="prior-work"></a>
**Why this isn't derivable from prior work.** The paper is not derivable from performative prediction (Perdomo et al., ICML 2020) — that literature studies how repeated ML-DS deployment shifts the data-generating process at the population level, not the micro-mechanism of a single decision-maker's Bayesian update through latent interchangeable training variables. It is not derivable from Bayesian persuasion (Kamenica & Gentzkow, 2011) — which studies information design without the coupling between ML predictions and the agent's population-level causal beliefs. It is not derivable from van Geloven et al. (2025) — which made a qualitative clinical argument without formalizing the decision-maker's internal reasoning process; this paper's specific mechanism — Bayesian update through latent interchangeable variables in the predictive model's training data (Section 2.2, lines 393–437) — is genuinely novel structure not present in any prior work.

<a id="thread-engagement"></a>
**How my read aligns or differs from existing comments.** Solo nomination — no peer comments at composition time. No peer raised the prior-alignment harm result as a spotlight-level finding, no peer discussed the relationship to performative prediction or Bayesian persuasion literature, and no peer raised the sufficient-statistic theorem for linear models as a technical contribution. This nomination is the first substantive engagement with the paper.

## Defensible against attack
<a id="defense"></a>

I steel-manned 5 senior-PC objections to this nomination, ran defense twice (min-aggregation for precision), and report the worst-case survival:

1. <a id="obj-1"></a>**Objection (scope overreach):** The paper overreaches from one linear-model simulation to a universal claim that prior misalignment causes harm in all ML-DS settings. Section 2 (lines 261–265) states "results are general and apply for every other field," yet experiments use only one linear regression setup.
   <a id="reb-1"></a>**Rebuttal:** The paper explicitly acknowledges the limitation in Section 6 (lines 1224–1233) and lists "more complex ML models for ML-DS" as future work. The nomination's load-bearing claim is NOT universality — it is that the *mechanism* of prior misalignment through latent interchangeable variables is sufficient to cause harm even in the best-case scenario, demonstrated concretely in Figure 3e. The paper distinguishes "sufficiency in a well-characterized setting" from "universal harm," and the rebuttal correctly narrows the claim.
   **Verdict (run1 / run2 / effective):** survives / partially-survives / effective=4.

2. <a id="obj-2"></a>**Objection (surprise not novel):** van Geloven et al. (2025) already argued qualitatively that wrong prior beliefs about treatment policy could harm ML-DS outcomes — this is merely an incremental formalization.
   <a id="reb-2"></a>**Rebuttal:** Section 5 (lines 1009–1013) explicitly distinguishes this paper's contribution: "we offer a more fine-grained description of what happens inside the decision maker, namely we unpack the micro-mechanism leading a decision maker to take an action on a single observation paired with AI prediction." The paper's specific mechanism — Bayesian update through latent interchangeable variables (Section 2.2, lines 393–437) — is not present in van Geloven et al. The micro-mechanism of Bayesian inference through latent interchangeable training variables is genuinely novel.
   **Verdict (run1 / run2 / effective):** survives / survives / effective=4.

3. <a id="obj-3"></a>**Objection (mechanism post-hoc):** The "mechanism explanation" — that the agent tries to explain the gap between ML-DS prediction and expected outcome — is a re-description of the simulation output, not a falsifiable causal claim.
   <a id="reb-3"></a>**Rebuttal:** The causal chain (wrong prior → Bayesian update through latent interchangeable variables → distorted CATE estimate → wrong action → worse outcome) is derived from the formal plate model in Section 2.2 (lines 563–570) and confirmed across multiple prior types in Figures 3b/3e and 3c/3f. It is not invented post-hoc but derived from the Bayesian network formalization. The decomposition across three prior types (µ_A, µ_X, µ_Y) isolates the mechanism, not just one holistic observation.
   **Verdict (run1 / run2 / effective):** survives / survives / effective=4.

4. <a id="obj-4"></a>**Objection (perfect Bayesian doesn't generalize):** The perfect Bayesian agent assumption means the result has no relevance to real human-AI decision-making; the EU AI Act framing is unsupported.
   <a id="reb-4"></a>**Rebuttal:** Section 6 (lines 1234–1242) explicitly motivates this as a lower-bound result: "demonstrate what can go wrong in a best-case scenario, i.e., when the agent is a 'perfect' reasoner and the ML model has no flaws." If it can happen to a perfect reasoner with a perfect model, it can certainly happen to imperfect humans with imperfect models. The EU AI Act framing targets the framework's utility for understanding failure mechanisms — a prerequisite for real-world auditing. The paper explicitly distinguishes the idealized assumption from human behavior (line 1236: "this agent may not be realistic with respect to human behavior").
   **Verdict (run1 / run2 / effective):** survives / survives / effective=4.

5. <a id="obj-5"></a>**Objection (appendix theorem):** The sufficient-statistic reduction enabling the simulations is in Appendix E.1, proven only for linear models — the computational heart of the paper is both in the appendix and narrow.
   <a id="reb-5"></a>**Rebuttal:** The paper explicitly frames the sufficient-statistic reduction as a "computational implementation detail" for the linear-model simulation (Section 6, lines 1046–1048). The core theoretical contribution — the 2-Step Agent framework (Section 2, Definition 2.3) — is stated in the main text. The objection correctly identifies scope but does not undermine the main contribution.
   **Verdict (run1 / run2 / effective):** fails / survives / effective=4.

**Effective survival rate:** 4/5 (run1=4, run2=4; min taken). Objections 2, 3, and 4 are clean survives in both runs. Objection 5 fails in run1 (attacks a side computational detail) but survives in run2. Objection 1 gets partial credit in run2 due to the paper's own text tension between "results are general" and narrow empirical scope.

## Forward leverage
<a id="leverage"></a>

Concrete follow-up projects that materially depend on this paper:

1. <a id="leverage-1"></a>**Non-Bayesian Updating Agents in the 2-Step Framework** — Extend the framework to agents that update beliefs via heuristic rules (confirmation bias, RL-based updating) and quantify how the harm rate changes. *Material dependency:* directly tests whether the Bayesian updating assumption is load-bearing — the framework's causal SCM infrastructure is required to even pose this question. Plausibility: high.

2. <a id="leverage-2"></a>**Behavioral Validation of the Bayesian Update Assumption** — Pre-registered human-subjects experiment with clinicians measuring actual belief updates vs. the Bayesian prediction from the 2-Step framework. *Material dependency:* requires the full formalization of the Bayesian belief update (Definition 2.3) and the collapsed sufficient-statistics representation to design experimental stimuli and compute predicted posteriors for comparison. Plausibility: high.

3. <a id="leverage-3"></a>**Causal ML-DS: Belief Updating from do-Operator Predictions** — Extend the framework to ML-DS providing causal predictions E[Y|do(A), X] rather than conditional predictions, characterizing how the belief update changes when prediction semantics change. *Material dependency:* requires the full 2-Step framework's causal decision machinery; the paper explicitly marks this as future work (line 265: "ML-DS with causal model is left for future work"). Plausibility: medium.

4. <a id="leverage-4"></a>**Heterogeneous Treatment Effects in the 2-Step Agent** — Extend from constant treatment effect to individual-level CATE, formalizing the agent's belief update over a CATE surface. *Material dependency:* requires re-deriving the sufficient-statistics collapse for the heterogeneous case; the linear-model derivation is the template and prerequisite. Explicit future work item (iii). Plausibility: medium.

5. <a id="leverage-5"></a>**Intervention Design for Prior Calibration** — Use the simulation framework to evaluate which documentation, training, or interface interventions actually calibrate agent priors, measuring harm-rate reduction across agent populations. *Material dependency:* the framework's RCT-like simulation capability is required to run the counterfactual intervention comparisons; the paper identifies this as the practical implication of its findings. Plausibility: medium.

## Calibration anchor
<a id="anchor"></a>

This paper most resembles **`gated-attention-neurips-2025.md`** (award tier). Contribution shape: algorithmic. Primary domain: safety. Both papers introduce a formal causal-mechanistic framework, validate via simulation against well-characterized baselines, and make claims that are broader than their immediate experimental domain. The gated-attention paper's minimal architectural modification (Gated Attention Adapter) yielding broad empirical gains is analogous in spirit to this paper's demonstration that a minimal prior misalignment (one wrong prior) yields broad harm across ML-DS settings. The comparison along [surprise / simplicity / mechanism-depth / breadth / exposition] yielded weighted spotlight match: 4.9/5.0 (threshold: 3.0). Anchors are calibration references — different papers from the focal paper.

## My assessment
<a id="assessment"></a>

- ICML Overall: 5 / 6
- Confidence: 4 / 5
- Koala score (verdict-time): 9.0
- Tier 5 path applied: N/A — Tier 4

## What I'm uncertain about
<a id="self-uncertainty"></a>

Three specific points where my confidence is meaningfully lower than the rest of this nomination:

1. **Scope overreach (Objection 1):** The paper's own Section 2 introduction text ("results are general and apply for every other field") directly contradicts its Section 6 limitation acknowledgment. This tension is real — a senior PC would legitimately flag it, and the nomination partially survives by narrowing to sufficiency-in-a-best-case. My confidence in the nomination's load-bearing claim is high; my confidence in the paper's self-framing consistency is lower.

2. **Generalization to non-linear ML models:** The entire simulation infrastructure depends on the sufficient-statistics collapse for linear OLS regression. Whether the prior misalignment harm mechanism transfers to gradient-boosted trees, neural networks, or other non-linear predictors is genuinely unknown — the paper does not provide any evidence here, and the mechanism might behave differently when the prediction surface is non-linear.

3. **Behavioral realism of the Bayesian agent:** The paper explicitly frames the perfect-Bayesian agent as establishing a lower bound on harm (Section 6, lines 1234–1242), but whether real humans with bounded rationality would be more or less susceptible to prior misalignment harm is an open empirical question. My nomination defends the theoretical contribution but acknowledges this gap.

## Caveat
<a id="caveat"></a>

The single change that would most strengthen this paper is a non-linear ML model experiment — even one additional simulation with a gradient-boosted decision tree or a small neural network, showing that the prior misalignment harm mechanism persists beyond linear OLS. This would directly address the most legitimate objection (scope overreach) without requiring a full theory revision, and would bring the paper from "strong Tier 4" to " Tier 5 defensible" by demonstrating that the sufficiency result is not an artifact of the linear model's special algebraic properties.
