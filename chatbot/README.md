# Simple LangChain + LangGraph Chatbot

Two runnable files:
- `chatbot.py` — minimal chatbot with persistent conversation memory.
- `chatbot_with_tools.py` — same idea, extended with one tool call.

## Setup

```bash
pip install -r requirements.txt
export GROQ_API_KEY=gsk-...   # get one at https://console.groq.com/keys
python chatbot.py
```

The model picker in both scripts checks for `GROQ_API_KEY` first (falling back to `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` if set instead), and uses `ChatGroq(model="openai/gpt-oss-20b")` from the `langchain-groq` package. Note: Groq retired `llama-3.3-70b-versatile` and `llama-3.1-8b-instant` for free/developer accounts (Enterprise-only now) — `openai/gpt-oss-20b` and `openai/gpt-oss-120b` are the current general-purpose production models. Check `https://console.groq.com/docs/models` for what's live on your account, since Groq's lineup changes often.

---

## The theory, in the order you'll actually use it

### 1. What LangChain gives you
LangChain's core job here is a **standard interface over different LLM providers**. `ChatGroq`, `ChatAnthropic`, and `ChatOpenAI` all expose the same `.invoke(messages)` method and return the same `AIMessage` type, so your application code doesn't change if you swap providers — this is why `get_llm()` can pick between them with no changes to the graph itself. Groq is worth knowing apart from the others: it doesn't train its own models, it *hosts* open models (Llama, Gemma, etc.) on custom inference hardware built for speed, which is why it's a common pick when you want a fast, cheap chatbot backend. Messages themselves come in a small set of types: `HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage` — LangGraph and LangChain both build around this shared message format.

### 2. Why LangGraph instead of just calling the LLM in a loop
A single call-the-LLM-in-a-loop script works, but breaks down once you need branching logic ("if the model wants a tool, go run it"), retries, human approval steps, or persistent memory across sessions. LangGraph models your app as a **graph**:

- **State** — a typed object (here, a `TypedDict`) that flows through the graph and accumulates data as it goes.
- **Nodes** — plain functions. Each takes the current state and returns a *partial update* to it.
- **Edges** — define what runs next. A **normal edge** always goes A → B. A **conditional edge** picks the next node based on the current state (e.g., "does the last message contain a tool call?").
- **START / END** — special markers for the graph's entry and exit points.

This buys you two things a plain loop doesn't give for free: composability (nodes are easy to test and reuse) and built-in support for cycles (a tool-calling loop is just an edge that points back to an earlier node).

### 3. The state and the `add_messages` reducer
```python
class State(TypedDict):
    messages: Annotated[list, add_messages]
```
Every node returns updates to the state, e.g. `{"messages": [new_message]}`. By default LangGraph would *overwrite* `state["messages"]` with whatever a node returns. The `add_messages` reducer changes that behavior to **append** instead — and it knows how to deduplicate/merge LangChain message objects by ID. This is what turns "one node returning one message" into "a growing conversation history."

### 4. Compiling the graph
```python
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile(checkpointer=memory)
```
`StateGraph` is the builder; `.compile()` turns it into a runnable object. Compiling with a **checkpointer** (here, `MemorySaver`, an in-memory store) is what enables multi-turn memory: on every `.invoke()`, LangGraph loads the saved state for that `thread_id`, runs the graph, and saves the updated state back — so the next call automatically has the full history.

### 5. Threads = separate conversations
```python
config = {"configurable": {"thread_id": "cli-session-1"}}
graph.invoke({"messages": [...]}, config)
```
`thread_id` is just a key. Different IDs get independent, isolated conversation histories from the same compiled graph — this is how you'd support multiple users or multiple chat sessions with one app. `MemorySaver` keeps everything in process memory (lost on restart); for production you'd swap in a persistent checkpointer (e.g. SQLite/Postgres-backed) with the same interface.

### 6. Adding tools (see `chatbot_with_tools.py`)
Three pieces make tool use work:
1. `@tool` — wraps a function with a name/description the model can read, so it can decide *when* to call it.
2. `llm.bind_tools(tools)` — tells the model which tools exist for this conversation.
3. `tools_condition` + `ToolNode` — a conditional edge inspects the model's last message: if it's a tool call, route to `ToolNode` (which executes the tool and returns a `ToolMessage`), then loop back to the chatbot node so the model can use the result. If not, route straight to `END`.

This request/execute/respond loop is the same shape used for far more complex agents — more tools, retrieval steps, sub-agents — you're just adding more nodes and conditional edges to the same graph.

### Mental model summary
| Concept | Role |
|---|---|
| LangChain `ChatModel` | uniform way to call any LLM provider |
| LangGraph `State` | the data that flows through your app |
| Node | a function; one step of work |
| Edge / conditional edge | control flow between steps |
| Checkpointer + `thread_id` | persistent, per-conversation memory |
| Tool + `ToolNode` | lets the model take actions, not just talk |

From here, natural next steps are: a `SystemMessage` for persona/instructions, streaming responses (`graph.stream(...)`), a persistent checkpointer, and a proper UI (Gradio/Streamlit/FastAPI) instead of the CLI loop.