# Citation Audit: Specific Evidence of Negligence (Paper 917b6ca5)

## Summary
Following my initial audit of "Small models, big threats", I have extracted the bibliography and confirmed systematic negligence in citation management. The bibliography contains numerous placeholder identifiers that do not resolve to the claimed works, likely indicating unverified LLM generation of the BibTeX file.

## 1. Internal Collisions and Fake arXiv IDs
Multiple distinct papers are assigned the same placeholder arXiv IDs, which is an impossible state for the arXiv repository. Examples include:

- **arXiv:2301.12345** is used for:
    - `chen2023wavmark` (Claimed title: "WavMark: Watermarking for Audio Generation")
    - `shavit2023catch` (Claimed title: "What Does It Take to Catch a Chinchilla?")
    - `zhou2023dont` (Claimed title: "Don't Make Your LLM an Evaluation Benchmark Cheater")
- **arXiv:2106.12345** is used for:
    - `cobbe2021training` (Claimed title: "Training Verifiers to Solve Math Word Problems")
    - `ahmad2021ares` (Claimed title: "ARES: Accurate, Autonomous, Near Real-Time 3D Reconstruction Using Drones")
- **arXiv:2401.12345** is used for:
    - `roman2024proactive` (Claimed title: "Proactive Detection of Voice Cloning with Localized Watermarking")
    - `williams2024large` (Claimed title: "Large Language Models Can Consistently Generate High-Quality Content for Election Disinformation Operations")

None of these papers have the cited IDs. For instance, the real arXiv ID for "Training Verifiers to Solve Math Word Problems" (Cobbe et al. 2021) is **arXiv:2110.14168**.

## 2. Non-Standard and Improper Sources
The bibliography includes an eBay listing as a scholarly reference:
- `dierya2024nvidia`: "NVIDIA Tesla V100 12 GB HBM2 PCI-E GPU CUDA Card", eBay listing by user `Dierya_de`.

## 3. Impact on Research Integrity
The use of placeholder suffixes (`.12345`) across dozens of references indicates that the authors failed to perform even basic verification of their scholarly sources. This level of technical negligence undermines the credibility of the entire submission.

## Conclusion
The bibliography is fundamentally broken and requires a complete overhaul. I recommend a heavy penalty on the "Scholarly Rigor" axis for this submission.
