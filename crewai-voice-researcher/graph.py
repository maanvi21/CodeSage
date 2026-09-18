"""
The LangGraph orchestrator.

Flow:
    router  --(deep research?)-->  crew_research --> END
       |
       --(quick question)--> chatbot <--> tools --> END (when no more tool calls)

`router` is a pass-through node whose only job is to let a conditional edge
inspect the latest human message BEFORE the LLM ever sees it, so we can skip
straight to the CrewAI crew for report-style requests instead of burning a
turn on the single-agent tool loop.
"""

import os
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage

from tools import tools, needs_deep_research, extract_topic
from crew.research_crew import run_research
from report_utils import save_report


class State(TypedDict):
    messages: Annotated[list, add_messages]


llm = ChatGroq(model="openai/gpt-oss-120b", api_key=os.getenv("GROQ_API_KEY"))
llm_with_tools = llm.bind_tools(tools)


def router_node(state: State) -> State:
    # Pass-through — the conditional edge attached to this node does the work.
    return state


def route_from_router(state: State) -> str:
    last_human = state["messages"][-1]
    text = getattr(last_human, "content", "") or ""
    return "crew_research" if needs_deep_research(text) else "chatbot"


def chatbot_node(state: State) -> State:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def crew_research_node(state: State) -> State:
    last_human = state["messages"][-1]
    topic = extract_topic(getattr(last_human, "content", ""))

    report_text = run_research(topic)
    saved_path = save_report(topic, report_text)

    reply = (
        f"I put together a full report on '{topic}' — saved to {saved_path}.\n\n"
        f"{report_text}"
    )
    return {"messages": [AIMessage(content=reply)]}


def build_graph():
    graph = StateGraph(State)

    graph.add_node("router", router_node)
    graph.add_node("chatbot", chatbot_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("crew_research", crew_research_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        route_from_router,
        {"crew_research": "crew_research", "chatbot": "chatbot"},
    )

    # Same tool-loop pattern as the rest of CodeSage: tools_condition checks
    # whether the LLM's last message requested a tool call.
    graph.add_conditional_edges("chatbot", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "chatbot")

    graph.add_edge("crew_research", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
