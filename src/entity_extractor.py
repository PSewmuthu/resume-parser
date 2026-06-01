'''
Extracts structured entities from raw resume text using spaCy NLP and regex patterns.
'''

import os
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add root to sys.path for helper imports
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

import re
import spacy
from collections import defaultdict
from dateutil import parser as date_parser
from src.helpers.text_cleaner import clean_line, strip_markdown, clean
from src.helpers.date_extractor import _extract_date_range, _split_entries
from src.helpers.link_extractor import extract_link_markers, _match_project_githubs
from src.helpers.block_extractor import _split_experience_blocks, _split_project_blocks, _is_cert_like
from src.helpers.patterns import (
    _SUBLABEL_RE,
    _SECTION_RE_MAP,
    SECTION_PATTERNS,
    EMAIL_RE,
    PHONE_RE,
    TITLE_WORDS_RE,
    NAME_RE,
    LINKEDIN_RE,
    GITHUB_RE,
    TWITTER_RE,
    KAGGLE_RE,
    HUGGINGFACE_RE,
    PORTFOLIO_RE,
    GENERIC_URL_RE,
    ADDRESS_RE,
    DATE_RANGE_RE,
    CLIENT_LINE_RE,
    ROLE_LINE_RE,
    ENV_LINE_RE,
    RR_RE,
    INLINE_DATE_TITLE_RE,
    BULLET_RE,
    GPA_RE,
    DEGREE_RE,
    YEAR_RE,
    PROJECT_HEADER_RE,
    TECH_LINE_RE
)


class EntityExtractor:
    def __init__(self, raw_text):
        self.raw_text = raw_text

        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_lg")
        except OSError:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                raise RuntimeError(
                    "No spaCy English model found. Run: python -m spacy download en_core_web_sm")

    def detect_section(self, raw_line: str):
        """Return section key if this cleaned line is a standalone section header."""

        cleaned = clean_line(raw_line).rstrip(':').strip()

        # Never treat sub-labels as section headers
        if _SUBLABEL_RE.match(cleaned + ':'):
            return None

        for key, rx in _SECTION_RE_MAP.items():
            if rx.match(cleaned):
                return key

        return None

    def split_into_sections(self, text: str) -> dict:
        """
        Split raw text into labelled sections.
        - Handles inline content after a header keyword
        """

        lines = text.splitlines()
        sections = defaultdict(list)
        current = "header"

        for line in lines:
            cl = clean_line(line)

            # Never let sub-labels ("Technologies: ...") hijack section
            if _SUBLABEL_RE.match(cl):
                sections[current].append(line)
                continue

            section_key = self.detect_section(line)
            if section_key:
                current = section_key
                # Carry inline content after the header word
                remainder = re.sub(
                    rf"^(?:{SECTION_PATTERNS[section_key]})[:\s]*",
                    '', cl.rstrip(':').strip(),
                    flags=re.IGNORECASE,
                ).strip()
                if remainder:
                    sections[current].append(remainder)
            else:
                sections[current].append(line)

        return {k: "\n".join(v) for k, v in sections.items()}

    def extract_name(self, text: str) -> str:
        """
        Extract candidate name from the first lines.
        Handles:
        - Multi-line names
        - PyPDF2 injected spaces ("Engineer ing" should be skipped)
        - Single-word last-name continuation lines
        """

        lines = [clean_line(l)
                 for l in text.splitlines() if clean_line(l)][:20]

        # Try joining consecutive non-contact short lines (max 2 lines for name)
        for i, line in enumerate(lines[:8]):
            if EMAIL_RE.search(line) or PHONE_RE.search(line):
                continue

            if TITLE_WORDS_RE.search(line):
                continue

            if re.search(r'https?://', line):
                continue

            if len(line) > 60:
                continue

            candidate = line
            # If next line looks like a name continuation (short, title-case or all-caps, no URL)
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if (len(nxt) < 30 and not TITLE_WORDS_RE.search(nxt)
                        and not EMAIL_RE.search(nxt) and not re.search(r'https?://', nxt)
                        and re.match(r'^[A-Z][A-Za-z\s\-\'\.]+$', nxt)):
                    candidate = candidate + ' ' + nxt

            # Validate: must have at least 2 word-like tokens
            tokens = candidate.split()
            if len(tokens) >= 2 and NAME_RE.match(candidate):
                return candidate.title()

        # spaCy fallback
        doc = self.nlp(strip_markdown(text[:800]))
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()

        return ""

    def extract_contacts(self, text: str) -> dict:
        contacts = {}
        plain = strip_markdown(text)

        # Label-based email: "Email: addr@example.com" - stop at non-email chars
        label_email_m = re.search(
            r"(?:email|e-mail)[:\s]+([\w.+\-]+@[\w\-]+(?:\.[\w\-]+){1,4})",
            plain, re.IGNORECASE,
        )

        # Also search for plain email in FIRST 500 chars (header area), before references
        header_text = plain[:800]
        header_email = EMAIL_RE.search(header_text)

        def _clean_email(raw_em):
            """Extract clean email from a string that may have trailing garbage.
            Matches known TLDs to stop at the real domain boundary."""

            # Try known TLD patterns first
            clean = re.search(
                r"[\w.+\-]+@[\w\-]+(?:\.(?:com|org|net|edu|gov|io|lk|uk|in|au|ca|de|fr|sg|my|bd|nz|co))+",
                raw_em, re.IGNORECASE,
            )
            if clean:
                return clean.group(0)

            # Fallback: take up to the first non-email boundary character
            m = re.match(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+", raw_em)
            if m:
                # Strip trailing word-chars that look like concatenated text (CamelCase after TLD)
                email = m.group(0)
                email = re.sub(
                    r"\.[a-z]{2,6}[A-Z]\w*$", lambda x: x.group(0)[:x.group(0).rindex(".")], email)
                return email

            return raw_em

        if header_email:
            # Prefer email found in document header (first 800 chars) — most likely candidate email
            contacts["email"] = _clean_email(header_email.group(0))
        elif label_email_m:
            contacts["email"] = _clean_email(label_email_m.group(1))

        # Prefer phone from document header (first 800 chars) over label-based (avoids refs section)
        header_phone = PHONE_RE.search(plain[:800])
        label_phone = re.search(
            r"(?:phone|tel|mobile|mob|cell)[:\s]+([+\d][\d\s\-().]{6,}[\d])", plain, re.IGNORECASE)
        phone_src = header_phone.group(0) if header_phone else (
            label_phone.group(1) if label_phone else None)

        if phone_src:
            raw_phone = re.sub(r"[^\d+\-() ]", "", phone_src).strip()
            if len(re.sub(r"\D", "", raw_phone)) >= 7:
                contacts["phone"] = raw_phone

        m = LINKEDIN_RE.search(plain)
        if m:
            url = m.group(0)
            contacts["linkedin"] = url if url.startswith(
                "http") else "https://" + url

        m = GITHUB_RE.search(plain)
        if m:
            url = m.group(0)
            contacts["github"] = url if url.startswith(
                "http") else "https://" + url

        m = TWITTER_RE.search(plain)
        if m:
            url = m.group(0)
            contacts["twitter"] = url if url.startswith(
                "http") else "https://" + url

        m = KAGGLE_RE.search(plain)
        if m:
            url = m.group(0)
            contacts["kaggle"] = url if url.startswith(
                "http") else "https://" + url

        m = HUGGINGFACE_RE.search(plain)
        if m:
            url = m.group(0)
            contacts["huggingface"] = url if url.startswith(
                "http") else "https://" + url

        # Portfolio / website
        m = PORTFOLIO_RE.search(plain)
        if m:
            contacts["website"] = m.group(1)
        else:
            # Fallback: first https URL that's not a social platform
            for url in GENERIC_URL_RE.findall(plain):
                if not any(p in url for p in ['linkedin', 'github', 'twitter', 'kaggle', 'huggingface']):
                    contacts.setdefault("website", url)
                    break

        # Address: look for explicit "Address:" label first
        m = ADDRESS_RE.search(plain)
        if m:
            addr = m.group(1).strip().rstrip('.')
            if addr and not re.match(r"^[\d\s\-]+$", addr):
                contacts["address"] = addr
        else:
            # Fallback: city/country pattern not inside a pipe-table
            for line in plain.splitlines():
                cl = line.strip()
                if (re.search(r"\b[A-Z][a-z]+(?:,\s+[A-Z][a-z]+)*,?\s+(?:Sri Lanka|India|USA|USA|UK|Australia|Canada|Germany|France|Singapore|Malaysia|Pakistan|Bangladesh|Nepal)\b", cl, re.IGNORECASE)
                        and not DATE_RANGE_RE.search(cl)
                        and not cl.startswith("|")
                        and not re.search(r"\buniversity\b|\bcollege\b|\bschool\b|\binstitute\b", cl, re.IGNORECASE)):
                    contacts.setdefault("address", cl)
                    break

        return contacts

    def extract_summary(self, sections: dict) -> str:
        raw = sections.get("summary", "")
        lines = [re.sub(r"^[-•·\s]+", "", l).strip() for l in raw.splitlines()]

        return clean("\n".join(lines))

    def parse_skills_table(self, text: str) -> list:
        """Parse pipe-delimited tables AND bullet/comma lists. Returns flat list."""

        skills = []
        seen = set()

        def add(s):
            s = re.sub(r'[\[\]()"\']', '', s).strip()
            s = re.sub(r'^[\d.\s\-–*•]+|[\d.\s\-–*•]+$', '', s).strip()

            # Skip URLs and lines that look like section headers
            if re.search(r'https?://', s):
                return
            if 2 <= len(s) <= 80 and s.lower() not in seen:
                seen.add(s.lower())
                skills.append(s)

        for line in text.splitlines():
            cl = clean_line(line)
            if not cl or cl == '•':
                continue

            # Skip sub-label lines ("Technical Skills:", etc.)
            if re.match(r"^technical\s+skills?\s*:?\s*$", cl, re.IGNORECASE):
                continue

            if '|' in cl:
                parts = [p.strip() for p in cl.split(
                    '|') if p.strip() and p.strip() != '---']
                if not parts:
                    continue

                add(parts[0])
                if len(parts) > 1:
                    for v in re.split(r'[,;]+', parts[1]):
                        add(v.strip())
            else:
                # Strip leading bullet
                cl = re.sub(r'^[•·\-–*>\s]+', '', cl).strip()
                if not cl:
                    continue

                # Handle "Category (sub1, sub2, sub3)" pattern
                paren_match = re.match(r"^(.+?)\s*\((.+)\)\s*$", cl)
                if paren_match:
                    category = paren_match.group(1).strip()
                    subs = paren_match.group(2).strip()
                    add(category)
                    for sub in re.split(r"[,;]+", subs):
                        add(sub.strip())
                elif ',' in cl and len(cl) > 40:
                    for token in re.split(r"[,;]+", cl):
                        add(token.strip())
                else:
                    add(cl)

        return skills

    def extract_skills(self, sections: dict) -> list:
        skills_text = sections.get("skills", "")
        if skills_text.strip():
            return self.parse_skills_table(skills_text)

        return []

    def extract_experience(self, sections: dict) -> list:
        text = sections.get("experience", "")
        if not text:
            return []

        entries = []
        for block in _split_experience_blocks(text):
            if len(block.strip()) < 15:
                continue

            entry = {
                "title": "", "company": "", "location": "",
                "start_date": None, "end_date": None,
                "description": "", "responsibilities": [], "tech_stack": [],
            }

            lines = [clean_line(l) for l in block.splitlines()]
            resp_parts = []
            in_resp = False

            for line in lines:
                if not line:
                    continue

                # Client: line
                cm = CLIENT_LINE_RE.match(line)
                if cm:
                    raw = cm.group(1).strip()
                    dr = _extract_date_range(raw)
                    entry["start_date"] = dr["start_date"]
                    entry["end_date"] = dr["end_date"]
                    raw = DATE_RANGE_RE.sub("", raw).strip().strip(',')
                    parts = [p.strip() for p in raw.split(',')]
                    entry["company"] = parts[0]
                    entry["location"] = ", ".join(
                        parts[1:]).strip() if len(parts) > 1 else ""
                    continue

                # Role: line
                rm = ROLE_LINE_RE.match(line)
                if rm:
                    entry["title"] = rm.group(1).strip()
                    continue

                # Environment / tech stack
                if ENV_LINE_RE.match(line):
                    tech_raw = re.sub(r"^Environment\s*:\s*", "",
                                      line, flags=re.IGNORECASE)
                    entry["tech_stack"] = [t.strip()
                                           for t in re.split(r"[,;]+", tech_raw) if t.strip()]
                    continue

                # Roles & Responsibilities header
                if RR_RE.match(line):
                    in_resp = True
                    continue

                # Inline date title
                itm = INLINE_DATE_TITLE_RE.match(line)
                if itm:
                    entry["title"] = itm.group("title").strip()
                    dr = _extract_date_range(itm.group("dates"))
                    entry["start_date"] = dr["start_date"]
                    entry["end_date"] = dr["end_date"]
                    continue

                # Bullet responsibility
                if BULLET_RE.match(line):
                    in_resp = True
                    resp_parts.append(BULLET_RE.sub("", line).strip())
                    continue

                # Plain sentence
                if in_resp and len(line) > 10:
                    resp_parts.append(line)
                elif entry["title"] and not entry["company"] and len(line) < 80 and not BULLET_RE.match(line):
                    # Line right after title line is likely the company name
                    entry["company"] = line
                elif not entry["company"] and not entry["title"] and len(line) < 60:
                    entry["company"] = line
                elif entry["title"] and entry["company"] and len(line) > 15:
                    # Plain prose description (no bullet, not in resp block)
                    resp_parts.append(line)

            # Separate plain-prose descriptions from bullet responsibilities
            bullet_resps = [r for r in resp_parts if re.match(r"^[•·\-–*>]", r) or
                            (len(r) > 20 and r[0].isupper() and not r.endswith(':'))]
            entry["responsibilities"] = bullet_resps if bullet_resps else resp_parts

            if not entry["description"] and resp_parts:
                entry["description"] = " ".join(resp_parts)

            if entry["title"] or entry["company"]:
                entries.append(entry)

        return entries

    def extract_education(self, sections: dict) -> list:
        text = sections.get("education", "")
        if not text.strip():
            return []

        entries = []
        for block in _split_entries(text):
            if len(block) < 5:
                continue

            entry = {}
            block_lines = [clean_line(l)
                           for l in block.splitlines() if clean_line(l)]
            entry.update(_extract_date_range(block))
            gpa = GPA_RE.search(block)

            if gpa:
                entry["grade"] = gpa.group(1).strip()

            lines_nd = [l for l in block_lines if not re.fullmatch(
                r"[\d\-\u2013/,\s]+", l)]

            # Extract institution from date line
            institution_from_date_line = ""
            for bl in block_lines:
                dr_match = DATE_RANGE_RE.search(bl)
                if dr_match:
                    remainder = bl[dr_match.end():].strip()
                    if remainder and len(remainder) > 3:
                        institution_from_date_line = remainder
                    break

            degree_line, institution_line = "", ""
            for i, l in enumerate(lines_nd):
                if DEGREE_RE.search(l):
                    degree_line = l
                    institution_line = institution_from_date_line or (
                        lines_nd[i + 1] if i + 1 < len(lines_nd) else "")
                    break
            if not degree_line and lines_nd:
                degree_line = lines_nd[0]
                institution_line = institution_from_date_line or (
                    lines_nd[1] if len(lines_nd) > 1 else "")

            # Strip trailing date range from degree line if present
            degree_clean = DATE_RANGE_RE.sub(
                "", degree_line).strip().rstrip(",;").strip()
            # Also strip standalone year
            degree_clean = YEAR_RE.sub(
                "", degree_clean).strip().rstrip(",;–-").strip()
            parts = re.split(r"\s+(?:in|of)\s+", degree_clean,
                             maxsplit=1, flags=re.IGNORECASE)

            entry["degree"] = parts[0].strip()
            entry["field"] = parts[1].strip() if len(parts) > 1 else ""
            entry["institution"] = institution_line

            # Deduplicate entries (same degree+institution)
            key = (entry.get("degree", ""), entry.get("institution", ""))
            if not any((e.get("degree"), e.get("institution")) == key for e in entries):
                entries.append(entry)

        return entries

    def extract_certifications(self, sections: dict) -> list:
        """
        Parse certifications in two common formats:
        Format A (bullet):  • Cert Name (Year) / • Cert Name - Issuer
        Format B (2-line):  Cert Name YEAR\nIssuer
        """
        raw_lines = [
            re.sub(r"^[•·\-–*>\s]+", "", clean_line(l)).strip()
            for l in sections.get("certifications", "").splitlines()
        ]
        raw_lines = [l for l in raw_lines if l]

        certs = []
        seen = set()
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            years = YEAR_RE.findall(line)

            if years:
                # This line has a year → it's a cert name+year line
                year = years[-1]
                name = re.sub(r"\b(?:19|20)\d{2}\b",
                              "", line).strip(" ,|-").strip()
                cert = {"name": name, "year": year}

                # Next line (if short and no year) is the issuer
                if i + 1 < len(raw_lines):
                    nxt = raw_lines[i + 1]
                    if not YEAR_RE.findall(nxt) and len(nxt) < 80:
                        cert["issuer"] = nxt
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
            else:
                # No year on this line
                cert = {"name": line}

                # Check if next line has a year (name then year on separate line)
                if i + 1 < len(raw_lines) and YEAR_RE.findall(raw_lines[i + 1]):
                    year_line = raw_lines[i + 1]
                    cert["year"] = YEAR_RE.findall(year_line)[-1]
                    cert["issuer"] = re.sub(
                        r"\b(?:19|20)\d{2}\b", "", year_line).strip()
                    i += 2
                else:
                    i += 1

            # Dedup key = name + issuer (same cert from different issuers is distinct)
            key = (cert.get("name", "") + "|" + cert.get("issuer", "")).lower()
            if key and key not in seen:
                seen.add(key)
                certs.append(cert)

        return certs

    def extract_projects(self, sections: dict) -> list:
        text = sections.get("projects", "")
        if not text:
            return []

        projects = []
        seen_names = set()

        for block in _split_project_blocks(text):
            lines = [clean_line(l)
                     for l in block.splitlines() if clean_line(l)]
            if not lines:
                continue

            entry = {}

            # First line is always "Name | Date"
            hm = PROJECT_HEADER_RE.match(lines[0])
            if hm:
                entry["name"] = hm.group("name").strip()
                entry.update(_extract_date_range(hm.group("dates")))
            else:
                entry["name"] = lines[0]
                entry.update(_extract_date_range(lines[0]))

            # Strip trailing "View Project" hyperlink text (PDF anchor text artifact)
            entry["name"] = re.sub(r"\s*View\s+Project\s*$",
                                   "", entry["name"], flags=re.IGNORECASE).strip()

            # Deduplicate by name
            if entry["name"] in seen_names:
                continue
            seen_names.add(entry["name"])

            # Technologies line
            entry["technologies"] = []
            desc_lines = []
            github_url = ""

            for line in lines[1:]:
                tm = TECH_LINE_RE.match(line)
                if tm:
                    entry["technologies"] = [
                        t.strip() for t in re.split(r"[,;/]+", tm.group(1)) if t.strip()
                    ]
                    continue

                if re.match(r"^GitHub\s*:", line, re.IGNORECASE):
                    github_url = re.sub(r"^GitHub\s*:\s*", "",
                                        line, flags=re.IGNORECASE).strip()
                    continue

                bullet_stripped = re.sub(r"^[•·\-–*>\s]+", "", line).strip()
                if bullet_stripped and not re.search(r"https?://", bullet_stripped):
                    desc_lines.append(bullet_stripped)

            # Strip page-separator artifacts like "| | | |" from description
            desc_text = " ".join(desc_lines)
            desc_text = re.sub(r'(?:\s*\|\s*){2,}', ' ', desc_text).strip()
            entry["description"] = desc_text
            if github_url:
                entry["github"] = github_url

            projects.append(entry)

        return projects

    def extract_awards(self, sections: dict) -> list:
        text = sections.get("awards", "")
        items = []
        seen = set()
        buf = ""

        for line in text.splitlines():
            line = re.sub(r"^[•·\-–*>\s]+", "", clean_line(line)).strip()
            if not line:
                if buf:
                    if buf.lower() not in seen:
                        seen.add(buf.lower())
                        items.append(buf)
                    buf = ""
                continue

            # Continuation line starts with "(" or is very short (year fragment)
            if line.startswith("(") and buf:
                buf = buf + " " + line
            elif buf:
                if buf.lower() not in seen:
                    seen.add(buf.lower())
                    items.append(buf)
                buf = line
            else:
                buf = line

        if buf and buf.lower() not in seen:
            items.append(buf)

        return items

    def split_awards_and_certs(self, sections: dict) -> tuple:
        """
        For sections (like ACHIEVEMENTS) that mix awards and certs,
        split into (awards_list, certs_list).
        Returns (awards, certifications) where each item is a string.
        """

        raw_awards = self.extract_awards(sections)
        true_awards = []
        extracted_certs = []

        for item in raw_awards:
            if _is_cert_like(item):
                # Parse as cert: extract year and name
                years = YEAR_RE.findall(item)
                cert = {"name": item}

                if years:
                    cert["year"] = years[-1]
                    # name without year and trailing punctuation
                    cert["name"] = re.sub(
                        r"\b(?:19|20)\d{2}\b", "", item).strip(" ,()|-")
                extracted_certs.append(cert)
            else:
                true_awards.append(item)

        return true_awards, extracted_certs

    def extract_publications(self, sections: dict) -> list:
        return [
            re.sub(r"^[•·\-–*>\s]+", "", clean_line(l)).strip()
            for l in sections.get("publications", "").splitlines()
            if clean_line(l) and len(clean_line(l)) > 3
        ]

    def extract_languages(self, sections: dict) -> list:
        items = []
        for line in sections.get("languages", "").splitlines():
            line = re.sub(r"^[•·\-–*>\s]+", "", clean_line(line)).strip()

            for part in re.split(r"[,|]", line):
                part = part.strip()
                if part:
                    items.append(part)

        return items

    def extract_interests(self, sections: dict) -> list:
        raw = re.split(r"[,|•·\n/\\]+", sections.get("interests", ""))

        return [r.strip() for r in raw if r.strip() and len(r.strip()) > 1]

    def extract_references(self, sections: dict) -> list:
        text = sections.get("references", "")
        if not text.strip():
            return []

        if re.search(r"available\s+on\s+request|upon\s+request", text, re.IGNORECASE):
            return [{"note": "Available on request"}]

        # Split on bullet points OR blank-line-separated blocks
        if re.search(r"^[•·]", text.strip(), re.MULTILINE):
            blocks = re.split(r"(?=^[•·]\s)", text, flags=re.MULTILINE)
        else:
            # No bullets: split on blank lines OR on lines that look like a new person's name
            blocks = re.split(r"\n{2,}", text.strip())
            if len(blocks) == 1:
                # Try splitting on "Professor|Dr|Mr|Miss|Ms|Mrs" at line start
                blocks = re.split(
                    r"(?=^(?:Professor|Dr\.?|Mr\.?|Miss|Ms\.?|Mrs\.?)\s)", text.strip(), flags=re.MULTILINE)

        refs = []
        for block in blocks:
            lines = [re.sub(r"^[•·\-–\s]+", "", clean_line(l)).strip()
                     for l in block.splitlines() if clean_line(l)]
            lines = [l for l in lines if l]
            if not lines:
                continue

            ref = {"name": lines[0]}
            for l in lines[1:]:
                em = EMAIL_RE.search(l)
                ph = PHONE_RE.search(l)

                if re.match(r"^(?:tel|phone|mob)\s*:", l, re.IGNORECASE) and ph:
                    ref["phone"] = ph.group(0)
                elif re.match(r"^email\s*:", l, re.IGNORECASE) and em:
                    ref["email"] = em.group(0)
                elif em:
                    ref["email"] = em.group(0)
                elif ph:
                    ref["phone"] = ph.group(0)
                else:
                    ref.setdefault("title_company", l)

            refs.append(ref)

        return refs

    def extract_entities(self, raw_text: str = None) -> dict:
        """Given raw resume text, return a fully structured dict."""

        if raw_text is None:
            raw_text = self.raw_text

        # Extract annotation-layer links injected by text_extractor, get clean text
        link_data = extract_link_markers(raw_text)
        clean_source = link_data.get('cleaned_text', raw_text)

        text = clean(clean_source)
        sections = self.split_into_sections(text)

        # Build all fields
        contacts = self.extract_contacts(text)

        # Enrich contacts with annotation-layer links (override regex if annotation available)
        if link_data.get('linkedin'):
            contacts['linkedin'] = link_data['linkedin']

        if link_data.get('portfolio'):
            contacts['website'] = link_data['portfolio']

        if link_data.get('github'):
            contacts['github'] = link_data['github']

        if link_data.get('kaggle'):
            contacts['kaggle'] = link_data['kaggle']

        if link_data.get('huggingface'):
            contacts['huggingface'] = link_data['huggingface']

        # Extract projects then attach GitHub links from annotation layer
        projects = self.extract_projects(sections)
        projects = _match_project_githubs(
            projects, link_data.get('project_githubs', []))

        # Smart awards/certs split: sections with ACHIEVEMENTS mix both
        raw_certs = self.extract_certifications(sections)
        awards_list, cert_list_from_awards = self.split_awards_and_certs(
            sections)

        # Prefer explicit certifications section; fall back to those parsed from achievements
        final_certs = raw_certs if raw_certs else cert_list_from_awards

        # If certs were split from achievements, awards_list is already filtered
        final_awards = awards_list if not raw_certs and cert_list_from_awards else self.extract_awards(
            sections)

        return {
            "name":           self.extract_name(text),
            "contacts":       contacts,
            "summary":        self.extract_summary(sections),
            "skills":         self.extract_skills(sections),
            "experience":     self.extract_experience(sections),
            "education":      self.extract_education(sections),
            "certifications": final_certs,
            "projects":       projects,
            "awards":         final_awards,
            "publications":   self.extract_publications(sections),
            "languages":      self.extract_languages(sections),
            "interests":      self.extract_interests(sections),
            "references":     self.extract_references(sections),
        }


if __name__ == "__main__":
    # For testing purposes, we can randomly select a file from the raw_resumes directory
    
    import json
    import random
    from text_extractor import TextExtractor
    
    raw_resumes_dir = os.path.join(parent_dir, 'data', 'raw_resumes')

    files = [f for f in os.listdir(raw_resumes_dir) if os.path.isfile(
        os.path.join(raw_resumes_dir, f))]

    if not files:
        raise ValueError("No files found in the data/raw_resumes directory.")

    random_file = random.choice(files)
    file_path = os.path.join(raw_resumes_dir, random_file)

    print(f"Extracting text from: {file_path}\n")

    extractor = TextExtractor(file_path)
    text = extractor.extract()

    entity_extractor = EntityExtractor(text)
    extracted_entities = entity_extractor.extract_entities()

    with open("extracted_entities.json", "w") as f:
        json.dump(extracted_entities, f, indent=4)
