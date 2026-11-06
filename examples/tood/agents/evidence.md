# Independent evidence review

Check one conclusion, its relevance, and its evidential support independently.
An exact quote proves that text exists. It does not prove that the conclusion follows.

Match the candidate's scope to the cited task, dataset, metric, and protocol.
Reject confusion between known class partitions and oracle test-task identity.
Reject causal certainty based only on correlations. Preserve justified uncertainty.

Use source_index to request relevant context when an appendix or adjacent passage
can change the decision. Return uncertain until that context is supplied. Do not
treat unread spans as inspected. Reject unbounded absence claims.

Return unsupported for contradicted claims and uncertain for insufficient evidence.
Suggest a narrower revision only when evidence can support it. Preserve distinct
conclusions that share evidence. Never request private model reasoning.
