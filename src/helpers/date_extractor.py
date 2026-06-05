'''
Helpers for date extraction and normalization
'''

import re
from dateutil import parser as date_parser
from src.helpers.patterns import DATE_RANGE_RE, SINGLE_DATE_RE, YEAR_RE


def parse_date(text: str) -> str:
    try:
        return date_parser.parse(text, fuzzy=True).strftime("%Y-%m")
    except Exception:
        return text.strip()


def _extract_date_range(block: str) -> dict:
    m = DATE_RANGE_RE.search(block)

    if m:
        start = parse_date(m.group("start")) if m.group("start") else None

        end_raw = m.group("end").strip().lower()
        end = end_raw if re.match(
            r"^(present|current|now|ongoing|till\s+date|to\s+date)$", end_raw
        ) else parse_date(end_raw)

        return {"start_date": start, "end_date": end}

    # Single month+year (no range)
    sm = SINGLE_DATE_RE.search(block)
    if sm:
        return {"start_date": parse_date(sm.group(0)), "end_date": None}

    years = YEAR_RE.findall(block)
    if len(years) >= 2:
        return {"start_date": years[0], "end_date": years[1]}

    if len(years) == 1:
        return {"start_date": years[0], "end_date": None}

    return {"start_date": None, "end_date": None}


def _split_entries(text: str) -> list:
    """Generic multi-entry splitter (education, certs, etc.)."""

    blocks = re.split(r"\n{2,}", text.strip())
    result = []

    for block in blocks:
        sub = re.split(r"(?=\n.{0,100}\b(?:19|20)\d{2}\b)", block)
        result.extend([b.strip() for b in sub if b.strip()])

    return result
