from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.rag.retrieval import hybrid_retrieve


class GraphState(TypedDict):
    query: str
    query_type: str
    refined_query: str
    route_strategy: str
    requester_user_id: int
    requester_role: str
    contexts: list[dict]


def _analyze_query(state: GraphState):
    q = state["query"].strip()
    query_type = "question" if "?" in q else "command"
    if any(t in q.lower() for t in ["when", "id", "date", "version"]):
        route_strategy = "factual"
    elif any(t in q.lower() for t in ["summarize", "compare", "explain", "why"]):
        route_strategy = "analytical"
    else:
        route_strategy = "balanced"
    return {"query_type": query_type, "refined_query": q, "route_strategy": route_strategy}


def _retrieve(state: GraphState):
    contexts = hybrid_retrieve(
        state["refined_query"],
        k=6,
        requester_user_id=state.get("requester_user_id"),
        requester_role=state.get("requester_role", "user"),
    )
    return {"contexts": contexts}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("analyze_query", _analyze_query)
    graph.add_node("retrieve", _retrieve)

    graph.add_edge(START, "analyze_query")
    graph.add_edge("analyze_query", "retrieve")
    graph.add_edge("retrieve", END)

    return graph.compile()


graph_app = build_graph()
