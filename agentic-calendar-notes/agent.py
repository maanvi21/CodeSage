"""
The LangGraph agent itself. Same shape as chatbot_with_tools.py, extended
with a system prompt and six tools instead of one.
"""

import os
from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from tools import ALL_TOOLS

load_dotenv()

SYSTEM_PROMPT = (
    "You are a helpful personal assistant that manages the user's notes "
    "and reminders. Use your tools to add, list, and delete notes and "
    "reminders — don't just say you did something, actually call the "
    "tool. When deleting, if the user doesn't give an id, call the "
    "matching list tool first, find the right item, then delete it. Keep "
    "replies short and confirm what you did."
)


def get_llm():
    if os.getenv("GROQ_API_KEY"):
        from langchain_groq import ChatGroq
        return ChatGroq(model="openai/gpt-oss-20b")
    elif os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-6")
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini")
    else:
        raise RuntimeError(
            "Set GROQ_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY in your "
            ".env file."
        )


llm = get_llm().bind_tools(ALL_TOOLS)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot_node(state: State) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


def build_graph():
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", ToolNode(ALL_TOOLS))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")

    memory = MemorySaver()
    return graph_builder.compile(checkpointer=memory)


# Compiled once, reused across Streamlit reruns via the module cache.
graph = build_graph()
