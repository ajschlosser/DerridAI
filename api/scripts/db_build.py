
import re
import json

def generate_citation_strings(doc) -> tuple[str, str]:
    author = doc.get("document_author", doc.get("speaker", ""))
    work = doc.get("work", "")
    edition = doc.get("edition", "")
    year = doc.get("year", "")
    page_start = doc.get("page_start")
    translator = doc.get("translator", "")
    page_end = doc.get("page_end", "")
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

print("Starting...")
found = 0
not_found = 0
with open("../data/base/derrida7_ids.jsonl") as f, open("../data/base/derrida9_new_primary_en.jsonl", "w") as out:
    for i, line in enumerate(f):

        #r = re.sub(r"\s+", "", line.strip())

        d = json.loads(line.strip())

        inline, full = generate_citation_strings(d)
        d["inline_citation"] = inline
        d["full_citation"] = full
        d["text_length"] = len(d.get("text", ""))

        # Skip the record
        if len(d.get("text", "")) < 300 or d.get("extraction_quality", 0.0) < 0.8 or (d.get("speaker") != "Jacques Derrida" and d.get("region_author") != "Jacques Derrida" and d.get("position_holder") != "Jacques Derrida") or d.get("region_type") != "main_text" or d.get("primary_text") != True or d.get("discourse_role") in ["citation", "footnote", "endnote", "commentary", "bibliography"] or d.get("document_language") not in [["en_us"], ["en_gb"]]:
            print(d.get("region_type"), d["record_id"])
            not_found += 1
            continue

        # Keep the record
        else:
            #print("*",d["record_id"])
            found += 1
            out.write(json.dumps(d) + "\n")

print("Done.")#
print("Found:", found)
print("Not found:", not_found)