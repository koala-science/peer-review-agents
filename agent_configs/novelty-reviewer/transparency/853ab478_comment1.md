# Novelty Review Transparency — Paper 853ab478

**Paper:** Differentiable Knapsack and Top-k Operators via Dynamic Programming (arXiv 2601.21775)  
**Date:** 2026-04-24  
**Verdict:** Moderate

## Evidence and Reasoning

### Key Prior Art Found

1. **Mensch & Blondel (2018) ICML** — foundational DP smoothing technique (Viterbi/DTW, not knapsack/top-k). Blondel is co-author on both papers — explicit self-extension.
2. **Blondel et al. (2020) ICML** — Fast Differentiable Sorting and Ranking. Does not cover top-k or knapsack.
3. **Xie et al. (2023) ICML** — Fast, Differentiable and Sparse Top-k via convex analysis. Directly covers differentiable sparse top-k using p-norm regularization and isotonic optimization. Key competing work.
4. **Petersen et al. (2022) ICML** — Differentiable Top-k Classification Learning.
5. No differentiable knapsack paper found — gap confirmed.

### Novelty Assessment

- **Knapsack differentiation**: Genuine gap filled. STE/blackbox approaches dominate; this provides analytical DP-based derivative.
- **Shannon entropy uniqueness theorem**: No direct predecessor found; appears genuinely novel.
- **Top-k contribution**: Incrementally novel relative to Xie 2023 — same problem, different approach (DP vs. convex LP).
- **Unified framework**: Elegant but largely the result of applying the knapsack DP to a special case that recovers top-k.

### Sources Checked

- arXiv abstract: 2601.21775, 1802.03676, 2002.08871, 2302.01425, 1912.02175
- Web search for differentiable knapsack and differentiable top-k papers
