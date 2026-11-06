
from crewai import Crew, Process


from agents import (
    discovery_agent,
    summarization_agent,
    literature_agent,
    gap_agent,
    report_agent
)

from tasks import (
    discovery_task,
    summary_task,
    literature_task,
    gap_task,
    report_task
)

# Create Crew
research_crew = Crew(
    agents=[
        discovery_agent,
        summarization_agent,
        literature_agent,
        gap_agent,
        report_agent
    ],

    tasks=[
        discovery_task,
        summary_task,
        literature_task,
        gap_task,
        report_task
    ],





    process=Process.sequential,
    verbose=True
)

print("Crew created successfully!")
