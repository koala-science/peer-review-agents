# Paper selection strategy

Describe in plain language which papers this agent should review. The agent
applies this to a shortlist of eligible papers, least reviewed first (after the
filters in agent.yaml), and records its reason for every choice in the selection
log.

Review the papers with the fewest existing arguments first, in any field: those
are where a careful review adds the most. Keep the order of the shortlist unless
two papers have the same number of arguments.

Skip only papers that cannot be reviewed from their text, such as a paper whose
abstract shows it is not a research paper.
