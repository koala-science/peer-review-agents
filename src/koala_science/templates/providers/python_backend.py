"""Replace proposal orchestration; Koala still verifies every candidate."""

from koala_science import BackendBudget, BackendResult, Limits, PaperContext


class PythonBackend:
    supports_budget = True

    async def propose(
        self, context: PaperContext, limits: Limits, budget: BackendBudget
    ) -> BackendResult:
        # Before EACH external model call: await budget.reserve_call().
        # After completion: budget.report_usage(model_response).
        # Empty output is valid. Replace this with bounded proposal orchestration.
        # Report only spans your implementation actually inspected.
        return BackendResult(candidates=[], inspected_span_ids=[])
