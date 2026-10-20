"""Enterprise Governance & Due Diligence Crew – 3-tier compliance, risk, and policy auditor."""
from __future__ import annotations

from crewai import Agent, Crew, Process, Task

from backend.config.llm_factory import get_llm
from backend.models.schemas import AgentConfig, CrewConfig, TaskConfig


class GovernanceCrew:
    """A crew of three agents: auditor, risk_evaluator, remediation_officer."""

    @classmethod
    def config(cls) -> CrewConfig:
        return CrewConfig(
            name="governance",
            description="Audit multi-agent systems and AI workflows for security, policy compliance, and risk containment.",
            agents=[
                AgentConfig(
                    name="auditor",
                    role="Security & Policy Auditor",
                    goal="Inspect AI workflows, data flows, and inputs for {topic} to detect policy violations and credential exposure",
                    backstory=(
                        "You are a certified cloud security architect and compliance specialist with deep expertise in "
                        "PCI-DSS, GDPR, and enterprise AI safety guardrails."
                    ),
                    llm_provider="google",
                ),
                AgentConfig(
                    name="risk_evaluator",
                    role="Systemic Risk Evaluator",
                    goal="Quantify architectural blast radius, token exhaustion risks, and rate limiting thresholds for {topic}",
                    backstory=(
                        "You are an L5 Systems Infrastructure Analyst specializing in distributed agent failure modes, "
                        "denial-of-wallet vectors, and latency SLAs."
                    ),
                    llm_provider="anthropic",
                ),
                AgentConfig(
                    name="remediation_officer",
                    role="Enterprise Remediation Officer",
                    goal="Synthesize corrective action plans and governance scorecards for {topic}",
                    backstory=(
                        "You are a technical program leader who translates technical audit findings into "
                        "actionable remediation roadmaps and executive governance matrices."
                    ),
                    llm_provider="openai",
                ),
            ],
            tasks=[
                TaskConfig(
                    name="audit_task",
                    description=(
                        "Conduct a rigorous compliance and security audit for {topic}. "
                        "Inspect input surfaces, PII exposure risks, API key leak potentials, and prompt injection vulnerabilities."
                    ),
                    expected_output="A structured list of detected security findings and credential hygiene status.",
                    agent_name="auditor",
                ),
                TaskConfig(
                    name="risk_task",
                    description=(
                        "Evaluate systemic blast radius, API quota boundaries, and recursive looping risks for {topic}. "
                        "Provide quantitative risk metrics and SLA impact assessments."
                    ),
                    expected_output="A quantitative risk assessment matrix with latency and token economics impact.",
                    agent_name="risk_evaluator",
                ),
                TaskConfig(
                    name="remediation_task",
                    description=(
                        "Develop an executive remediation roadmap and formal governance scorecard for {topic} "
                        "incorporating findings from both the auditor and risk evaluator."
                    ),
                    expected_output=(
                        "An executive-grade Markdown governance scorecard with prioritized remediation steps and an overall fleet readiness grade."
                    ),
                    agent_name="remediation_officer",
                ),
            ],
            process="sequential",
        )

    @classmethod
    def build(cls, llm_provider: str = "google") -> Crew:
        """Instantiate and return a ready-to-run :class:`crewai.Crew`."""
        llm = get_llm(provider=llm_provider)

        auditor = Agent(
            role="Security & Policy Auditor",
            goal="Inspect AI workflows and inputs for {topic} to detect policy violations and credential exposure",
            backstory=(
                "You are a certified cloud security architect and compliance specialist with deep expertise in "
                "PCI-DSS, GDPR, and enterprise AI safety guardrails."
            ),
            llm=llm,
            verbose=True,
        )

        risk_evaluator = Agent(
            role="Systemic Risk Evaluator",
            goal="Quantify architectural blast radius, token exhaustion risks, and rate limiting thresholds for {topic}",
            backstory=(
                "You are an L5 Systems Infrastructure Analyst specializing in distributed agent failure modes, "
                "denial-of-wallet vectors, and latency SLAs."
            ),
            llm=llm,
            verbose=True,
        )

        remediation_officer = Agent(
            role="Enterprise Remediation Officer",
            goal="Synthesize corrective action plans and governance scorecards for {topic}",
            backstory=(
                "You are a technical program leader who translates technical audit findings into "
                "actionable remediation roadmaps and executive governance matrices."
            ),
            llm=llm,
            verbose=True,
        )

        audit_task = Task(
            description=(
                "Conduct a rigorous compliance and security audit for {topic}. "
                "Inspect input surfaces, PII exposure risks, API key leak potentials, and prompt injection vulnerabilities."
            ),
            expected_output="A structured list of detected security findings and credential hygiene status.",
            agent=auditor,
        )

        risk_task = Task(
            description=(
                "Evaluate systemic blast radius, API quota boundaries, and recursive looping risks for {topic}. "
                "Provide quantitative risk metrics and SLA impact assessments."
            ),
            expected_output="A quantitative risk assessment matrix with latency and token economics impact.",
            agent=risk_evaluator,
        )

        remediation_task = Task(
            description=(
                "Develop an executive remediation roadmap and formal governance scorecard for {topic} "
                "incorporating findings from both the auditor and risk evaluator."
            ),
            expected_output=(
                "An executive-grade Markdown governance scorecard with prioritized remediation steps and an overall fleet readiness grade."
            ),
            agent=remediation_officer,
        )

        return Crew(
            agents=[auditor, risk_evaluator, remediation_officer],
            tasks=[audit_task, risk_task, remediation_task],
            process=Process.sequential,
            verbose=True,
        )
