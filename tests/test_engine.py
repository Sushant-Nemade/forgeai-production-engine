import pytest

from core_engine.agents.pm_agent import ProductManagerAgent
from core_engine.orchestrator import State


@pytest.mark.asyncio
async def test_pm_schema_mapping():
    schema = await ProductManagerAgent().run("resource: invoice; customer_id(string), amount(number), paid(boolean)")
    assert schema.resource == "invoice"
    assert {f.name for f in schema.fields} == {"customer_id", "amount", "paid"}


def test_state_machine_contract():
    assert State.RECEIVED.value == "received"
    assert State.DEPLOYABLE.value == "deployable"
