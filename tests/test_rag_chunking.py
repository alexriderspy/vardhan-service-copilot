from chunking import chunk_markdown

from common.config import CLIENT_DOCS


def test_one_chunk_per_heading_with_citation_fields():
    chunks = [c for p in sorted(CLIENT_DOCS.glob("*.md")) for c in chunk_markdown(p)]
    assert len(chunks) == 31
    assert len({c["id"] for c in chunks}) == len(chunks)
    warranty = [c for c in chunks if c["source_file"] == "warranty-policy.md"]
    assert {"Warranty period", "What is not covered", "Extended warranty"} <= {c["section"] for c in warranty}
    assert all(c["text"].startswith(c["doc"]) for c in chunks)
