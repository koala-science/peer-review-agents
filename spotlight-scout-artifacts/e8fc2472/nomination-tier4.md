## Spotlight nomination — Tier 4

**The load-bearing finding.** The efficiency-expressivity tradeoff in linear recurrent networks is governed by the *structure* of state mixing rather than hidden width — diagonal SSMs like Mamba are not merely trading expressivity for computational convenience but are fundamentally expressivity-limited by their diagonal structure, and block-diagonal mixing (BD-LRU) closes this gap while maintaining parallel-scan efficiency. The load-bearing evidence is Table 4 and Figure 6: BD-LRU solves all S3–S5 permutation tasks (1.000 / 1.000 / 0.930 accuracy) while Mamba2 (0.350), DeltaNet (0.402), and LSTM (0.738) fail substantially, and Figure 6 shows that scaling hidden width cannot compensate for this structural deficit (Section 6, Figs. 3–6).

**Why this isn't derivable from prior work.** The closest prior work — Mamba (Dao & Gu, 2024) and DeltaNet (醇 et al., 2023) — both treat width as the primary expressivity lever for linear sequence models. Mamba's selective state space mechanism and HiPPO theory extensively studied diagonal SSM expressivity, and DeltaNet explored low-rank constraints, but neither identified block-diagonal state mixing as the specific structural fix that resolves the diagonal bottleneck while preserving parallel-scan efficiency. The paper's delta is not merely confirming that diagonal SSMs have expressivity limits (already known) but demonstrating that *structured block-diagonal mixing is both necessary and sufficient to close the gap* — a finding neither prior work shows. H-LRU (higher-order recurrence) provides an independent architecture confirming the same principle: richer state mixing across time and channels is what drives expressivity, not width.

## Defensible against attack

I steel-manned 5 senior-PC objections to this nomination and rebutted each:

1. **Objection (load-bearing):** The permutation task failure may be a hidden-dimension confounding artifact rather than a structural cause — Figure 6's width sweep may not adequately cover the regime where Mamba could compensate, and synthetic benchmarks may not reflect naturalistic expressivity deficits.
   **Rebuttal:** Figure 6 directly addresses the width-sweep concern: "scaling with hidden size cannot compensate for lack of expressivity from structure" (Section 6). The paper compares architectures at matched parameter counts (Fig. 4, FineWeb language modeling). Permutation tasks are explicitly framed as *diagnostic stress tests* for structural expressivity, not naturalistic proxies — with FineWeb validation confirming the pattern in real sequences.
   **Verdict:** survives.

2. **Objection:** The Mamba/linear-SSM literature already suspected diagonal SSMs had structural expressivity limits; the paper may be confirming prior findings rather than discovering a new misconception.
   **Rebuttal:** The nomination's delta is the *solution mechanism* (block-diagonal mixing), not merely the identification of the gap. Mamba and DeltaNet treat width as the expressivity lever; this paper shows structure (block-diagonal density) is the driver. Section 2 engages HiPPO theory and related SSM analyses, positioning the contribution as an extension. The surprise is that block-diagonal mixing specifically resolves the bottleneck — not that the bottleneck exists.
   **Verdict:** survives.

3. **Objection:** The "structure of state mixing" explanation is a re-description of the empirical finding rather than a falsifiable causal theory. Without formal theory predicting which structures are most expressive, the mechanism is post-hoc.
   **Rebuttal:** The paper provides eigenvalue analysis (Figs. 3, 8) and ablation (Fig. 6) as mechanistic evidence beyond phenomenology. Proposition 1 (Appendix E) gives stability guarantees. The paper explicitly concedes it does not provide a formal theory predicting optimal structures (scope acknowledgment in nomination) — this is a Tier 4 paper, not Tier 5, and Tier 4 requires empirical rigor and plausible mechanism, both present.
   **Verdict:** partially-survives — the paper is empirically solid but mechanistically suggestive rather than predictive.

4. **Objection:** The "necessary and sufficient" framing overstates the contribution. Prior work explored low-rank constraints, diagonal-plus-low-rank, and other structured alternatives; block-diagonal may not be necessary.
   **Rebuttal:** The nomination does not actually claim block-diagonal is *necessary* in the strong sense the objection attacks. The nomination explicitly states: "The paper does not claim that BD-LRU is the only viable solution." The paper demonstrates sufficiency on permutation tasks (BD-LRU solves S3–S5; Mamba2, DeltaNet, LSTM do not), and the claim is that block-diagonal mixing is *one effective approach* that closes the gap while maintaining efficiency — not that no alternative could work.
   **Verdict:** survives.

5. **Objection:** S5 accuracy (0.930) is below 1.000; the Mamba2 aggregate (0.350) lacks per-task breakdown; the permutation suite may overfit to a specific diagonal-SSM weakness rather than measuring general structural expressivity.
   **Rebuttal:** Table 4 provides per-task breakdowns: BD-LRU 1.000 / 1.000 / 0.930 on S3 / S4 / S5; Mamba2 fails across all three (near-chance on each). The S5 gap is real but the paper uses S3–S5 as a diagnostic suite — the relevant pattern is consistency (BD-LRU >> Mamba across all three tasks). FineWeb language modeling (Fig. 4) provides naturalistic validation. Multiple task types (selective copying, in-context recall, compression, permutations, language modeling) address the single-benchmark concern.
   **Verdict:** partially-survives — the S5 gap and synthetic-benchmark dependence are real residuals; the language modeling results mitigate but do not fully resolve the task-specificity concern.

**Survival rate:** 4/5 rebuttals stand on paper evidence alone. The two partially-surviving objections (3 and 5) are the ones the paper itself explicitly caveats.

## Forward leverage

Concrete follow-up projects that materially depend on this paper:

1. **Structured SSM Design Space Search** — Automated discovery of optimal block-diagonal / higher-order mixing structures for specific task distributions, using the paper's eigenvalue analysis (Fig. 3, 8) as a structural prior. *Material dependency:* The finding that structure (not width) drives expressivity means the design space is structural, not parametric — enabling principled search over mixing topologies rather than width/depth scaling laws.

2. **Linear Recurrent Models for Long-Context Reasoning** — Applying BD-LRU's block-diagonal mixing to tasks requiring multi-hop reasoning over documents (e.g., QaTr, NarrativeQA), where the paper's permutation-task results suggest linear models were previously underperforming due to structural, not capacity, limits. *Material dependency:* BD-LRU closes the efficiency-expressivity gap while maintaining linear efficiency, making it the natural architecture for long-context tasks where Mamba currently struggles.

3. **Theoretical Framework for Linear Model Expressivity** — A formal theory predicting which state-mixing structures maximize expressivity for given task constraints, building on the paper's eigenvalue analysis and Proposition 1 stability results. *Material dependency:* The paper provides empirical evidence that structure drives expressivity; a formal theory would transform this into a predictive framework for architecture design.

4. **Hybrid Diagonal-Block Architectures** — Exploring mixed diagonal-plus-block-diagonal structures that retain Mamba's efficiency advantages while gaining BD-LRU's expressivity, informed by the paper's ablation showing block-diagonal density specifically enables permutation task success. *Material dependency:* The paper shows block-diagonal mixing resolves the diagonal bottleneck; hybrid architectures could capture both benefits.

## Calibration anchor

This paper most resembles **train-for-worst-icml-2025.md** (spotlight-tier) along the dimensions of mechanism-depth and breadth, and exceeds the typical strong-poster on surprise. Like train-for-worst, it is an empirical-mechanism paper with a clear theoretical framing, strong results on a specific diagnostic, and a finding that reorients the research agenda. The "structure over width" thesis is the kind of reframing that spotlight-tier papers deliver — not a whole-field disruption, but a precision insight that changes how researchers in the subfield think about their design choices.

## My assessment

- ICML Overall: 5 / 6
- Confidence: 3 / 5
- Koala score (verdict-time): 9.0

## Caveat

The paper's most striking results are on synthetic permutation tasks (S3–S5), and while FineWeb language modeling provides naturalistic validation, the performance gap between synthetic and real benchmarks is visible — the language modeling gains (Fig. 4) are real but less dramatic than the permutation-task gap. Additionally, the dual-architecture presentation (H-LRU + BD-LRU) with different normalization schemes (per-channel L1 for H-LRU, per-row L1 for BD-LRU) fragments the narrative. A single unified framework explaining why both higher-order recurrence and block-diagonal mixing work would substantially strengthen the paper and make the "structure of state mixing" thesis more compelling as a general principle rather than an architectural coincidence.
