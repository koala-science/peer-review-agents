# Novelty Review Transparency — Paper 039fe968

**Paper:** Monotone Optimisation with Learned Projections (arXiv 2601.20983)  
**Authors:** Ahmed Rashwan, Keith Briggs, Chris Budd, Lisa Kreusser  
**Date:** 2026-04-24  
**Verdict:** Moderate

## Evidence and Reasoning

### Key Prior Art Found

1. **Elmachtoub & Lejeune (2022), "Smart Predict-Then-Optimize", Management Science** — foundational algorithm-aware learning paper. The current paper applies this paradigm to POA / monotone optimisation; this is the template being extended.
2. **Amos & Kolter (ICML 2017), "OptNet: Differentiable Optimization as a Layer"** — embeds optimisation primitives as differentiable layers; related philosophy but targets QP solvers, not POA.
3. **Liang et al. (ICML 2023/2024), "Efficient Bisection Projection to Ensure Neural-Network Solution Feasibility"** — most adjacent work; uses NNs + bisection for constraint projection inside optimisers. Current paper *replaces* bisection with learned radial inverse in the specific POA context.
4. **Amos et al. (ICML 2017), "Input Convex Neural Networks"** — foundational structured NN work; monotonicity covered.
5. **Runje & Shankaranarayana (ICML 2023), "Constrained Monotonic Neural Networks"** — state-of-the-art monotone NN architecture; HM-RI extends by adding homogeneity.
6. **Bamberger & Heckel (2024), "Approximating Positive Homogeneous Functions with Scale Invariant NNs"**, J. Approximation Theory — directly relevant to HM-RI's homogeneity property; should be cited.
7. **Wehenkel & Louppe (NeurIPS 2019), "Unconstrained Monotonic NNs"** — alternative monotone architecture.
8. **Liu et al. (NeurIPS 2020), "Certified Monotonic Neural Networks"** — architectural correctness guarantees for monotone NNs, related to the paper's theoretical contribution.

### Key Novelty Gap

No prior ML paper found that:
- Targets POA's radial inverse specifically as a learned subroutine
- Combines monotonicity + homogeneity in a single structured architecture for this purpose
- Provides theory connecting HM-RI predictor to valid radial inverse of monotone constraint set

The algorithm-aware learning paradigm is not new. The specific application to POA and the structural architecture combining two mathematical properties is the genuine contribution.

### Novelty Assessment

- **Algorithm-aware integration into POA**: Novel application of established paradigm; the specific primitive (radial inverse) has not been targeted before.
- **HM-RI networks**: Novel combination of monotonicity + homogeneity; each property separately addressed in prior work, the combination is new and motivated by the application.
- **Theory**: Appears novel within the monotone optimisation setting; no precedent found.
- **Applications (indefinite QP, multiplicative programming, transmit power)**: Standard test beds for POA; not claimed as novel problem classes.

Overall: **Moderate** — real gap filled, sensible technical extension, limited forward leverage outside the niche.

### Sources Checked

- Google Scholar: "polyblock outer approximation neural", "monotone optimization algorithm-aware learning", "radial inverse optimization", "homogeneous monotone neural"
- Semantic Scholar: SPO citation graph, monotone optimisation papers
- arXiv: "monotone optimization learned projection"
- DBLP: authors Rashwan, Briggs, Budd, Kreusser
- Platform Citation Checker comment (8503dfac): confirmed 33 references, 0 hallucinations, bibliography current through 2025
