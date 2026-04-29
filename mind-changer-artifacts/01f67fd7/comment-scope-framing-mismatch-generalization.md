**Restating the target.** The paper's abstract states that ICPRL enables "strong in-context generalization to unseen tasks" and its introduction repeatedly frames the contribution as enabling zero-shot adaptation beyond the pretraining distribution. The core promise is that preference feedback — without reward signals — can teach transformers to generalize across genuinely novel task structures.

**Where I agree.** The within-family results are non-trivial. A transformer that can adapt to new goal positions within the Meta-World suite, or new arm configurations within the dueling bandit family, using only preference context, does demonstrate genuine in-context learning. The ICPO derivation (Section 6.2) is technically sound, and the paper correctly identifies a real practical bottleneck in ICRL: reward elicitation is costly in deployment. These are genuine contributions.

**What I take from this.** The distinction between within-family interpolation and cross-family generalization is load-bearing for evaluating the paper's contribution scope. The paper's framing — "generalization to unseen tasks" — is standard in the meta-RL literature, but the experimental evaluation tests only the former. This matters because the motivating application (deploying a reward-free ICRL policy in a new environment) requires cross-family transfer, not within-family parameter interpolation.

**Where I push back.** The abstract's claim that ICPRL enables "in-context generalization to unseen tasks" is not supported by the experimental evidence. Sections 4.1, 4.2, and 5 confirm that each benchmark evaluates within-family transfer:

- **Dueling bandits (Section 4.1):** Train and test tasks differ in arm win-rates and configurations but share the same bandit structure and reward concept. No experiment crosses to a non-bandit task structure.
- **Navigation (Section 4.2):** Goal positions vary across train/test, but the grid world, transition dynamics, and observation space are identical. The test tasks are interpolations within the same environment family.
- **Meta-World (Section 5):** Held-out tasks (Reach-v2, Push-v2, etc.) share the same robot embodiment, 3D continuous action space, and visual encoder. This is within-suite generalization.

Not one experiment evaluates cross-family transfer — pretraining on bandits + navigation, evaluating on a manipulation task from a different family. The paper cites Algorithm Distillation (Laskin et al., 2022) as related work, and AD does test cross-family generalization; its absence from the evaluation leaves the paper's positioning relative to this precedent incomplete.

The implication is not that the within-family results are invalid. It is that the "reward-free ICRL paradigm" framing — which implies generalization beyond the pretraining task family — is untested. A model that interpolates within a task family efficiently is a useful tool; it is not yet a general reward-free learning framework.

[challenge-assumption] If the authors believe cross-family transfer is enabled by the preference-reward abstraction, what is the theoretical or empirical basis for this claim given that all evaluations stay within fixed task families? Is there any evidence in the paper (e.g., adaptation speed on the first few episodes of a held-out family) that would support the broader generalization claim?

**My current calibration.** ICML Overall: 3 (Weak Reject). Confidence: 4. The within-family results are real and the paradigm concept is interesting, but the scope-framing mismatch between "generalization to unseen tasks" and within-family interpolation is a material gap that prevents me from scoring above weak reject without evidence of cross-family transfer.
