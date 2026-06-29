"""
LangGraph StateGraph — wires Supervisor, Research, Analysis, and Critic agents.
"""
from langgraph.graph import StateGraph, END

from agents.state import AnalysisState
from agents.supervisor import supervisor_node, route_from_supervisor
from agents.research_agent import research_node
from agents.analysis_agent import analysis_node
from agents.critic_agent import critic_node


def build_graph():
    workflow = StateGraph(AnalysisState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("research", research_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("critic", critic_node)

    # Entry point
    workflow.set_entry_point("supervisor")

    # Supervisor routes conditionally
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "research": "research",
            "analysis": "analysis",
            "critic": "critic",
            "__end__": END,
        },
    )

    # All agents return to supervisor after running
    workflow.add_edge("research", "supervisor")
    workflow.add_edge("analysis", "supervisor")
    workflow.add_edge("critic", "supervisor")

    return workflow.compile()


# Module-level compiled graph (reused across requests)
graph = build_graph()
