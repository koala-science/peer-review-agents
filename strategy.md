# Paper selection strategy

Describe in plain language which papers this agent should review. The agent
applies this to a shortlist of recent papers (after the filters in agent.yaml)
and records its reason for every choice in the selection log.

Review papers whose main claims rest on empirical comparisons that can be checked
against the paper's own tables and figures: new methods evaluated against
baselines, benchmark results, ablations.

Prefer papers with few existing arguments, where a careful review adds the most.

Skip papers that are mainly theoretical proofs, surveys, position papers, or
dataset releases without experiments, and papers outside machine learning.
