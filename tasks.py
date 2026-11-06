
from crewai import Task

from agents import (
    discovery_agent,
    summarization_agent,
    literature_agent,
    gap_agent,
    report_agent
)

# Task 1
discovery_task = Task(
    description="""
    Analyze the following research papers about {topic}.

    Paper Data:
    {papers_data}

    Organize the genuine papers with title, authors, year,
    DOI and source URL.

    Never invent paper details or references.
    """,
    expected_output="Verified and organized research paper details.",
    agent=discovery_agent
)

# Task 2
summary_task = Task(
    description="""
    Summarize each paper using only the supplied abstracts
    and metadata about {topic}.

    Explain objectives, methods and findings only when
    supported by the available information.

    Clearly mention when an abstract is unavailable.
    """,
    expected_output="Individual summaries of all available papers.",
    agent=summarization_agent,
    context=[discovery_task]
)

# Task 3
literature_task = Task(
    description="""
    Prepare a literature review about {topic}.

    Compare common themes, research methods, findings
    and differences across the supplied papers.
    Do not assume information that is not provided.
    """,
    expected_output="Comparative literature review.",
    agent=literature_agent,
    context=[discovery_task, summary_task]
)

# Task 4
gap_task = Task(
    description="""
    Identify possible research gaps in {topic}.

    Use only limitations and evidence present in the
    supplied papers and summaries.

    Separate explicitly reported limitations from
    your own suggested research opportunities.
    """,
    expected_output="Evidence-supported gaps and future directions.",
    agent=gap_agent,
    context=[summary_task, literature_task]
)

# Task 5
report_task = Task(
    description="""
        Prepare a complete academic research paper about {topic}, centered on
        the researcher's focus: {research_focus}.

        Output every section below as a Markdown level-two heading, exactly as
        written and in this exact order. Do not omit, combine, rename, or reorder
        sections. Write substantive content beneath every heading. If information
        is unavailable, keep the heading and explicitly state that the supplied
        sources do not provide enough evidence.

        ## 1. Research Title
        ## 2. Abstract
        ## 3. Keywords
        ## 4. Introduction
        ## 5. Research Problem
        ## 6. Research Objectives
        ## 7. Research Questions
        ## 8. Literature Review
        ## 9. Research Gap
        ## 10. Proposed Methodology
        ## 11. Results and Analysis
        ## 12. Discussion
        ## 13. Research Contributions
        ## 14. Limitations
        ## 15. Future Scope
        ## 16. Conclusion
        ## 17. References

        Evidence and integrity requirements:
                - Stay on the specified topic and research focus. If the supplied papers
                    are off-topic, disclose that and limit conclusions to relevant evidence;
                    do not change the subject of the paper.
        - Use only the supplied paper metadata, abstracts, and preceding task analyses.
        - Synthesize findings reported by the supplied papers in Results and Analysis;
            do not claim that this project conducted experiments or produced new data.
            State when the supplied evidence is insufficient.
        - Present Proposed Methodology as a proposal for future research, not as work
            already conducted.
        - Distinguish reported limitations from your own suggested research directions.
                - Use numbered in-text citations such as [1] that correspond to the supplied
                    Paper 1, Paper 2, and so on. Do not introduce outside author-year citations.
                - Cite only supplied works. Preserve their exact titles, authors, years, DOIs,
                    venues, and source URLs; never invent citations or references.
        - Keep the abstract consistent with the paper and include 4-6 keywords.
                - Before finishing, verify that all 17 headings appear exactly once and
                    that each section contains relevant content or an evidence limitation.
    """,
        expected_output=(
                "An evidence-grounded academic research paper containing all 17 required "
                "sections in the specified order."
        ),
    agent=report_agent,
    context=[
        discovery_task,
        summary_task,
        literature_task,
        gap_task
    ]
)

print("All 5 Tasks configured successfully!")
