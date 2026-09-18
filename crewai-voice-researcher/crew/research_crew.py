"""
The CrewAI layer: a 3-agent sequential crew that turns a topic into a
structured, fact-checked report. Kept in its own module so it can be
tested standalone (see the __main__ block) before wiring it into LangGraph.
"""

import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool

_llm = LLM(model="groq/llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
_search_tool = TavilySearchTool()

researcher = Agent(
    role="Researcher",
    goal="Find accurate, current, well-sourced information on the given topic",
    backstory=(
        "An investigative researcher who digs up relevant facts and recent "
        "developments before anyone else touches the topic. Always notes sources."
    ),
    tools=[_search_tool],
    llm=_llm,
    verbose=True,
)

fact_checker = Agent(
    role="Fact-checker",
    goal="Verify claims from the research and flag anything unsupported or contradictory",
    backstory=(
        "A skeptical editor who cross-checks every claim against sources before "
        "it goes to print. Flags anything uncertain rather than letting it slide."
    ),
    tools=[_search_tool],
    llm=_llm,
    verbose=True,
)

writer = Agent(
    role="Report Writer",
    goal="Turn verified research into a clear, structured report",
    backstory=(
        "A technical writer who turns raw research into a readable markdown "
        "report with a short executive summary up top and clear section headers."
    ),
    llm=_llm,
    verbose=True,
)


def build_crew(topic: str) -> Crew:
    research_task = Task(
        description=(
            f"Research the topic: '{topic}'. Gather key facts, recent developments, "
            "and relevant context. Note where each fact came from."
        ),
        expected_output="A bullet-point list of researched facts with sources noted.",
        agent=researcher,
    )

    fact_check_task = Task(
        description=(
            "Review the research findings and verify each claim against current "
            "sources. Flag anything uncertain, outdated, or contradictory."
        ),
        expected_output="An annotated list of facts, each marked as verified or uncertain, with brief reasoning.",
        agent=fact_checker,
        context=[research_task],
    )

    write_task = Task(
        description=(
            f"Write a structured markdown report on '{topic}' using the verified "
            "research. Start with a 2-3 sentence executive summary, then organize "
            "the body under clear section headers. Only include verified facts; "
            "note explicitly where something is uncertain."
        ),
        expected_output="A complete markdown report with an executive summary and sectioned body.",
        agent=writer,
        context=[fact_check_task],
    )

    return Crew(
        agents=[researcher, fact_checker, writer],
        tasks=[research_task, fact_check_task, write_task],
        process=Process.sequential,
        verbose=True,
    )


def run_research(topic: str) -> str:
    """Convenience entry point used by the LangGraph node."""
    crew = build_crew(topic)
    result = crew.kickoff()
    return result.raw


if __name__ == "__main__":
    # Sanity-check the crew on its own before wiring it into the graph.
    from dotenv import load_dotenv
    load_dotenv()
    output = run_research("Impact of AI on renewable energy grids")
    print(output)
