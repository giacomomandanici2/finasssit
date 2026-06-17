import pytest

from datapizza.agents import Agent
from datapizza.clients.mock_client import MockClient
from datapizza.tools import tool

from app.agents.exceptions import ToolError, ToolForbidden, ToolTimeout
from app.agents.tools import safe_tool


@tool
@safe_tool
async def tool_forbidden(**kwargs: object) -> str:
    raise ToolForbidden("Accesso negato al record richiesto", tool_name="tool_forbidden")


@tool
@safe_tool(timeout=0.001)
async def tool_timeout(**kwargs: object) -> str:
    import asyncio
    await asyncio.sleep(10)
    return "mai raggiunto"


@tool
@safe_tool
async def tool_generic_error(**kwargs: object) -> str:
    raise ToolError("Errore generico nella fonte dati", tool_name="tool_generic_error")


@pytest.mark.asyncio
async def test_tool_forbidden_returns_graceful_message():
    agent = Agent(
        name="test",
        client=MockClient(),
        tools=[tool_forbidden],
        max_steps=3,
    )
    result = await agent.a_run("usa lo strumento function")
    assert result is not None
    assert result.text
    assert "Accesso negato" in result.text


@pytest.mark.asyncio
async def test_tool_timeout_returns_graceful_message():
    agent = Agent(
        name="test",
        client=MockClient(),
        tools=[tool_timeout],
        max_steps=3,
    )
    result = await agent.a_run("usa lo strumento function")
    assert result is not None
    assert result.text
    assert "tempo massimo" in result.text or "superato" in result.text


@pytest.mark.asyncio
async def test_tool_error_returns_graceful_message():
    agent = Agent(
        name="test",
        client=MockClient(),
        tools=[tool_generic_error],
        max_steps=3,
    )
    result = await agent.a_run("usa lo strumento function")
    assert result is not None
    assert result.text
    assert "Errore" in result.text or "errore" in result.text


def test_exception_hierarchy():
    assert issubclass(ToolForbidden, ToolError)
    assert issubclass(ToolTimeout, ToolError)
    err = ToolForbidden("test", tool_name="x")
    assert err.tool_name == "x"
    assert str(err) == "test"
