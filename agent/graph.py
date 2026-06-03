"""
agent/graph.py — LangGraph StateGraph for Remesa.

Wires all seven nodes with conditional routing that short-circuits to END on
any ``failed`` / ``cancelled`` status. Human-in-the-loop is handled by the
dynamic ``interrupt()`` inside ``confirm_with_user`` (see agent/nodes.py), so we
do NOT pass ``interrupt_before`` — that would double-pause the graph.

Durable checkpointing uses AsyncSqliteSaver. ``from_conn_string`` returns an
async context manager, so ``build_graph`` is async: it enters the context, keeps
it alive on the compiled graph, and exposes ``aclose()`` for clean shutdown.
"""
from functools import partial

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agent.nodes import (
    check_sanctions,
    confirm_with_user,
    execute_transfer,
    generate_receipt,
    notify_recipient,
    parse_intent,
    quote_fx,
)
from agent.state import AgentState

# Linear order of the pipeline. Conditional routing walks this sequence,
# jumping to END whenever a node sets status to "failed" or "cancelled".
_SEQUENCE = [
    "parse_intent",
    "quote_fx",
    "check_sanctions",
    "confirm_with_user",
    "execute_transfer",
    "notify_recipient",
    "generate_receipt",
]


def _make_router(current: str):
    """Return a conditional-edge function: continue to next node, or END."""
    idx = _SEQUENCE.index(current)
    nxt = _SEQUENCE[idx + 1] if idx + 1 < len(_SEQUENCE) else END

    def _route(state: AgentState) -> str:
        if state.get("status") in ("failed", "cancelled"):
            return END
        return nxt

    return _route


def _assemble(agent_kit) -> StateGraph:
    """Build (but do not compile) the StateGraph with all nodes and edges."""
    builder = StateGraph(AgentState)

    builder.add_node("parse_intent", parse_intent)
    builder.add_node("quote_fx", partial(quote_fx, agent_kit=agent_kit))
    builder.add_node("check_sanctions", partial(check_sanctions, agent_kit=agent_kit))
    builder.add_node("confirm_with_user", confirm_with_user)
    builder.add_node("execute_transfer", partial(execute_transfer, agent_kit=agent_kit))
    builder.add_node("notify_recipient", notify_recipient)
    builder.add_node("generate_receipt", generate_receipt)

    builder.set_entry_point("parse_intent")

    # Nodes that can fail/cancel route conditionally to the next node or END.
    for node in (
        "parse_intent",
        "quote_fx",
        "check_sanctions",
        "confirm_with_user",
        "execute_transfer",
    ):
        nxt = _SEQUENCE[_SEQUENCE.index(node) + 1]
        builder.add_conditional_edges(
            node,
            _make_router(node),
            {nxt: nxt, END: END},
        )

    # Tail of the happy path never fails — plain edges.
    builder.add_edge("notify_recipient", "generate_receipt")
    builder.add_edge("generate_receipt", END)

    return builder


async def build_graph(agent_kit, db_path: str = "remesa_checkpoints.db"):
    """
    Build and compile the StateGraph with durable SQLite checkpointing.

    Returns the CompiledGraph. The compiled object carries an ``aclose()``
    coroutine that releases the SQLite connection; call it on shutdown.
    Call this once at startup and store the result as a singleton.
    """
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    builder = _assemble(agent_kit)

    saver_cm = AsyncSqliteSaver.from_conn_string(db_path)
    saver = await saver_cm.__aenter__()  # keep connection open for the app's life
    graph = builder.compile(checkpointer=saver)

    async def _aclose():
        await saver_cm.__aexit__(None, None, None)

    graph.aclose = _aclose  # type: ignore[attr-defined]
    return graph


def build_graph_in_memory(agent_kit):
    """
    Synchronous, in-memory variant for tests and quick experiments.

    Uses MemorySaver (no disk, no async context). Checkpoints do not survive a
    process restart — use ``build_graph`` for the real demo.
    """
    return _assemble(agent_kit).compile(checkpointer=MemorySaver())
