"""Content Creation Crew – generates a blog post or social media content."""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from backend.config.llm_factory import get_llm
from backend.models.schemas import AgentConfig, CrewConfig, TaskConfig


class ContentCrew:
    """A crew of two agents: content strategist and copywriter."""

    @classmethod
    def config(cls) -> CrewConfig:
        return CrewConfig(
            name="content",
            description="Plan and write engaging blog posts or social media content.",
            agents=[
                AgentConfig(
                    name="strategist",
                    role="Content Strategist",
                    goal="Create a content plan for {topic} targeting {audience}",
                    backstory=(
                        "You are a seasoned content strategist who knows how to "
                        "craft compelling narratives and structure content for "
                        "maximum engagement."
                    ),
                ),
                AgentConfig(
                    name="copywriter",
                    role="Senior Copywriter",
                    goal="Write engaging content on {topic} for {audience}",
                    backstory=(
                        "You are an experienced copywriter with a talent for "
                        "turning strategy into compelling, share-worthy content."
                    ),
                ),
            ],
            tasks=[
                TaskConfig(
                    name="strategy_task",
                    description=(
                        "Create a detailed content plan for a {content_type} "
                        "about {topic} targeting {audience}. "
                        "Include headline options, key points, and tone of voice."
                    ),
                    expected_output=(
                        "A content brief with title options, outline, key messages "
                        "and recommended tone."
                    ),
                    agent_name="strategist",
                ),
                TaskConfig(
                    name="writing_task",
                    description=(
                        "Write a complete {content_type} on {topic} for {audience} "
                        "following the content brief provided."
                    ),
                    expected_output=(
                        "A fully written, publication-ready {content_type} "
                        "in markdown format."
                    ),
                    agent_name="copywriter",
                ),
            ],
            process="sequential",
        )

    @classmethod
    def build(cls, llm_provider: str = "google") -> Crew:
        """Instantiate and return a ready-to-run :class:`crewai.Crew`."""
        llm = get_llm(provider=llm_provider)

        strategist = Agent(
            role="Content Strategist",
            goal="Create a content plan for {topic} targeting {audience}",
            backstory=(
                "You are a seasoned content strategist who knows how to craft "
                "compelling narratives and structure content for maximum engagement."
            ),
            llm=llm,
            verbose=True,
        )

        copywriter = Agent(
            role="Senior Copywriter",
            goal="Write engaging content on {topic} for {audience}",
            backstory=(
                "You are an experienced copywriter with a talent for turning "
                "strategy into compelling, share-worthy content."
            ),
            llm=llm,
            verbose=True,
        )

        strategy_task = Task(
            description=(
                "Create a detailed content plan for a {content_type} "
                "about {topic} targeting {audience}. "
                "Include headline options, key points, and tone of voice."
            ),
            expected_output=(
                "A content brief with title options, outline, key messages "
                "and recommended tone."
            ),
            agent=strategist,
        )

        writing_task = Task(
            description=(
                "Write a complete {content_type} on {topic} for {audience} "
                "following the content brief provided."
            ),
            expected_output=(
                "A fully written, publication-ready {content_type} in markdown format."
            ),
            agent=copywriter,
        )

        return Crew(
            agents=[strategist, copywriter],
            tasks=[strategy_task, writing_task],
            process=Process.sequential,
            verbose=True,
        )
