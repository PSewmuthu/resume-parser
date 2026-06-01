'''
Helpers for text cleaning and normalization
'''

import re
from collections import OrderedDict
from src.helpers.patterns import _OCR_CAP_PAIRS, _STOP


def strip_markdown(text: str) -> str:
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'_{2,}', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text


def clean_line(line: str) -> str:
    """Strip markdown, normalise internal whitespace (including mid-word spaces from OCR/PDF)."""
    line = strip_markdown(line)
    # Collapse tabs to spaces, then multiple spaces to one
    line = line.replace('\t', ' ')
    line = re.sub(r' {2,}', ' ', line)
    return line.strip()


def deduplicate_text(text: str) -> str:
    """
    Remove duplicate paragraph blocks that appear due to PyPDF2 double-accumulation.
    Strategy: split on double-newlines, keep each unique paragraph in first-seen order.
    """
    paragraphs = re.split(r'\n{2,}', text.strip())
    seen = OrderedDict()
    for p in paragraphs:
        key = re.sub(r'\s+', ' ', p.strip())
        if key and key not in seen:
            seen[key] = p
    return '\n\n'.join(seen.values())


def clean(text: str) -> str:
    text = deduplicate_text(text)

    # Known multi-token OCR artifact fixes
    # These handle cases where suffix rules conflict with stopword exclusions
    text = text.replace('ranslat or', 'ranslator')
    text = text.replace('ranslat or', 'ranslator')  # duplicate safety

    # PyPDF2 OCR space artifact normalisation
    # Hyphen-space: "real -time" → "real-time"
    text = re.sub(r'(\w) -(\w)', r'\1-\2', text)

    # Hyphen-newline: "AI -\npowered" → "AI-powered"
    text = re.sub(r' -\n', '-', text)

    # Single letter preceded by a letter/hyphen
    # "Full-S tack" → "Full-Stack", "Pre-D ev" → "Pre-Dev"
    text = re.sub(r'(?<=[a-z\-])([A-Z]) ([a-z]{2,})\b', r'\1\2', text)

    def _join_cap_pair(m):
        pair = (m.group(1), m.group(2))

        # Also check without trailing 's'
        if pair in _OCR_CAP_PAIRS or (m.group(1), m.group(2).rstrip('s')) in _OCR_CAP_PAIRS:
            return m.group(1) + m.group(2)
        return m.group(0)
    text = re.sub(r'\b([A-Z]) ([A-Za-z]{2,})\b', _join_cap_pair, text)

    # Acronym space: "RA G" → "RAG", "MV T" → "MVT"
    text = re.sub(r'\b([A-Z]{2,}) ([A-Z])\b', r'\1\2', text)

    def _join_frag(m):
        return m.group(0) if m.group(2).lower() in _STOP else m.group(1) + m.group(2)

    text = re.sub(r'(\w{3,}) ([a-z]{2,3})\b', _join_frag, text)
    # Common longer suffix fragments
    text = re.sub(
        r'(\w{2,}) (ing|tion|ment|ence|ance|ern|ogy|ate|ive|ous|ary'
        r'|elop(?:er|ment|ing)?|ranslat(?:or|ion|ing)?|lassif(?:y|ier|ied)?)\b',
        r'\1\2', text
    )

    # Join list-continuation lines (line ending with & or ,)
    text = re.sub(r'([&,])\n([a-zA-Z])', r'\1 \2', text)

    # General whitespace cleanup
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
