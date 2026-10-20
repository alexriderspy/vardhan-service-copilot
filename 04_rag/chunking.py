"""Split each Markdown document into one chunk per `## heading`.

Why by heading? Manuals are already organised by topic ("Troubleshooting:
low pressure"), so a section is a natural, self-contained answer, and the
heading gives us a clean citation: (document, section).
"""

from pathlib import Path


def chunk_markdown(path: Path) -> list[dict]:
    lines = path.read_text().splitlines()
    title = lines[0].lstrip("# ").strip()            # first line is "# Document title"
    chunks, section, body = [], None, []

    def flush():
        if section and body:
            text = "\n".join(body).strip()
            chunks.append({
                "id": f"{path.stem}#{section.lower().replace(' ', '-').replace(':', '')}",
                "doc": title, "section": section, "source_file": path.name,
                # Put the title + heading inside the text too, so the embedding knows the context.
                "text": f"{title} > {section}\n{text}",
            })

    for line in lines[1:]:
        if line.startswith("## "):
            flush()
            section, body = line[3:].strip(), []
        else:
            body.append(line)
    flush()
    return chunks
