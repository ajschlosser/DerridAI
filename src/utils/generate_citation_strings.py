
from langchain_core.documents import Document

def generate_citation_strings(doc: Document) -> tuple[str, str]:
    author = doc.metadata.get("document_author", doc.metadata.get("speaker", ""))
    work = doc.metadata.get("work", "")
    edition = doc.metadata.get("edition", "")
    year = doc.metadata.get("year", "")
    page_start = doc.metadata.get("page_start")
    translator = doc.metadata.get("translator", "")
    page_end = doc.metadata.get("page_end", "")
    author_last_name = author.split(' ')[-1]
    inline_author = author_last_name
    author_name_reversed = f"{author.split(' ')[-1]}, {author.split(' ')[0]}"
    if page_start is None:
        pages_cited = ""
    elif page_end is None or page_end == page_start:
        pages_cited = str(page_start)
    else:
        pages_cited = f"{page_start}-{page_end}"
    inline_citation = f"{inline_author} {year}{': ' + pages_cited if pages_cited else ''}"
    full_citation = f"{author_name_reversed}. {work}.{f' {translator} trans.' if translator else ''} {edition}. {year}"
    return inline_citation, full_citation