"""
The agent's brain: same chatbot-node + tools-node + conditional-edge shape
as before, but with a real web search tool bound to it.
"""

import os
from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_tavily import TavilySearch

load_dotenv()

SYSTEM_PROMPT = (
    "You are a voice assistant, like Siri. Your replies are spoken aloud, "
    "so keep them short — one or two sentences unless the user clearly "
    "wants detail. Use the web search tool whenever a question needs "
    "current information (news, prices, weather, recent events, facts you "
    "aren't sure about). Don't mention that you searched; just answer "
    "naturally, the way a person would."
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
            "Set GROQ_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY in .env"
        )


tools = [TavilySearch(max_results=3)]
llm = get_llm().bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot_node(state: State) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


def build_graph():
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", ToolNode(tools))

    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges("chatbot", tools_condition)
    graph_builder.add_edge("tools", "chatbot")

    memory = MemorySaver()
    return graph_builder.compile(checkpointer=memory)


graph = build_graph()
