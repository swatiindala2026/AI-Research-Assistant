
import html
import logging
import os
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)

_http_session = requests.Session()
_http_session.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3,
            status=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
    ),
)


def get_abstract(inverted_index):
    if not inverted_index:
        return "Abstract not available"

    words = {}

    for word, positions in inverted_index.items():
        for position in positions:
            words[position] = word

    return " ".join(
        words[i] for i in sorted(words)
    )


def _openalex_pdf_url(paper):
    locations = [
        paper.get("best_oa_location"),
        paper.get("primary_location"),
        *(paper.get("locations") or []),
    ]
    for location in locations:
        if (
            isinstance(location, dict)
            and location.get("is_oa")
            and location.get("pdf_url")
        ):
            return location["pdf_url"]
    return None


def _search_crossref(topic, number, start_year):
    params = {
        "query.bibliographic": topic,
        "filter": f"from-pub-date:{start_year}-01-01,until-pub-date:2026-12-31",
        "rows": number,
    }
    contact_email = os.getenv("CROSSREF_MAILTO")
    if contact_email:
        params["mailto"] = contact_email

    response = _http_session.get(
        "https://api.crossref.org/works",
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    works = response.json().get("message", {}).get("items", [])
    papers = []

    for work in works:
        date_parts = next(
            (
                work.get(date_field, {}).get("date-parts")
                for date_field in ("published-online", "published-print", "issued")
                if work.get(date_field, {}).get("date-parts")
            ),
            [],
        )
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        doi = work.get("DOI")
        has_creative_commons_license = any(
            "creativecommons.org/licenses/" in license_info.get("URL", "").lower()
            for license_info in work.get("license", [])
        )
        pdf_url = next(
            (
                link.get("URL")
                for link in work.get("link", [])
                if has_creative_commons_license
                and link.get("content-type", "").lower() == "application/pdf"
                and link.get("URL")
            ),
            None,
        )
        abstract = html.unescape(re.sub(r"<[^>]*>", " ", work.get("abstract") or ""))
        abstract = " ".join(abstract.split()) or "Abstract not available"
        authors = []

        for author in work.get("author", []):
            name = " ".join(
                part for part in (author.get("given"), author.get("family")) if part
            ) or author.get("name")
            if name:
                authors.append(name)

        papers.append({
            "title": next(iter(work.get("title") or []), None),
            "authors": ", ".join(authors),
            "year": year,
            "venue": ", ".join(work.get("container-title") or []),
            "type": work.get("type"),
            "citation_count": work.get("is-referenced-by-count"),
            "keywords": (work.get("subject") or [])[:8],
            "open_access_status": "Creative Commons license" if has_creative_commons_license else "Not specified",
            "doi": doi,
            "abstract": abstract,
            "source": f"https://doi.org/{doi}" if doi else work.get("URL"),
            "pdf_url": pdf_url,
        })

    return papers


def search_papers(topic, number=5, start_year=2020):

    url = "https://api.openalex.org/works"

    params = {
        "search": topic,
        "filter": f"publication_year:{start_year}-2026",
        "per-page": number
    }

    response = _http_session.get(
        url,
        params=params,
        timeout=30
    )

    try:
        response.raise_for_status()
    except requests.HTTPError:
        if response.status_code not in {429, 500, 502, 503, 504}:
            raise
        logger.warning(
            "OpenAlex returned HTTP %s after retries; falling back to Crossref.",
            response.status_code,
        )
        return _search_crossref(topic, number, start_year)

    papers = response.json().get("results", [])

    output = []

    for paper in papers:

        authors = [
            item["author"]["display_name"]
            for item in paper.get("authorships", [])
        ]
        primary_location = paper.get("primary_location") or {}
        source_metadata = primary_location.get("source") or {}
        open_access = paper.get("open_access") or {}
        keywords = [
            keyword.get("display_name")
            for keyword in paper.get("keywords", [])
            if keyword.get("display_name")
        ][:8]

        output.append({
            "title": paper.get("title"),
            "authors": ", ".join(authors),
            "year": paper.get("publication_year"),
            "venue": source_metadata.get("display_name"),
            "type": paper.get("type"),
            "citation_count": paper.get("cited_by_count"),
            "keywords": keywords,
            "open_access_status": open_access.get("oa_status") or ("Open access" if open_access.get("is_oa") else "Not specified"),
            "doi": paper.get("doi"),
            "abstract": get_abstract(
                paper.get("abstract_inverted_index")
            ),
            "source": (
                primary_location.get("landing_page_url")
            ) or paper.get("doi") or paper.get("id"),
            "pdf_url": _openalex_pdf_url(paper),
        })

    return output
