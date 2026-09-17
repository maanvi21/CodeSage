"""
Simple chatbot using LangChain + LangGraph.

Setup:
    pip install -r requirements.txt
    # Put your key in a .env file in this folder (see .env), e.g.:
    #   GROQ_API_KEY=gsk-your-key-here

Run:
    python chatbot.py
"""

import os
from typing import Annotated
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()  # reads a .env file in the same folder and sets env vars from it


# ---------------------------------------------------------------------------
# 1. Pick a chat model (LangChain's job: wrap a provider's API in a common
#    interface so the rest of the code doesn't care which LLM is behind it)
# ---------------------------------------------------------------------------
def get_llm():
    if os.getenv("GROQ_API_KEY"):
        from langchain_groq import ChatGroq
        # llama-3.3-70b-versatile is Enterprise-only as of late 2026; use a
        # currently-available production model instead. Swap for
        # "openai/gpt-oss-120b" (bigger, slower) if you want more capability.
        return ChatGroq(model="openai/gpt-oss-20b")
    elif os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-6")
    elif os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini")
    else:
        raise RuntimeError(
            "Set GROQ_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY as an "
            "environment variable before running this script."
        )


llm = get_llm()


# ---------------------------------------------------------------------------
# 2. Define the graph's state (LangGraph's job: model the app as a graph of
#    steps that read and write a shared, typed state object)
# ---------------------------------------------------------------------------
class State(TypedDict):
    # `add_messages` is a reducer: instead of each node OVERWRITING
    # "messages", new messages returned by a node are appended to the
    # existing list (and it knows how to merge LangChain message objects).
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# 3. Define the node(s). A node is just a function: state in, partial state
#    (updates) out.
# ---------------------------------------------------------------------------
def chatbot_node(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# ---------------------------------------------------------------------------
# 4. Wire the graph together: nodes + edges (control flow between nodes)
# ---------------------------------------------------------------------------
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

# A checkpointer persists state per "thread_id", which is what gives the
# graph multi-turn memory across calls to .invoke().
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)


# ---------------------------------------------------------------------------
# 5. Simple CLI loop
# ---------------------------------------------------------------------------
def main():
    config = {"configurable": {"thread_id": "cli-session-1"}}

    print("Simple LangGraph chatbot. Type 'quit' to exit.\n")
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
        ai_message = result["messages"][-1]
        print(f"Bot: {ai_message.content}\n")


if __name__ == "__main__":
    main()