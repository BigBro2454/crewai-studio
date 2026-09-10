"""Research Crew – three agents that research a topic and produce a report."""
from __future__ import annotations

import os
from crewai import Agent, Crew, LLM, Process, Task
try:
    from crewai_tools import SerperDevTool
    _HAS_SERPER = True
except ImportError:
    _HAS_SERPER = False

from backend.config.llm_factory import get_llm
from backend.models.schemas import AgentConfig, CrewConfig, TaskConfig


class ResearchCrew:
    """A crew of three agents: researcher, analyst, writer."""

    @classmethod
    def config(cls) -> CrewConfig:
        return CrewConfig(
            name="research",
            description="Research a topic deeply and produce a structured report.",
            agents=[
                AgentConfig(
                    name="researcher",
                    role="Senior Research Specialist",
                    goal="Find comprehensive, accurate information about {topic}",
                    backstory=(
                        "You are an expert researcher with years of experience "
                        "gathering data from multiple sources. You are thorough, "
                        "fact-checking everything before reporting."
                    ),
                ),
                AgentConfig(
                    name="analyst",
                    role="Data Analyst",
                    goal="Analyse and synthesise the research findings about {topic}",
                    backstory=(
                        "You are a seasoned analyst who distils raw research into "
                        "clear insights, identifying patterns and key takeaways."
                    ),
                ),
                AgentConfig(
                    name="writer",
                    role="Technical Writer",
                    goal="Write a polished, well-structured report on {topic}",
                    backstory=(
                        "You turn complex analytical findings into readable, "
                        "well-structured documents suitable for any audience."
                    ),
                ),
            ],
            tasks=[
                TaskConfig(
                    name="research_task",
                    description="Research {topic} thoroughly using all available sources.",
                    expected_output="A bullet-point summary of key facts and sources.",
                    agent_name="researcher",
                ),
                TaskConfig(
                    name="analysis_task",
                    description=(
                        "Analyse the research findings on {topic}, "
                        "identify patterns and key insights."
                    ),
                    expected_output="An analytical breakdown with numbered insights.",
                    agent_name="analyst",
                ),
                TaskConfig(
                    name="writing_task",
                    description=(
                        "Write a comprehensive report on {topic} using the "
                        "research and analysis provided."
                    ),
                    expected_output=(
                        "A markdown-formatted report with introduction, "
                        "findings, analysis and conclusion."
                    ),
                    agent_name="writer",
                ),
            ],
            process="sequential",
        )

    @classmethod
    def build(cls, llm_provider: str = "google") -> Crew:
        """Instantiate and return a ready-to-run :class:`crewai.Crew`."""
        llm = get_llm(provider=llm_provider)

        # Optional web-search tool (only if crewai_tools + SERPER_API_KEY available)
        tools = [SerperDevTool()] if (_HAS_SERPER and bool(os.getenv("SERPER_API_KEY"))) else []

        researcher = Agent(
            role="Senior Research Specialist",
            goal="Find comprehensive, accurate information about {topic}",
            backstory=(
                "You are an expert researcher with years of experience "
                "gathering data from multiple sources."
            ),
            llm=llm,
            tools=tools,
            verbose=True,
        )

        analyst = Agent(
            role="Data Analyst",
            goal="Analyse and synthesise the research findings about {topic}",
            backstory=(
                "You are a seasoned analyst who distils raw research "
                "into clear insights."
            ),
            llm=llm,
            verbose=True,
        )

        writer = Agent(
            role="Technical Writer",
            goal="Write a polished, well-structured report on {topic}",
            backstory="You turn complex findings into readable, structured documents.",
            llm=llm,
            verbose=True,
        )

        research_task = Task(
            description="Research {topic} thoroughly using all available sources.",
            expected_output="A bullet-point summary of key facts and sources.",
            agent=researcher,
        )

        analysis_task = Task(
            description=(
                "Analyse the research findings on {topic}, "
                "identify patterns and key insights."
            ),
            expected_output="An analytical breakdown with numbered insights.",
            agent=analyst,
        )

        writing_task = Task(
            description=(
                "Write a comprehensive report on {topic} using the "
                "research and analysis provided."
            ),
            expected_output=(
                "A markdown-formatted report with introduction, "
                "findings, analysis and conclusion."
            ),
            agent=writer,
        )

        return Crew(
            agents=[researcher, analyst, writer],
            tasks=[research_task, analysis_task, writing_task],
            process=Process.sequential,
            verbose=True,
        )
