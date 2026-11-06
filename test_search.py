from research_tools import search_papers

papers = search_papers(
    topic="Generative AI in Healthcare",
    number=5,
    start_year=2020
)

for paper in papers:
    print("\nTitle:", paper["title"])
    print("Authors:", paper["authors"])
    print("Year:", paper["year"])
    print("DOI:", paper["doi"])
    print("Source:", paper["source"])