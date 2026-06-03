"""
agent/tools.py — LangChain tools wrapping Coinbase AgentKit.

Remesa's core flow drives AgentKit actions directly from the graph nodes
(see agent/nodes.py), which keeps the receipt deterministic. This module
additionally exposes AgentKit's actions as LangChain ``Tool`` objects so the
intent-parsing LLM can be upgraded to a tool-calling agent later without
restructuring the graph.
"""
import structlog

log = structlog.get_logger()


def get_langchain_tools(agent_kit) -> list:
    """
    Return AgentKit actions as LangChain tools.

    Uses ``coinbase-agentkit-langchain`` when available; returns an empty list
    otherwise so the rest of the app keeps working without the optional bridge.
    """
    try:
        from coinbase_agentkit_langchain import get_langchain_tools as _bridge

        tools = _bridge(agent_kit)
        log.info("Loaded AgentKit LangChain tools", count=len(tools))
        return tools
    except Exception as exc:  # noqa: BLE001
        log.warning("AgentKit LangChain bridge unavailable", error=str(exc))
        return []
