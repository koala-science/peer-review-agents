"""Replace proposal orchestration; Koala still verifies every candidate."""

from koala_science import BackendBudget, Limits, PaperContext, Proposals


class PythonBackend:
    supports_budget = True

    async def propose(
        self, context: PaperContext, limits: Limits, budget: BackendBudget
    ) -> Proposals:
        # Before EACH external model call: await budget.reserve_call().
        # After completion: budget.report_usage(model_response).
        # Empty output is valid. Replace this with bounded proposal orchestration.
        return Proposals(candidates=[])
