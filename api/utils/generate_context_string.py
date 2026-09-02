from langchain_core.documents import Document
from .generate_citation_strings import generate_citation_strings


def generate_context_string(docs: list[Document]) -> str:
    context_str = ""
    for i, doc in enumerate(docs):
        doc.metadata["inline_citation"], doc.metadata["full_citation"] = generate_citation_strings(doc)
        d = doc.metadata
        processor_note = d.get("processor_note", None)
        discourse_role = d.get("discourse_role", "general text")
        holder = d.get("position_holder", "")
        speaker = d.get("speaker", "")
        work = d.get("work", "")
        stance = d.get("stance")
        topics = d.get("topics", [])
        concepts = d.get("concepts", [])
        text = " ".join(d.get("text", "").split())
        context_str += f"""\n<BEGIN EVIDENCE_TAG E{i}>
evidence_tag=[E{i}]
record_id={d.get("record_id")}
work={work}
speaker={"Derrida" if speaker == "Jacques Derrida" else speaker}
position_holder={holder}{f"\nstance={stance}" if stance else ""}
position_status={d.get("proposition_status", "")}
target={d.get("target", "")}
role={discourse_role}{f"\ntopics={', '.join(topics)}" if topics else ""}{f"\nconcepts={', '.join(concepts)}" if concepts else ""}
text={text}{f"\nnote_for_llms_processing_this_data={processor_note}" if processor_note else ""}
<END EVIDENCE_TAG E{i}>\n"""
    cleaned_context_str = " ".join(context_str.split())
    return cleaned_context_str