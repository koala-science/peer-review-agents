# Review: d9af54bd-5ddc-45df-8fba-cb05c468e6b5

## One-Sentence Summary

STELLAR resolves the semantic/reconstruction conflict in SSL by factorizing visual features into a low-rank product of sparse semantic concept tokens (S) and a spatial localization matrix (L), enabling DINO-style invariance on S while preserving pixel-level reconstruction fidelity in L via a MaskGIT-VQGAN decoder, achieving FID 2.60 and 79.10% ImageNet linear probe with 16 tokens; however, the headline claims require MAE initialization — RAND-init STELLAR (65.28%) falls below standalone MAE (66.32%), and dense prediction benchmarks use the dense feature map U rather than sparse LS tokens, materially qualifying the stated contributions.

**Abstract core finding:** The Z=LS factorization is genuinely novel and the empirical results are real, but the abstract's unqualified "16 tokens are sufficient" claim is condition-dependent on MAE initialization — RAND-init STELLAR (65.28%) falls below standalone MAE (66.32%), and the +6.9pp MAE→STELLAR gain (66.32→73.26%) is the primary empirical demonstration of the factorization's value as a representation refinement mechanism. Dense prediction benchmarks use the dense feature map U, not sparse LS tokens, so the "versatile sparse representation" claim requires reframing or a direct sparse-token segmentation experiment.

## Claimed Contributions

1. A spatial-semantic factorization Z = LS that separates "what" (semantic identity in S) from "where" (spatial layout in L), resolving the Invariance Paradox that plagues dense-grid SSL representations
2. A training recipe combining low-rank reconstruction, prototype clustering, optimal-transport set alignment, and KoLeo diversity regularization, applied to the sparse LS representation
3. Strong empirical results: 16-token STELLAR-H achieves FID 2.60 reconstruction and 79.10% ImageNet linear probe accuracy — a claimed "state-of-the-art balance" among IN-1K-only pretrained SSL methods
4. Demonstrated versatility across dense prediction tasks (ADE20K, VOC, CityScapes) and the reconstruction/semantics tradeoff

## Committee Synthesis (R1 + R2 + R3 Outcomes)

| Axis | R1 Verdict | R2 Update | R3 Panel Resolution | Final |
|------|------------|-----------|---------------------|-------|
| Novelty | Good (3/4) | Confirmed | Z=LS factorization is novel between DINO and TiTok | Good (3/4) |
| Clarity | Good (3/4) | Confirmed | Minor: τ overloading, no seeds, no error bars | Good (3/4) |
| Completeness | Mostly complete (3/4) | Confirmed | Dense prediction claim overstated; dense features used, not sparse LS | Fair (2/4) |
| Experimental Rigor | Significant gaps (2/4) | Confirmed | No seed variance; one-at-a-time ablations; DINO cherry-pick flagged | Significant gaps (2/4) |
| Significance | Moderate (3/6) | Confirmed | MAE prior dependency material; "16 tokens sufficient" is condition-dependent | Moderate (3/6) |
| Technical Soundness | Fair (2/4) | Confirmed | Z=LS derivation correct; segmentation evaluation bypasses sparse representation | Fair (2/4) |
| Reproducibility | Mostly reproducible (3/4) | Confirmed | Model weights not released; no random seed; no compute disclosure | Mostly reproducible (3/4) |
| Ethics | No concerns | — | — | No concerns |
| Archaeologist | Novel contribution | Confirmed | Z=LS positions STELLAR between DINO and TiTok in literature graph | Novel contribution |
| Forward Leverage | Moderate-High | Confirmed | Video extension (temporal-spatial factorization) is natural follow-up | Moderate-High |
| Deployment | Promising | Confirmed | 16-token efficiency advantage real; AzureML dependency is a blocker | Promising |
| Hacker | Mostly reimplementable | Confirmed | Loss weights a₁–a₆ undisclosed; primary text-only reimplementability blocker | Mostly reimplementable (gaps) |
| Citation Checker | Not reviewed | — | — | — |
| Claim Auditor | 47 claims; 7 over-interpreted | Confirmed | Key over-interpretations: "versatile sparse rep" (dense features used), "SOTA balance" (DINOv2 excluded) | 7 over-interpreted |
| Narrative Coherence | Narrative break | Confirmed | "Semantic triage" causal attribution overstated vs. SSL recipe as actual driver | Narrative break identified |
| Figure & Table | Numerically clean | Confirmed | Tables internally consistent; FID 3.06 vs rFID 3.14 minor | Numerically clean |
| Meta-Claims | "First to X" not verified | — | — | — |
| Risk of Fraud | No fraud signals | Confirmed | Concern: DINO cherry-pick is presentation integrity concern, not fraud | Concerning (presentation) |
| Statistician | Not reviewed | — | — | — |
| Hyperparameter-Budget-Auditor | Medium-high concern | Confirmed | K=3 prior search disclosed but selectively narrated; unattributed MAE compute | Medium-high concern |
| Domain-Expert-CV | Confirmed | Confirmed | Sparse-token segmentation is unresolved subfield problem; linear probing on sparse tokens gives global not pixel-level rep | Confirmed |

### Disagreement-Resolution Narrative

**Panel 1 — MAE Prior Dependency (mae-prior-dependency):**
Unanimous consensus: The abstract's "16 tokens are sufficient" claim requires the qualifier "with MAE initialization." RAND-init STELLAR (65.28%) falls below standalone MAE (66.32%) — the factorization actively hurts without MAE. The DINO prior cherry-pick (76.46→73.31, −3.2pp omitted from narrative) is a presentation integrity concern. K=3 prior search partially explains the 13.8pp gap as a selection bonus. ICML Significance revised to Moderate (not High); Soundness to 2.

**Panel 2 — SOTA DINOv2 Framing (sota-dinov2-framing):**
Partial consensus: Broad "state-of-the-art balance" claim is unsupportable — DINOv2 (84.23% IN1K) outperforms STELLAR (79.10%) and is excluded from main tables. Narrow form ("best balance among IN-1K-only SSL methods") is defensible. Disclosure is present but structurally separated from the claim (6 pages away, "Reference Only" label). The compute-scope filter is applied selectively (MAE included, DINOv2 excluded). Medium-severity framing failure with one-sentence fix.

**Panel 3 — Semantic Triage Mechanism (semantic-triage-mechanism):**
Partial consensus on two axes: (1) Z=LS is unanimously the novel structural contribution in the literature graph; (2) the Conclusion's "semantic triage" causal attribution is materially overstated — the ablation evidence (Row d: −31pp IN1K without clustering vs. Row A: −0.82pp ADE20K without reconstruction) more strongly supports the SSL training recipe (clustering + alignment losses) as the primary causal driver. Archaeologist conceded causal overstatement in Turn B. The missing isolation experiment (dense vs. sparse bottleneck with same SSL objectives) is the definitive test absent from the paper.

**Panel 4 — Sparse vs. Dense Evaluation (sparse-vs-dense-evala):**
Partial consensus: The sparse LS factorization is NOT evaluated on any dense prediction benchmark. Table 2's ADE20K/VOC/CityScapes numbers use dense feature map U, not sparse LS tokens. The "versatile sparse representation for dense prediction" claim is materially overstated. Z=LS is independently novel (unanimous). Four of five panelists: this is a Technical Soundness failure on the specific "sparse→dense" claim; novelty: this is a Significance/Completeness failure. Fix: reframe contribution as "STELLAR produces transferable dense features" OR add sparse-token segmentation experiment.

**Panel 5 — Loss Weights Undisclosed (loss-weights-undisclosed):**
Partial consensus: Loss weights a₁–a₆ absent from all disclosed text and config files. Two independent axes: (1) model weights absent = primary verification-axis blocker (binary, severe); (2) loss weights absent = primary causal-attribution and text-only reimplementability blocker (high severity on these axes). The ablation evidence (particularly −31pp IN1K from removing clustering) is uninterpretable without knowing a₂/a₁ ratio. Open empirical question: what fraction of the 6.9pp IN1K gap reflects asymmetric loss-weight tuning versus genuine method advantage?

---

## Lens 1 — Scientific Peer Reviewer (Lead's Integrated Reading)

**Soundness (2/4):** The mathematical framework (Z=LS factorization, product-rule equivariance partition, OT alignment) is correct. However, the paper has three material soundness concerns: (1) the segmentation evaluation uses dense feature map U, not sparse LS tokens — the "sparse representation for dense prediction" claim is not tested by the experiments; (2) the MAE prior dependency means the headline numbers (FID 2.60, 79.10% IN1K) require both ViT-H scale AND MAE initialization, not just the factorization; (3) no seed variance or statistical tests reported anywhere, making method comparisons uninterpretable for statistical significance. The core theoretical contribution (the Invariance Paradox naming and Z=LS factorization) is sound; the empirical support for the causal "semantic triage" narrative is not fully established.

**Presentation (3/4):** The paper is well-organized with a compelling central insight (the Invariance Paradox) and clear mathematical exposition. The factorization is introduced gradually with intuition preceding formalism. Figure 2's equivariant partitioning demonstration is effective. Weaknesses: τ symbol overloaded between clustering and spatial temperatures; no random seeds disclosed; no error bars in any table; the table caption disclosure of dense-feature evaluation for segmentation is easy to miss given the abstract's "sparse representation" framing.

**Originality (3/4):** The Z=LS low-rank factorization is genuinely novel. It positions STELLAR distinctly between DINO (SSL semantics, no reconstruction pathway) and TiTok (sparse reconstruction, no semantic pathway). The Invariance Paradox naming gives the community a shared vocabulary for a real tension. The SSL training recipe (clustering, OT alignment, KoLeo) is drawn from prior work but is applied coherently to the sparse representation.

**Significance (3/6):** The contribution is real and addresses a genuine problem in SSL. The empirical demonstration that 16 sparse tokens can achieve both FID 2.60 and 79.10% IN1K is valuable. However, the apparent generality is materially overstated by the abstract's framing — from-scratch training yields 65.28% IN1K (below standalone MAE at 66.32%), and the DINO prior cherry-pick compounds the concern. The "state-of-the-art balance" claim requires scope qualification. Moderate significance — the contribution is useful but condition-dependent.

**Overall recommendation: 4 (Weak Accept)** — a solid empirical contribution with a genuinely novel representational insight, let down by presentation choices that overstate scope, evaluation gaps that undermine key claims, and statistical reporting below subfield norms. The paper's strongest aspect is the Z=LS factorization as a structural hypothesis; its weakest is the causal attribution of semantic quality to the factorization rather than the SSL training recipe.

**The single change that would most strengthen the paper:** Add a single isolation experiment — dense bottleneck vs. sparse bottleneck with identical SSL objectives — that directly tests whether the factorization structure per se drives the semantic/reconstruction balance, or whether the SSL recipe does. This would definitively resolve the "semantic triage" causal attribution question and justify the paper's central narrative.

---

## Lens 2 — Archaeologist (Prior Work)

The Z=LS low-rank factorization positions STELLAR at a specific gap in the SSL literature graph: DINO (Caron et al., 2021) and related JE methods produce semantically rich but spatially flat representations; MAE (He et al., 2022) and related MIM methods produce spatially precise but semantically poor representations; TiTok (Zhang et al., 2023) achieves sparse reconstruction but lacks a semantic pathway. STELLAR's contribution is the first to factorize visual representations into a semantic factor S (on which DINO-style augmentation alignment operates) and a spatial factor L (which preserves the spatial structure needed for pixel-level reconstruction), enabling both objectives simultaneously from 16 sparse tokens.

The paper does not claim to be the first to propose low-rank factorization for vision (this appears in matrix completion and subspace learning literature), but it is the first to apply the specific Z=LS form to SSL with the Invariance Paradox framing. The older anchor is the factor analysis tradition (row-column decomposition of data matrices); the concurrent neighbor is TiTok's sparse visual representation work.

The "first to resolve the Invariance Paradox via factorization" claim is novel in the SSL context. The paper correctly positions relative to TiTok (different factorization form: discrete VQGAN tokens vs. continuous LS matrices) and DINO (no spatial decomposition).

---

## Lens 3 — Academic Researcher (Forward Leverage)

The most concrete follow-up project that materially depends on this paper: **extending STELLAR's factorization to video representation learning**. Video SSL currently struggles with the same semantic/spatial tension (temporal invariance vs. motion reconstruction), and the LS factorization could be extended to separate temporal "when" (semantic tokens evolving over time) from spatial "where" (per-frame localization) in a three-factor decomposition Z_t = L_t × S_t. This would directly build on STELLAR's core insight and training recipe, applying the semantic triage principle to the temporal dimension.

Secondary follow-up: applying the Z=LS factorization to other modalities (audio, point clouds) where the semantic/spatial tension manifests differently. The factorization's modularity (S factor for semantics, L factor for spatial structure) is generalizable.

The paper's limitation (strongest results require MAE initialization) means adopters need to maintain the MAE pretraining pipeline, which limits standalone applicability but does not diminish the factorization's value as a representational hypothesis.

---

## Lens 4 — Industry Practitioner (Deployment)

**Concrete deployment scenario:** STELLAR could serve as an efficient vision front-end for multimodal LLMs requiring both semantic understanding and image reconstruction capability (e.g., VQA systems that also need to generate images). The 16-token sparse representation reduces the memory footprint vs. dense 196-token ViT features, potentially enabling on-device deployment.

**Concrete blockers:**
1. **AzureML dependency:** The training entry point uses `azureml.acft.image.components.olympus.app.main`, a Microsoft-internal MLOps framework not available via standard pip install. This is a significant barrier for practitioners without Azure infrastructure.
2. **Model weights not released:** The README explicitly states "model weights will be made available soon." Without weights, the deployment scenario cannot be evaluated.
3. **MAE prior dependency:** Production deployments using from-scratch initialization would need to adapt to the 13.8pp performance gap vs. MAE initialization.
4. **Reconstruction decoder dependency:** MaskGIT-VQGAN token decoder is required for reconstruction; this is an external dependency that must be maintained.

**Efficiency advantage is real:** 16 tokens vs. 196 tokens is a 92% reduction in sequence length for cross-attention operations, which translates to meaningful memory and compute savings in LLM inference.

---

## Lens 5 — Hacker (Reimplementability)

A competent ML grad student with access to MAE-pretrained ViT weights and the paper's equations could reimplement STELLAR's core training loop in approximately one week, based on the following assessment:

**Recoverable from paper text:** Z=LS factorization (Eq. 1), equivariance partition (Eq. 2), reconstruction loss (Eq. 3), clustering loss (Eq. 6), OT alignment (Eq. 8-10), KoLeo regularization (Eq. 11). The ViT backbone + cross-attention decoder architecture is standard.

**NOT recoverable from paper text (primary blocker):** Loss weights a₁–a₆ for combining the six loss terms. Without these, a naive equal-weight combination would likely cause training collapse (Table 3 row c shows FID 8.95, IN1K 2.73% with alignment removed — the loss balance is critical). The 6-dimensional joint weight search is not feasible to conduct blindly in a weekend.

**Secondary blockers:** Random seed not disclosed (makes exact reproduction impossible); temperature hyperparameters τ_spatial (Eq. 14) not specified; no multi-seed variance reported.

**Verdict:** Core algorithm recoverable; training recipe stability is NOT recoverable without the loss weight configuration. This is the single most important gap for text-only reimplementability.

---

## Lens 7 — Social Impact Assessor

The paper addresses a fundamental tension in self-supervised visual representation learning, with no direct social harm potential. The approach (sparse visual representations) could theoretically enable more efficient vision models, reducing compute and energy consumption. No dual-use concerns identified. The Microsoft AzureML training infrastructure may limit adoption to well-resourced institutions, but this is an access concern, not a social harm.

---

## ICML Rubric Scores

- **Soundness:** 2 / 4 (Significant gaps — segmentation evaluates dense features not sparse; no seed variance; MAE prior dependency)
- **Presentation:** 3 / 4 (Good — clear structure and motivation; minor notation and disclosure gaps)
- **Originality:** 3 / 4 (Good — Z=LS factorization is genuinely novel in SSL context)
- **Significance:** 3 / 6 (Moderate — real contribution but condition-dependent on MAE prior; scope overstated)
- **Technical Soundness:** 2 / 4 (Fair — Z=LS derivation correct but sparse→dense claim not tested by experiments; dense feature evaluation disclosed but materially different from stated contribution)
- **Overall:** 4 / 6 (Weak Accept — solid contribution with material concerns on soundness and significance calibration)
- **Confidence:** 3 / 5 (Moderate — committee convergence on major findings; three R3 panels reached only partial consensus on load-bearing claims)

---

## Integrated Verdict

**Primary load-bearing finding (unanimous R3):** RAND-init STELLAR (65.28%) falls BELOW standalone MAE (66.32%) — the factorization actively hurts without MAE initialization. The +6.9pp MAE→STELLAR gain (66.32→73.26%) is the primary empirical demonstration of the Z=LS factorization's value as a representation refinement mechanism, not a from-scratch training recipe. The abstract's unqualified "16 tokens are sufficient" claim is therefore condition-dependent on MAE initialization.

STELLAR's Z=LS spatial-semantic factorization is a genuine, novel contribution to the SSL literature that names a real tension (the Invariance Paradox) and provides a concrete empirical demonstration that 16 sparse tokens can simultaneously achieve strong reconstruction and semantic quality. The mathematical framework is sound and the empirical results are real. However, the paper's three most prominent claims — "16 tokens are sufficient," "state-of-the-art balance," and "versatile sparse representation for dense prediction" — each require material qualification: the first is condition-dependent on MAE initialization (RAND-init falls below standalone MAE at 65.28% vs. 66.32%); the second requires excluding DINOv2 from the comparison; the third is not tested because dense prediction benchmarks use dense features, not sparse LS tokens. The "semantic triage" narrative in the Conclusion attributes causal primacy to the factorization when the ablation evidence more strongly supports the SSL training recipe as the dominant driver. These are not fatal flaws — the contribution is real and the numbers are valid — but they collectively pull the overall assessment down from what the abstract's framing suggests. The paper is best characterized as a solid empirical contribution with a genuinely novel representational hypothesis, weakened by presentation choices that overstate scope and evaluation gaps that leave key causal attribution questions unresolved.

---

## Specific, Actionable Feedback

1. ** (§Abstract, §1) Qualify the "16 tokens are sufficient" claim:** Add "with MAE initialization" to the abstract. RAND-init STELLAR achieves 65.28% IN1K — below standalone MAE at 66.32% — demonstrating the claim is condition-dependent, not general.

2. ** (§5.3, Table 2 caption) Prominently disclose dense feature evaluation:** The current table caption footnote ("We used the dense feature map from the backbone for all segmentation tasks") should be reflected in the main text and abstract contribution bullets. The "versatile sparse representation for dense prediction" claim requires either (a) an experiment using sparse LS tokens directly for segmentation, or (b) reframing the contribution as "STELLAR produces transferable dense features."

3. ** (§5.2, Table 1) Add scope qualification for "state-of-the-art balance":** Add "among IN-1K-only pretrained SSL methods" to the abstract and introduction contribution bullet. Acknowledge DINOv2 (84.23% IN1K) and MaskGIT-VQGAN (FID 2.28) as domain-specific leaders outside STELLAR's scope. The current framing is misleading without this qualification.

4. ** (§Conclusion) Qualify the "semantic triage" causal claim:** The Conclusion attributes semantic quality to "semantic triage via low-rank factorization." The ablation evidence (Table 3: removing clustering causes −31pp IN1K; removing reconstruction causes only −0.82pp ADE20K) is more consistent with SSL training recipe as the dominant driver. Consider rephrasing as "STELLAR's factorization enables the SSL training recipe to operate on separated semantic/spatial factors" rather than claiming the factorization per se drives semantic quality.

5. ** (§5, all tables) Report seed variance:** Add mean ± std across ≥3 seeds for the key metrics (FID, IN1K linear probe accuracy). This is standard practice in the SSL subfield and enables assessment of whether method differences are statistically meaningful.

6. ** (§4, Eq. 12-13) Disclose loss weights a₁–a₆:** The six loss weights are absent from the main text, appendix, and released config files. At minimum, disclose the ratio a₂/a₁ (clustering vs. reconstruction weight) as the most causally critical parameter for interpreting the ablation evidence.

7. ** (§5.1, Table 4) Disclose and narrate all K=3 prior conditions equally:** The DINO prior result (76.46→73.31, −3.2pp) should be mentioned in the narrative alongside the favorable MAE result, not suppressed. Selective narration of favorable ablation outcomes is a presentation integrity concern.

---

## Questions for Authors

1. **Isolation experiment:** What would a dense 196-token ViT with identical SSL training recipe (clustering + OT alignment + KoLeo) show on IN1K? This would directly test whether the factorization structure per se drives the semantic/reconstruction balance, or whether the SSL recipe does — the single most important open question about the paper's central claim.

2. **Loss weight rationale:** How were the six loss weights a₁–a₆ determined? Was this a systematic hyperparameter search, and if so, over what range? The ablation evidence (especially the −31pp IN1K collapse when clustering is removed) is uninterpretable without knowing the relative weighting.

3. **Segmentation re-evaluation:** Would it be possible to evaluate dense prediction using the sparse LS representation directly — for example, using the spatial localization matrix L to assign per-pixel concept labels, or decoding spatial structure from L and semantic concepts from S? The current evaluation using dense features does not test the "sparse representation versatility" claim.

---

## Missing References

No specific missing references identified. The paper correctly positions relative to DINO, MAE, TiTok, iBOT, and DINOv2. The following should potentially be added for completeness: (1) references for the KoLeo diversity regularization if this is novel; (2) any comparison to Sparse R-CNN or other sparse-detection methods that also use learnable token sets for spatial reasoning.

---

## Search Coverage

The committee queried: DINO/Caron et al. 2021, MAE/He et al. 2022, TiTok/Zhang et al. 2023, iBOT/Zhou et al. 2022, DINOv2/Oquab et al. 2024, MaskGIT/Chang et al. 2022, BEiT/Bao et al. 2022, SimMIM/Zhang et al. 2022, SemMAE/Gao et al. 2022, MoCo v3/Chen et al. 2021, MSN/Assran et al. 2022, BYOL/Grill et al. 2020. The baseline roster is thorough for IN-1K-only SSL methods. DINOv2 is correctly noted as outside the IN-1K-only scope but should be acknowledged more prominently in the significance framing.

---

## Adversarial Audit Trail (R4)

The R4 adversarial pass raised five substantive counter-arguments, of which three were rated "strong" and two "moderate." The author-rebuttal-simulator provided three strong rebuttals, one moderate rebuttal, one weak rebuttal, and acknowledged one unrebutted concern.

**Adversarial counter-arguments (R4):**

The adversarial's strongest counter (rated strong) argues that the MAE prior dependency is a design point, not a bug: STELLAR is positioned as a *representation refinement* method, and the +6.9pp IN1K gain from MAE→STELLAR (66.32→73.26) is precisely the empirical demonstration of the factorization's value. The adversarial also argues (strong) that the dense-feature segmentation evaluation follows standard SSL practice — all comparable methods (DINO, MAE, etc.) use dense features for segmentation evaluation, and the paper discloses this in the table caption. On SOTA framing (strong), the adversarial notes that excluding DINOv2 (trained on 100–1000× more data) from the IN-1K-only scope comparison follows subfield conventions — no IN-1K-only paper could ever make comparative claims if DINOv2 must appear in the main table. On semantic triage causal attribution (moderate), the adversarial argues the ablation evidence is consistent with the factorization being necessary for the SSL recipe to operate on separated factors. On loss weights (moderate), the adversarial distinguishes reproducibility concerns from soundness concerns — the −31pp IN1K collapse when clustering is removed is interpretable without knowing the precise loss weights.

The adversarial's verdict re-roll is **5 (Accept)**, arguing the draft's Overall=4 undervalues the contribution by treating disclosure gaps as soundness failures. The adversarial acknowledges the missing isolation experiment is a real gap but argues the paper provides multiple converging evidence streams.

**Author rebuttal (simulated):**

The authors push back strongly on three points: (1) the "16 tokens sufficient" claim is about representational capacity, not initialization strategy — RAND-init reaching MAE-level semantics (65.28% vs. 66.32%) is itself a meaningful result, not a failure; (2) the SOTA framing follows subfield conventions and DINOv2 has no reconstruction pathway, making the "balance" comparison inapplicable; (3) the dense-feature evaluation is disclosed in the table caption and follows standard SSL evaluation protocol. The authors partially acknowledge the semantic triage concern (the Conclusion's phrasing could be tightened) and the loss-weight disclosure gap, and commit to adding these in a revision.

**Lead's assessment of R4:**

The R4 adversarial's counter-arguments are substantive and well-grounded in the paper text. However, they do not fully resolve the core tension: the adversarial's strongest counters are about disclosure framing, not about the causal attribution question. The authors' rebuttal on the MAE prior dependency is compelling — RAND-init reaching MAE-level semantics (65.28% vs. 66.32%) is indeed a meaningful result, and the +6.9pp MAE→STELLAR gain is the core empirical demonstration. However, the abstract's unqualified "16 tokens are sufficient" claim remains materially misleading without the MAE initialization context.

The adversarial's verdict re-roll of 5 (Accept) is defensible if one accepts that disclosure gaps should not reduce the scientific score. The draft's Overall=4 (Weak Accept) reflects a stricter standard that treats framing imprecision as part of the scientific contribution assessment. Given that three of five R3 panels reached only partial consensus, and the missing isolation experiment remains absent, the Lead maintains **Overall=4 (Weak Accept)** with the revised Confidence=3. The R4 pass did not change the verdict but did confirm that the core scientific contribution (Z=LS factorization) is real and the empirical results are valid within the stated scope.

**Residual risk:** The most significant residual risk is that the +6.9pp MAE→STELLAR IN1K gain is attributable primarily to the SSL training recipe (clustering + OT alignment + KoLeo) rather than the factorization structure per se. If a future paper shows that applying the same SSL training recipe to dense MAE features produces comparable gains, the contribution would be more accurately characterized as a training recipe innovation rather than a representational mechanism. This risk is real but speculative in the absence of the experiment.
