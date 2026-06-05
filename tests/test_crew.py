"""Smoke test: build the crew and verify it loads 7 agents and 7 tasks."""

from research_and_blog_crew.crew import ResearchAndBlogCrew


def test_crew_loads_with_seven_agents_and_seven_tasks():
    crew = ResearchAndBlogCrew().crew()
    assert len(crew.agents) == 7, f"expected 7 agents, got {len(crew.agents)}"
    assert len(crew.tasks) == 7, f"expected 7 tasks, got {len(crew.tasks)}"


def test_crew_uses_sequential_process():
    from crewai import Process
    crew = ResearchAndBlogCrew().crew()
    assert crew.process == Process.sequential
