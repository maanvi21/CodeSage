"""
Same chatbot as chatbot.py, extended with one tool call and a conditional
edge — the pattern you'd extend to add search, calculators, DB lookups, etc.

Setup:
    pip install -r requirements.txt
    # Put your key in a .env file in this folder (see .env), e.g.:
    #   GROQ_API_KEY=gsk-your-key-here

Run:
    python chatbot_with_tools.py
"""

import os
from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()  # reads a .env file in the same folder and sets env vars from it


# ---------------------------------------------------------------------------
# 1. Define a tool. The @tool decorator turns a normal Python function into
#    something the LLM can be told about and choose to call.
# ---------------------------------------------------------------------------
@tool
def get_word_length(word: str) -> int:
    """Return the number of characters in a word."""
    return len(word)


tools = [get_word_length]


# ---------------------------------------------------------------------------
# 2. Chat model, bound to the tools so it knows they're available
# ---------------------------------------------------------------------------
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
            "Set GROQ_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY first."
        )


llm = get_llm().bind_tools(tools)


# ---------------------------------------------------------------------------
# 3. State + nodes
# ---------------------------------------------------------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]


def chatbot_node(state: State) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}


# ---------------------------------------------------------------------------
# 4. Graph with a conditional edge:
#    chatbot -> (did it ask for a tool?) -> tools -> chatbot -> ... -> END
# ---------------------------------------------------------------------------
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", ToolNode(tools))

graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,  # routes to "tools" if the last message requested a
    # tool call, otherwise routes to END
)
graph_builder.add_edge("tools", "chatbot")  # after a tool runs, let the
# model see the result and respond

memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)


def main():
    config = {"configurable": {"thread_id": "cli-session-tools"}}
    print("Tool-using LangGraph chatbot. Try: 'how many letters in strawberry?'")
    print("Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Bye!")
            break
        if not user_input:
            continue

        result = graph.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config,
        )
        print(f"Bot: {result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()