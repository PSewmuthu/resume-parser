'''
Helpers for splitting section text into per-entry blocks
'''

import re
from src.helpers.text_cleaner import clean_line
from src.helpers.patterns import (
    INLINE_DATE_TITLE_RE,
    PROJECT_HEADER_RE,
    _TECH_LINE_LOOKAHEAD,
    _AWARD_KEYWORDS_RE,
    _CERT_KEYWORDS_RE
)


def _split_experience_blocks(text: str) -> list:
    """
    Split experience text into per-job blocks.
    Supports:
    1. Client: … style (consulting resumes)
    2. Inline-date style: "Job Title     Aug 2023 – Apr 2024"
    3. Fallback: blank-line boundaries
    """

    lines = text.splitlines()

    # Check if this uses Client: labels
    has_client = any(re.match(r"^Client\s*:", clean_line(l),
                              re.IGNORECASE) for l in lines)

    if has_client:
        blocks, buf = [], []
        for line in lines:
            if re.match(r"^Client\s*:", clean_line(line), re.IGNORECASE) and buf:
                blocks.append("\n".join(buf))
                buf = []
            buf.append(line)

        if buf:
            blocks.append("\n".join(buf))

        return blocks

    # Inline-date style: split whenever a line matches "Title     Date"
    blocks, buf = [], []
    for line in lines:
        cl = clean_line(line)

        if INLINE_DATE_TITLE_RE.match(cl) and buf:
            blocks.append("\n".join(buf))
            buf = []
        buf.append(line)
    if buf:
        blocks.append("\n".join(buf))

    if len(blocks) > 1:
        return blocks

    # Fallback: double blank line split
    return [b.strip() for b in re.split(r"\n{2,}", text.strip()) if b.strip()]


def _split_project_blocks(text: str) -> list:
    """
    Split project section into per-project blocks.
    Supports two formats:
    Format A: "Project Name | Date"  (pipe + date on title line)
    Format B: "Project Name\nTechnologies: ..."  (title then tech on next line)
    Also discards social link / URL lines before the first project.
    """
    lines = text.splitlines()
    blocks = []
    buf = []
    in_project = False

    def _is_project_title(cl: str, next_cl: str) -> bool:
        """True if cl looks like a project title line."""

        if PROJECT_HEADER_RE.match(cl):
            return True

        # Format B: title line if the NEXT line starts with "Technologies:"
        if next_cl and _TECH_LINE_LOOKAHEAD.match(next_cl):
            # Must not be a technologies line itself, a bullet, or a URL
            if not _TECH_LINE_LOOKAHEAD.match(cl) and not re.match(r"^[•·\-–*>]", cl):
                if not re.search(r"https?://", cl) and len(cl) > 4:
                    return True
        return False

    for idx, line in enumerate(lines):
        cl = clean_line(line)
        next_cl = clean_line(lines[idx + 1]) if idx + 1 < len(lines) else ""

        if _is_project_title(cl, next_cl):
            if buf and in_project:
                blocks.append("\n".join(buf))

            buf = [line]
            in_project = True
        elif in_project:
            buf.append(line)
        # else: skip content before first project (social links, etc.)

    if buf and in_project:
        blocks.append("\n".join(buf))

    return blocks


def _is_cert_like(text: str) -> bool:
    """Return True if an award line looks more like a certification (not a true award)."""

    if _AWARD_KEYWORDS_RE.search(text):
        return False   # Strong award signal overrides cert keywords

    return bool(_CERT_KEYWORDS_RE.search(text))
