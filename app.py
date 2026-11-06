
import streamlit as st
from datetime import date
import hashlib
from io import BytesIO
from pathlib import Path
import re
import requests
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from agents import llm
from crew import research_crew
from research_tools import search_papers

REPORT_SECTION_TITLES = (
    "Research Title",
    "Abstract",
    "Keywords",
    "Introduction",
    "Research Problem",
    "Research Objectives",
    "Research Questions",
    "Literature Review",
    "Research Gap",
    "Proposed Methodology",
    "Results and Analysis",
    "Discussion",
    "Research Contributions",
    "Limitations",
    "Future Scope",
    "Conclusion",
    "References",
)


# Page configuration
st.set_page_config(
    page_title="CrewAI Research Assistant",
    page_icon="R",
    layout="wide"
)

st.markdown(
    """
    <style>
    :root {
        --ink: #20342f;
        --muted: #65756f;
        --forest: #1d6251;
        --copper: #b65c42;
        --line: #dce5df;
    }
    .stApp {
        background: linear-gradient(135deg, #f7f9f6 0%, #edf3ef 100%);
        color: var(--ink);
    }
    [data-testid="stSidebar"] {
        background: #e9f0eb;
        border-right: 1px solid var(--line);
    }
    h1, h2, h3 {
        color: var(--ink);
        font-family: Georgia, "Times New Roman", serif;
        letter-spacing: 0;
    }
    .eyebrow {
        color: var(--copper);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .stButton > button, .stFormSubmitButton > button {
        background: var(--forest);
        border: 1px solid var(--forest);
        border-radius: 4px;
        color: white;
        min-height: 2.8rem;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background: #174f42;
        border-color: #174f42;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="eyebrow">Literature workbench</div>', unsafe_allow_html=True)
st.title("CrewAI Research Assistant")
st.caption("Evidence-led academic research and literature synthesis")

st.divider()

# Research topic input

with st.sidebar:
    st.markdown("### Research brief")
    with st.form("research_form"):
        topic = st.text_input(
            "Research topic",
            placeholder="Generative AI in healthcare",
        )

        research_focus = st.text_area(
            "Research focus",
            placeholder="Patient outcomes, clinical safety, implementation...",
            height=110,
        )

        paper_count = st.slider("Maximum papers", 1, 8, 3)
        start_year = st.number_input(
            "Published from",
            min_value=2000,
            max_value=date.today().year,
            value=2020,
            step=1,
        )
        submitted = st.form_submit_button(
            "Generate report",
            use_container_width=True,
        )


def format_papers(papers):
    return "\n\n".join(
        "\n".join(
            (
                f"Paper {index}",
                f"Title: {paper.get('title') or 'Title unavailable'}",
                f"Authors: {paper.get('authors') or 'Authors unavailable'}",
                f"Year: {paper.get('year') or 'Year unavailable'}",
                f"Venue: {paper.get('venue') or 'Not available'}",
                f"Publication type: {paper.get('type') or 'Not available'}",
                f"Citation count: {paper.get('citation_count') if paper.get('citation_count') is not None else 'Not available'}",
                f"Keywords: {', '.join(paper.get('keywords') or []) or 'Not available'}",
                f"Open-access status: {paper.get('open_access_status') or 'Not available'}",
                f"DOI: {paper.get('doi') or 'Not available'}",
                f"Abstract: {paper.get('abstract') or 'Abstract not available'}",
                f"Source: {paper.get('source') or 'Not available'}",
            )
        )
        for index, paper in enumerate(papers, start=1)
    )


def missing_report_sections(report):
    def normalize_heading(heading):
        heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
        heading = re.sub(r"^\d+[.)]\s*", "", heading)
        return " ".join(heading.split()).strip().casefold()

    headings = {
        normalize_heading(match.group(1))
        for match in re.finditer(r"(?m)^\s*#{1,3}\s+(.+?)\s*#*\s*$", report)
    }
    return [
        title for title in REPORT_SECTION_TITLES
        if title.casefold() not in headings
    ]


def build_references(papers):
    references = []
    for index, paper in enumerate(papers, start=1):
        authors = paper.get("authors") or "Authors unavailable"
        year = paper.get("year") or "Year unavailable"
        title = paper.get("title") or "Title unavailable"
        venue = paper.get("venue") or "Publication venue unavailable"
        doi = paper.get("doi") or "DOI unavailable"
        source = paper.get("source") or "Source URL unavailable"
        references.append(
            f"[{index}] {authors} ({year}). {title}. {venue}. DOI: {doi}. Source: {source}."
        )
    return references


def replace_references_section(report, papers):
    lines = report.splitlines()
    reference_index = None

    for index, line in enumerate(lines):
        heading = re.match(r"^\s*#{1,3}\s+(.+?)\s*#*\s*$", line)
        if not heading:
            continue
        normalized = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading.group(1))
        normalized = re.sub(r"^\d+[.)]\s*", "", normalized).strip().casefold()
        if normalized == "references":
            reference_index = index
            break

    reference_lines = ["## 17. References", *build_references(papers)]
    if reference_index is None:
        return report.rstrip() + "\n\n" + "\n\n".join(reference_lines)

    next_section = next(
        (
            index
            for index in range(reference_index + 1, len(lines))
            if re.match(r"^\s*#{1,3}\s+", lines[index])
        ),
        len(lines),
    )
    return "\n".join(
        lines[:reference_index] + reference_lines + lines[next_section:]
    )


def insert_before_references(report, additional_sections):
    lines = report.splitlines()
    reference_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(r"^\s*#{1,3}\s+", line)
            and normalize_report_heading(line) == "references"
        ),
        None,
    )
    addition_lines = additional_sections.strip().splitlines()

    if reference_index is None:
        return report.rstrip() + "\n\n" + "\n".join(addition_lines)

    return "\n".join(
        lines[:reference_index] + addition_lines + [""] + lines[reference_index:]
    )


def normalize_report_heading(line):
    heading = re.sub(r"^\s*#{1,3}\s+", "", line)
    heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    heading = re.sub(r"^\d+[.)]\s*", "", heading)
    return " ".join(heading.split()).strip().casefold()


def generate_missing_sections(report, missing_sections, papers, topic, research_focus):
    source_papers = []
    for paper in papers:
        source_paper = dict(paper)
        abstract = source_paper.get("abstract") or ""
        source_paper["abstract"] = abstract[:1000]
        source_papers.append(source_paper)

    requested_headings = "\n".join(
        f"## {REPORT_SECTION_TITLES.index(section) + 1}. {section}"
        for section in missing_sections
    )
    prompt = f"""Complete only the missing sections of this academic research paper.
Stay strictly on the topic and focus below. Output every requested heading exactly
as written, with substantive content under each, and do not repeat completed sections.

Topic: {topic}
Research focus: {research_focus}

Required missing headings:
{requested_headings}

Evidence sources:
{format_papers(source_papers)}

Existing report context (use it for continuity, do not repeat it):
{report[:5000]}

Use only the supplied sources. Cite them as numbered references like [1]. Do not
invent data, study findings, or citations. In Results and Analysis, synthesize only
reported evidence and state if evidence is insufficient. Present methodology as a
proposal, not as research already performed. If information is unavailable, state
that explicitly under the requested heading."""

    completion = llm.call(
        [
            {
                "role": "system",
                "content": "You complete evidence-grounded academic research papers accurately.",
            },
            {"role": "user", "content": prompt},
        ]
    )
    if not isinstance(completion, str) or not completion.strip():
        raise ValueError("The model returned no missing-section content.")
    return completion.strip()


def generate_research_report(papers, topic, research_focus):
    result = research_crew.kickoff(
        inputs={
            "topic": topic,
            "papers_data": format_papers(papers),
            "research_focus": research_focus,
        }
    )
    report = getattr(result, "raw", None) or str(result)
    report = replace_references_section(report, papers)
    st.session_state["research_report"] = report
    st.session_state.pop("report_is_source_only", None)
    st.session_state.pop("research_report_pdf", None)

    missing_sections = missing_report_sections(report)
    if missing_sections:
        st.session_state["missing_report_sections"] = missing_sections
    else:
        st.session_state.pop("missing_report_sections", None)
    return report, missing_sections


def build_source_only_report(topic, research_focus, papers):
    years = [paper.get("year") for paper in papers if paper.get("year")]
    venues = sorted({paper.get("venue") for paper in papers if paper.get("venue")})
    keywords = list(dict.fromkeys(
        keyword
        for paper in papers
        for keyword in paper.get("keywords", [])
        if keyword
    ))[:8]
    source_notes = []

    for index, paper in enumerate(papers, start=1):
        abstract = " ".join((paper.get("abstract") or "Abstract unavailable.").split())
        source_notes.extend(
            [
                f"### Source {index}: {paper.get('title') or 'Title unavailable'}",
                f"Authors: {paper.get('authors') or 'Unavailable'}; "
                f"year: {paper.get('year') or 'Unavailable'}; "
                f"venue: {paper.get('venue') or 'Unavailable'}.",
                f"Abstract supplied by the index: {abstract}",
            ]
        )

    year_range = f"{min(years)}-{max(years)}" if years else "unavailable"
    venue_summary = ", ".join(venues) if venues else "not supplied by the index"
    keyword_summary = ", ".join(keywords) if keywords else f"{topic}, {research_focus}"

    report = f"""## 1. Research Title
Source-Based Research Draft: {topic}

## 2. Abstract
This source-only draft organizes {len(papers)} records retrieved for the topic “{topic}” and research focus “{research_focus}.” The records span {year_range}. The Groq report-generation request was blocked by its daily token limit, so this document contains retrieved metadata and abstracts only; it is not an AI-generated literature synthesis and makes no verified research findings.

## 3. Keywords
{keyword_summary}

## 4. Introduction
This draft collects indexed scholarly records related to {topic}, with attention to {research_focus}. It provides a starting bibliography and the abstracts returned by the source index. Relevance and claims should be checked against each original publication.

## 5. Research Problem
The current run could not complete its planned evidence synthesis because the configured language-model service reached its daily token limit. The retrieved records alone are insufficient to establish the state of the field or support substantive conclusions.

## 6. Research Objectives
- Organize the {len(papers)} retrieved records and their available bibliographic information.
- Preserve source abstracts and links for direct verification.
- Identify the work needed to complete a full, evidence-grounded review.

## 7. Research Questions
1. Which retrieved publications are directly relevant to {topic} and {research_focus}?
2. What methods and findings do those publications report in their full text?
3. What evidence gaps remain after a verified review of the relevant publications?

## 8. Literature Review
The following is a source inventory, not a synthesized literature review. Abstract text is reproduced from the retrieved index and should be checked against the publisher or repository record.

{"\n\n".join(source_notes)}

## 9. Research Gap
A defensible research gap cannot be established from metadata and abstracts alone in this run. The records require relevance screening and full-text comparison before any gap claim can be made.

## 10. Proposed Methodology
For the full review, screen the retrieved records for relevance; verify each publication and its full text; extract study design, population, methods, outcomes, and limitations; compare evidence using a documented synthesis method; and record exclusions and uncertainty. This is a proposed process, not work already conducted.

## 11. Results and Analysis
No new experiment or formal analysis was conducted. Descriptive retrieval details only: {len(papers)} records; publication-year range {year_range}; venues returned by the index: {venue_summary}. These counts describe the search output, not the research field as a whole.

## 12. Discussion
This output preserves the retrieved source information but does not compare the studies or evaluate their findings. Any interpretation should wait until the publications are verified and their full texts are reviewed.

## 13. Research Contributions
This fallback provides an organized, traceable starting set of records and identifies the additional screening and synthesis needed. It does not claim a new scientific contribution.

## 14. Limitations
- The configured Groq model could not generate the planned synthesis because its daily token limit was reached.
- The draft relies on metadata and abstracts returned by the index, not verified full texts.
- The search results may omit relevant publications or include records outside the intended scope.
- No comparative analysis, quality appraisal, or independent validation was performed.

## 15. Future Scope
After the provider quota resets, retry full report generation from the saved papers. Then verify source relevance, review full texts, synthesize methods and results, appraise limitations, and revise the research gap and conclusions accordingly.

## 16. Conclusion
The current run produced a source-only draft for {topic}, not a completed research paper. Its records and abstracts are available for inspection, but substantive conclusions require a verified literature synthesis.
"""
    return replace_references_section(report, papers)


def groq_rate_limit_message(error):
    details = str(error)
    lowered_details = details.lower()
    if "rate_limit_exceeded" not in lowered_details:
        return None

    if "tokens per day" in lowered_details:
        quota_period = "daily token quota"
    elif "tokens per minute" in lowered_details:
        quota_period = "per-minute token quota"
    else:
        quota_period = "token quota"

    retry_match = re.search(r"try again in\s+([0-9hms.]+s)", details, re.IGNORECASE)
    retry_text = f" Retry in {retry_match.group(1)}." if retry_match else ""
    usage_match = re.search(
        r"Limit\s+([\d,]+),\s*Used\s+([\d,]+),\s*Requested\s+([\d,]+)",
        details,
        re.IGNORECASE,
    )
    usage_text = ""
    if usage_match:
        limit, used, requested = (
            int(value.replace(",", "")) for value in usage_match.groups()
        )
        usage_text = (
            f" The limit is {limit:,} tokens, {max(limit - used, 0):,} remain, "
            f"and this request needs {requested:,}."
        )

    return (
        f"Groq's {quota_period} has been reached.{usage_text}{retry_text} "
        "Your papers are saved. Use Retry report generation after the cooldown; "
        "it will not repeat the paper search."
    )


def report_to_pdf(report, topic, research_focus):
    buffer = BytesIO()
    page_width, _ = A4
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=topic,
        author="CrewAI Research Assistant",
    )
    base_styles = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "ResearchTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=25,
            textColor=colors.HexColor("#20342f"),
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "focus": ParagraphStyle(
            "ResearchFocus",
            parent=base_styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#65756f"),
            alignment=TA_CENTER,
            spaceAfter=20,
        ),
        "body": ParagraphStyle(
            "ResearchBody",
            parent=base_styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=7,
        ),
        "h1": ParagraphStyle(
            "ResearchHeading1",
            parent=base_styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#1d6251"),
            spaceBefore=12,
            spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "ResearchHeading2",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1d6251"),
            spaceBefore=9,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "ResearchHeading3",
            parent=base_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#20342f"),
            spaceBefore=7,
            spaceAfter=4,
        ),
    }

    def inline_markup(text):
        text = escape(text)
        text = re.sub(
            r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
            r'<link href="\2" color="#1d6251">\1</link>',
            text,
        )
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)

    story = [
        Paragraph(escape(topic), styles["title"]),
        Paragraph(
            f"<b>Research focus:</b> {escape(research_focus)}",
            styles["focus"],
        ),
    ]
    paragraph_lines = []

    def flush_paragraph():
        if paragraph_lines:
            story.append(
                Paragraph(inline_markup(" ".join(paragraph_lines)), styles["body"])
            )
            paragraph_lines.clear()

    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            style = styles[f"h{len(heading.group(1))}"]
            story.append(Paragraph(inline_markup(heading.group(2)), style))
        elif re.match(r"^[-*+]\s+", line):
            flush_paragraph()
            item = re.sub(r"^[-*+]\s+", "", line)
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{inline_markup(item)}", styles["body"]))
        else:
            paragraph_lines.append(line)

    flush_paragraph()

    def draw_page_number(canvas, _document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dce5df"))
        canvas.line(22 * mm, 15 * mm, page_width - 22 * mm, 15 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#65756f"))
        canvas.drawRightString(page_width - 22 * mm, 10 * mm, f"Page {_document.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=draw_page_number, onLaterPages=draw_page_number)
    return buffer.getvalue()


if submitted:
    if not topic.strip():
        st.sidebar.warning("Enter a research topic to continue.")
    elif not research_focus.strip():
        st.sidebar.warning("Enter a research focus to continue.")
    else:
        st.session_state.pop("research_report", None)
        st.session_state.pop("research_report_pdf", None)
        st.session_state.pop("research_papers", None)
        st.session_state.pop("missing_report_sections", None)
        st.session_state.pop("report_is_source_only", None)

        with st.status("Searching scholarly sources...", expanded=True) as status:
            try:
                papers = search_papers(
                    topic=topic.strip(),
                    number=paper_count,
                    start_year=int(start_year),
                )
                if not papers:
                    status.update(label="No papers found", state="error")
                    st.warning("No matching papers were returned by the sources.")
                else:
                    st.session_state["research_papers"] = papers
                    st.session_state["research_topic"] = topic.strip()
                    st.session_state["research_focus"] = research_focus.strip()
                    status.write(f"Found {len(papers)} papers. Preparing the analysis...")
                    report, missing_sections = generate_research_report(
                        papers,
                        topic.strip(),
                        research_focus.strip(),
                    )
                    if missing_sections:
                        status.update(
                            label="Draft ready for completion",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        report_pdf = report_to_pdf(
                            report,
                            topic.strip(),
                            research_focus.strip(),
                        )
                        report_path = Path("reports") / "research_report.pdf"
                        report_path.parent.mkdir(exist_ok=True)
                        report_path.write_bytes(report_pdf)
                        st.session_state["research_report_pdf"] = report_pdf
                        status.update(
                            label="Complete research report ready",
                            state="complete",
                            expanded=False,
                        )
            except Exception as error:
                quota_message = groq_rate_limit_message(error)
                saved_papers = st.session_state.get("research_papers", [])
                if quota_message and saved_papers:
                    source_report = build_source_only_report(
                        st.session_state.get("research_topic", topic.strip()),
                        st.session_state.get("research_focus", research_focus.strip()),
                        saved_papers,
                    )
                    st.session_state["research_report"] = source_report
                    st.session_state["report_is_source_only"] = True
                    st.session_state["missing_report_sections"] = []
                    source_pdf = report_to_pdf(
                        source_report,
                        st.session_state["research_topic"],
                        st.session_state["research_focus"],
                    )
                    source_pdf_path = Path("reports") / "research_report_source_only.pdf"
                    source_pdf_path.parent.mkdir(exist_ok=True)
                    source_pdf_path.write_bytes(source_pdf)
                    st.session_state["research_report_pdf"] = source_pdf
                    status.update(
                        label="Source-only draft ready",
                        state="complete",
                        expanded=False,
                    )
                    st.info(quota_message)
                else:
                    status.update(
                        label="Groq quota reached" if quota_message else "Research run failed",
                        state="error",
                        expanded=False,
                    )
                    if quota_message:
                        st.warning(quota_message)
                    else:
                        st.error("The research run could not be completed.")
                        with st.expander("Technical details"):
                            st.code(str(error))


report = st.session_state.get("research_report")
papers = st.session_state.get("research_papers", [])

if report:
    source_only = st.session_state.get("report_is_source_only", False)
    report = replace_references_section(report, papers)
    st.session_state["research_report"] = report
    missing_sections = missing_report_sections(report)
    if missing_sections:
        st.session_state["missing_report_sections"] = missing_sections
        st.caption(
            "Sections to complete: " + ", ".join(missing_sections)
        )
    else:
        st.session_state.pop("missing_report_sections", None)
    if not st.session_state.get("research_report_pdf"):
        report_pdf = report_to_pdf(
            report,
            st.session_state.get("research_topic", "Research Paper"),
            st.session_state.get("research_focus", ""),
        )
        report_filename = "research_report_source_only.pdf" if source_only else (
            "research_report_draft.pdf" if missing_sections else "research_report.pdf"
        )
        report_path = Path("reports") / report_filename
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_bytes(report_pdf)
        st.session_state["research_report_pdf"] = report_pdf
    st.caption(
        f"{st.session_state.get('research_topic', '')} · "
        f"{len(papers)} sources · Focus: "
        f"{st.session_state.get('research_focus', '')}"
    )
    report_tab, sources_tab = st.tabs(["Research report", f"Sources ({len(papers)})"])

    with report_tab:
        if source_only:
            st.info(
                "This source-only draft uses retrieved records and abstracts. "
                "It has not been synthesized by the AI model. Retry the full report "
                "after the Groq quota cooldown."
            )
            if st.button("Retry full AI report", key="retry_full_ai_report"):
                retry_error = None
                with st.status("Generating the full report from saved papers...", expanded=True) as status:
                    try:
                        full_report, remaining_sections = generate_research_report(
                            papers,
                            st.session_state.get("research_topic", ""),
                            st.session_state.get("research_focus", ""),
                        )
                        if remaining_sections:
                            st.session_state["missing_report_sections"] = remaining_sections
                            status.update(
                                label="Draft ready for completion",
                                state="complete",
                                expanded=False,
                            )
                        else:
                            full_pdf = report_to_pdf(
                                full_report,
                                st.session_state.get("research_topic", "Research Paper"),
                                st.session_state.get("research_focus", ""),
                            )
                            full_pdf_path = Path("reports") / "research_report.pdf"
                            full_pdf_path.parent.mkdir(exist_ok=True)
                            full_pdf_path.write_bytes(full_pdf)
                            st.session_state["research_report_pdf"] = full_pdf
                            status.update(
                                label="Complete research report ready",
                                state="complete",
                                expanded=False,
                            )
                    except Exception as error:
                        retry_error = error
                        retry_quota_message = groq_rate_limit_message(error)
                        status.update(
                            label="Groq quota reached" if retry_quota_message else "Report retry failed",
                            state="error",
                            expanded=False,
                        )

                if retry_error:
                    if retry_quota_message:
                        st.info(retry_quota_message)
                    else:
                        st.error("The full report could not be generated.")
                        with st.expander("Technical details"):
                            st.code(str(retry_error))
                else:
                    st.rerun()

        if missing_sections and papers:
            if st.button(
                f"Generate {len(missing_sections)} missing sections",
                key="generate_missing_report_sections",
            ):
                try:
                    with st.spinner("Generating only the missing sections..."):
                        continuation = generate_missing_sections(
                            report,
                            missing_sections,
                            papers,
                            st.session_state.get("research_topic", ""),
                            st.session_state.get("research_focus", ""),
                        )
                        updated_report = insert_before_references(report, continuation)
                        updated_report = replace_references_section(updated_report, papers)
                        st.session_state["research_report"] = updated_report
                        st.session_state.pop("research_report_pdf", None)
                        updated_missing = missing_report_sections(updated_report)
                        if updated_missing:
                            st.session_state["missing_report_sections"] = updated_missing
                        else:
                            st.session_state.pop("missing_report_sections", None)
                    st.rerun()
                except Exception as error:
                    st.error("Could not generate the missing sections.")
                    with st.expander("Technical details"):
                        st.exception(error)

        st.markdown(report)
        report_pdf = st.session_state.get("research_report_pdf")
        if report_pdf:
            st.download_button(
                "Download source-only draft PDF" if source_only else (
                    "Download draft PDF" if missing_sections else "Download report PDF"
                ),
                data=report_pdf,
                file_name=(
                    "research_report_source_only.pdf" if source_only else (
                        "research_report_draft.pdf"
                        if missing_sections
                        else "research_report.pdf"
                    )
                ),
                mime="application/pdf",
            )

    with sources_tab:
        for index, paper in enumerate(papers, start=1):
            st.markdown(f"**{index}. {paper.get('title') or 'Untitled paper'}**")
            details = " · ".join(
                str(value)
                for value in (
                    paper.get("authors"),
                    paper.get("year"),
                    paper.get("venue"),
                    paper.get("type"),
                    paper.get("doi"),
                )
                if value
            )
            if details:
                st.caption(details)
            citation_count = paper.get("citation_count")
            if citation_count is not None:
                st.caption(f"Citations: {citation_count}")
            keywords = paper.get("keywords") or []
            if keywords:
                st.caption("Keywords: " + ", ".join(keywords))
            if paper.get("open_access_status"):
                st.caption(f"Access: {paper['open_access_status']}")
            source = paper.get("source") or ""
            if source.startswith("http"):
                st.link_button("Open publication", source, key=f"source_{index}")

            pdf_url = paper.get("pdf_url")
            if pdf_url:
                st.caption("Open-access PDF")
                st.link_button("Open PDF", pdf_url, key=f"open_pdf_{index}")
                download_key = "pdf_download_" + hashlib.sha256(
                    pdf_url.encode("utf-8")
                ).hexdigest()[:16]

                if st.button("Prepare PDF download", key=f"prepare_pdf_{index}"):
                    try:
                        if not pdf_url.startswith("https://"):
                            raise ValueError("PDF links must use HTTPS.")
                        response = requests.get(pdf_url, timeout=(10, 60))
                        response.raise_for_status()
                        if not response.content.startswith(b"%PDF-"):
                            raise ValueError("The source did not return a valid PDF.")
                        st.session_state[download_key] = response.content
                    except (requests.RequestException, ValueError):
                        st.error("Could not retrieve this PDF. Try opening the source link.")

                pdf_data = st.session_state.get(download_key)
                if pdf_data:
                    filename = re.sub(
                        r"[^A-Za-z0-9._-]+", "_", paper.get("title") or "research_paper"
                    ).strip("._")[:100] or f"research_paper_{index}"
                    st.download_button(
                        "Download PDF",
                        data=pdf_data,
                        file_name=f"{filename}.pdf",
                        mime="application/pdf",
                        key=f"download_pdf_{index}",
                    )
            else:
                st.caption("No open-access PDF link was provided. Open the publication page to check access.")

            abstract = paper.get("abstract")
            if abstract and abstract != "Abstract not available":
                with st.expander("Abstract"):
                    st.write(abstract)
            st.divider()
else:
    st.markdown("### Your research brief will appear here")
    if papers:
        st.info("Your retrieved papers are saved. Retry the report without searching again.")
        if st.button("Retry report generation", key="retry_research_report"):
            retry_error = None
            with st.status("Retrying report generation from saved papers...", expanded=True) as status:
                try:
                    _, missing_sections = generate_research_report(
                        papers,
                        st.session_state.get("research_topic", ""),
                        st.session_state.get("research_focus", ""),
                    )
                    status.update(
                        label=(
                            "Draft ready for completion"
                            if missing_sections
                            else "Complete research report ready"
                        ),
                        state="complete",
                        expanded=False,
                    )
                except Exception as error:
                    retry_error = error
                    quota_message = groq_rate_limit_message(error)
                    status.update(
                        label="Groq quota reached" if quota_message else "Report retry failed",
                        state="error",
                        expanded=False,
                    )

            if retry_error:
                if quota_message:
                    st.warning(quota_message)
                else:
                    st.error("The report could not be generated.")
                    with st.expander("Technical details"):
                        st.code(str(retry_error))
            else:
                st.rerun()

st.divider()
st.caption("CrewAI · Groq · OpenAlex / Crossref")
