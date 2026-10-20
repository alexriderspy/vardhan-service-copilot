"""Checking whether a fact appears in a text, forgiving about how dates are written."""

from datetime import date


def variants(fact: str) -> list[str]:
    """An ISO date can be written many ways in a reply. Accept all of them."""
    try:
        d = date.fromisoformat(fact)
    except ValueError:
        return [fact]
    day = str(d.day)
    return [fact, f"{day} {d:%B %Y}", f"{d:%B} {day}, {d:%Y}", f"{d:%B} {day} {d:%Y}", f"{day} {d:%b %Y}",
            f"{d:%b} {day}, {d:%Y}", f"{d:%d/%m/%Y}", f"{day}th {d:%B %Y}", f"{day}st {d:%B %Y}",
            f"{day}nd {d:%B %Y}", f"{day}rd {d:%B %Y}", f"{d:%A}, {day} {d:%B %Y}"]


def facts_found(must_include: list, text: str) -> list[bool]:
    """Each fact is a string or a list of acceptable alternatives."""
    text = text.lower()
    found = []
    for fact in must_include:
        options = fact if isinstance(fact, list) else [fact]
        found.append(any(v.lower() in text for option in options for v in variants(option)))
    return found
