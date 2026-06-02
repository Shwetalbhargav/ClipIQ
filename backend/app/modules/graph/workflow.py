"""Workflow builder for Module 10: Graph.

Graph shape:

    START
      -> load_memory
      -> retrieve_a
      -> retrieve_b
      -> fetch_metadata
      -> compare
      -> build_context
      -> generate_response
      -> persist_turn
      -> END

The requested feature nodes are explicit:
- Retrieve A: `retrieve_a`
- Retrieve B: `retrieve_b`
- Fetch metadata: `fetch_metadata`
- Compare: `compare`
- Generate response: `generate_response`

This module uses LangGraph when installed. A tiny local fallback is included so
unit tests can still run in stripped-down CI environments; production should
install `langgraph` and use the compiled StateGraph.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .nodes import (
    GraphDependencies,
    create_build_context_node,
    create_compare_node,
    create_fetch_metadata_node,
    create_generate_response_node,
    create_load_memory_node,
    create_persist_turn_node,
    create_retrieve_a_node,
    create_retrieve_b_node,
)
from .state import GraphState

try:  # pragma: no cover - covered in a project environment with LangGraph installed
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - fallback exists for local kata/test runners
    END = "__end__"
    START = "__start__"
    StateGraph = None  # type: ignore[assignment]

Node = Callable[[GraphState], Awaitable[dict[str, Any]]]


class _LocalCompiledWorkflow:
    """Minimal async sequential executor used only when LangGraph is unavailable.

    It mimics the `ainvoke` method of a compiled LangGraph enough for unit tests.
    Do not rely on it for production tracing, branching, or checkpointing.
    """

    def __init__(self, nodes: list[Node]) -> None:
        self._nodes = nodes

    async def ainvoke(self, state: GraphState) -> GraphState:
        current: GraphState = dict(state)  # type: ignore[assignment]
        for node in self._nodes:
            updates = await node(current)
            current.update(updates)
        return current


def _node_sequence(deps: GraphDependencies) -> list[tuple[str, Node]]:
    """Create named nodes in execution order for both LangGraph and fallback."""

    return [
        ("load_memory", create_load_memory_node(deps)),
        ("retrieve_a", create_retrieve_a_node(deps)),
        ("retrieve_b", create_retrieve_b_node(deps)),
        ("fetch_metadata", create_fetch_metadata_node(deps)),
        ("compare", create_compare_node(deps)),
        ("build_context", create_build_context_node(deps)),
        ("generate_response", create_generate_response_node(deps)),
        ("persist_turn", create_persist_turn_node(deps)),
    ]


def build_graph(deps: GraphDependencies):
    """Build and compile the ClipIQ LangGraph workflow.

    The graph is intentionally linear for the MVP because every answer needs the
    same evidence package: memory, Video A retrieval, Video B retrieval, metadata,
    deterministic metric comparison, context, generation, and persistence.
    """

    nodes = _node_sequence(deps)

    if StateGraph is None:
        return _LocalCompiledWorkflow([node for _, node in nodes])

    graph = StateGraph(GraphState)
    for name, node in nodes:
        graph.add_node(name, node)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "retrieve_a")
    graph.add_edge("retrieve_a", "retrieve_b")
    graph.add_edge("retrieve_b", "fetch_metadata")
    graph.add_edge("fetch_metadata", "compare")
    graph.add_edge("compare", "build_context")
    graph.add_edge("build_context", "generate_response")
    graph.add_edge("generate_response", "persist_turn")
    graph.add_edge("persist_turn", END)

    return graph.compile()


async def run_graph(deps: GraphDependencies, *, comparison_id: str, question: str) -> GraphState:
    """Convenience wrapper used by the FastAPI chat service."""

    workflow = build_graph(deps)
    return await workflow.ainvoke({"comparison_id": comparison_id, "question": question})
