'''
This module defines regex patterns for extracting various entities from resumes, such as names, emails, phone numbers, and more. These patterns are used by the EntityExtractor class to identify and extract relevant information from the raw text of resumes.
'''

import re

# PDF annotation link marker parsing
# text_extractor.py injects __LINK_* markers at the top of extracted PDF text
_LINK_MARKER_RE = re.compile(
    r"^__LINK_(?P<type>[^:]+):(?P<rest>.+)$",
    re.IGNORECASE,
)

# Known single-uppercase-letter splits (lookup table of safe joins)
_OCR_CAP_PAIRS = {
    ('A', 'ugmented'), ('A', 'pplication'),
    ('B', 'eyond'), ('B', 'uild'),
    ('C', 'CTV'), ('C', 'omplete'), ('C', 'omputer'), ('C', 'lassification'),
    ('D', 'eveloper'), ('D', 'eep'), ('D', 'ata'),
    ('E', 'xpert'), ('E', 'xperience'), ('E', 'ngineering'), ('E', 'rror'),
    ('F', 'aculty'), ('F', 'ull'), ('F', 'iverr'), ('F', 'ile'),
    ('G', 'eneration'), ('G', 'oogle'),
    ('I', 'ntern'), ('I', 'ntelligent'), ('I',
                                          'ntermediate'), ('I', 'nformation'),
    ('L', 'anguage'), ('L', 'earning'), ('L', 'inked'),
    ('M', 'achine'), ('M', 'anagement'),
    ('N', 'atural'), ('N', 'etwork'),
    ('O', 'perations'), ('O', 'perating'),
    ('P', 'rogramming'), ('P', 'owered'), ('P',
                                           'erformance'), ('P', 'roficiency'),
    ('R', 'andom'), ('R', 'etrieval'), ('R', 'ecognition'), ('R', 'esearch'),
    ('S', 'cience'), ('S', 'tack'), ('S', 'tatistics'), ('S', 'tudent'),
    ('S', 'craper'), ('S', 'ystem'), ('S',
                                      'ystems'), ('S', 'inghe'), ('S', 'ewmuthu'),
    ('T', 'echnology'), ('T', 'raining'), ('T', 'ranslat'),
    ('V', 'ersion'), ('V', 'ehicle'),
    ('W', 'eb'), ('W', 'ork'),
}

# Suffix fragments - join when clearly a word-internal split
#    Uses an exclusion list of standalone words that must NOT be joined
_STOP = {'in', 'of', 'at', 'on', 'to', 'by', 'or', 'as', 'an', 'is', 'it',
         'be', 'do', 'no', 'up', 'if', 'so', 'us', 'we', 'he', 'me', 'my',
         'its', 'the', 'and', 'for', 'but', 'not', 'all', 'are', 'was',
         'has', 'had', 'can', 'may', 'via', 'per', 'new', 'old', 'any',
         'our', 'out', 'use', 'web', 'api', 'csv', 'sql', 'css', 'mvt',
         'llm', 'rag', 'cnn', 'rnn'}

# Section header patterns
SECTION_PATTERNS = {
    "contact":        r"contact(?:\s+info(?:rmation)?)?|personal\s+info(?:rmation)?|personal\s+details|websites?\s+and\s+social\s+links?",
    "summary":        r"(?:professional\s+)?summary|(?:professional\s+)?profile|objective|about\s+me|career\s+(?:objective|goal|summary)",
    "skills":         r"(?:technical\s+)?skills?|competenc(?:ies|y)|proficienc(?:ies|y)|expertise|key\s+skills?",
    "experience":     r"(?:professional\s+|work\s+)?experience|employment(?:\s+history)?|work\s+history|career\s+history|positions?\s+held",
    "education":      r"education(?:al\s+background)?|academic(?:\s+background)?|qualifications?|degrees?|schooling",
    "certifications": r"certifications?|certificates?|accreditations?|licen[sc]es?|credentials?",
    "projects":       r"projects?|work\s+samples?",
    "awards":         r"awards?|honors?|honours?|achievements?|recognition|scholarships?|activities",
    "publications":   r"publications?|research(?:\s+papers?)?|papers?|journals?",
    "languages":      r"languages?\s*(?:spoken|known|proficiency)?|spoken\s+languages?|linguistic\s+(?:skills?|abilities?)",
    "interests":      r"interests?|hobbies?|volunteering|extracurricular",
    "references":     r"references?|referees?",
}

_SECTION_RE_MAP = {
    key: re.compile(rf"^(?:{pat})[:\s]*$", re.IGNORECASE)
    for key, pat in SECTION_PATTERNS.items()
}

# Sub-labels that appear *inside* a section and must NOT trigger a section split
_SUBLABEL_RE = re.compile(
    r"^(?:technologies|tech\s+stack|tools\s+used|environment|stack)[:\s]",
    re.IGNORECASE,
)

# Contact field regexes
EMAIL_RE = re.compile(r'[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+', re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(\+?[\d][\d\s\-().]{6,}[\d])(?!\d)")
LINKEDIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+", re.IGNORECASE)
GITHUB_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", re.IGNORECASE)
TWITTER_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[\w\-]+", re.IGNORECASE)
KAGGLE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?kaggle\.com/[\w\-]+", re.IGNORECASE)
HUGGINGFACE_RE = re.compile(
    r"(?:https?://)?huggingface\.co/[\w\-]+", re.IGNORECASE)
PORTFOLIO_RE = re.compile(
    r"(?:portfolio|website)[:\s]+(https?://[\w\-./~%?=&]+)", re.IGNORECASE)
GENERIC_URL_RE = re.compile(r"https?://[\w\-./~%?=&]+", re.IGNORECASE)

ADDRESS_RE = re.compile(
    r"(?:address\s*:\s*)(.+?)(?:\.|$)",
    re.IGNORECASE,
)

# Timeline patterns
DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|"
    r"Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar|Apr|Jun|Jul)?"
    r"[,\s]*\d{4})"
    r"\s*[-–—to/]+\s*"
    r"(?P<end>(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|"
    r"Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar|Apr|Jun|Jul)"
    r"[,\s]*\d{4}|present|current|now|ongoing|till\s+date|to\s+date)",
    re.IGNORECASE,
)

YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")

DEGREE_RE = re.compile(
    r"\b(b\.?s\.?c?\.?|b\.?a\.?|m\.?s\.?c?\.?|m\.?a\.?|m\.?b\.?a\.?|ph\.?d\.?|"
    r"bachelor(?:'?s)?|master(?:'?s)?|doctor(?:ate)?|associate|diploma|certificate|"
    r"hnd|hnc|a\.?level|o\.?level|llb|beng|meng|btech|mtech|bed|med)\b",
    re.IGNORECASE,
)

GPA_RE = re.compile(
    r"(?:gpa|grade|cgpa|score|percentage|marks?)[:\s]*([0-9.]+\s*(?:/\s*[0-9.]+)?%?)",
    re.IGNORECASE,
)

# Single-date pattern: "March 2026" or "August 2025"
SINGLE_DATE_RE = re.compile(
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}",
    re.IGNORECASE,
)

# Name patterns
TITLE_WORDS_RE = re.compile(
    r"\b(developer|engineer(?:ing)?|analyst|manager|designer|architect|consultant|"
    r"director|officer|lead|senior|sr\.|jr\.|junior|intern|specialist|"
    r"programmer|scientist|researcher|coordinator|administrator|full\s+stack|java|"
    r"web\s+scraper|freelanc)\b",
    re.IGNORECASE,
)

# Matches names
NAME_RE = re.compile(
    r"^([A-Z][A-Za-z'.'\-]*\.?\s+[A-Z][A-Za-z'.'\-\s]*[A-Za-z])$"
)

# Experience section patterns
INLINE_DATE_TITLE_RE = re.compile(
    r"^(?P<title>.+?)\s*(?P<dates>"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}\s*[-\u2013\u2014]\s*"
    r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}|present|current|ongoing)"
    r")\s*$",
    re.IGNORECASE,
)

# Client and role lines that appear inside experience sections
CLIENT_LINE_RE = re.compile(r"^Client\s*:\s*(.+)$", re.IGNORECASE)
ROLE_LINE_RE = re.compile(r"^Role\s*:\s*(.+)$", re.IGNORECASE)
ENV_LINE_RE = re.compile(r"^Environment\s*:", re.IGNORECASE)
BULLET_RE = re.compile(r"^[•·\-–*]\s+")
RR_RE = re.compile(r"^Roles?\s*[&and]+\s*Responsibilities?", re.IGNORECASE)

# Projects
PROJECT_HEADER_RE = re.compile(
    r"^(?P<name>.+?)\s*\|\s*"
    r"(?P<dates>(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[^|]+)$",
    re.IGNORECASE,
)

TECH_LINE_RE = re.compile(r"^Technologies?\s*:\s*(.+)$", re.IGNORECASE)

_TECH_LINE_LOOKAHEAD = re.compile(r"^Technologies?\s*:", re.IGNORECASE)

# Publications / Languages / Interests

_CERT_KEYWORDS_RE = re.compile(
    r"\b(certificate|certification|training|course|fundamentals|"
    r"student\s+expert|credential|completion|"
    r"udemy|coursera|simplilearn|edx|pluralsight|"
    r"linkedin\s+learning|aws|azure|postman|badgr|canvas\s+credentials)\b",
    re.IGNORECASE,
)

_AWARD_KEYWORDS_RE = re.compile(
    r"\b(member|membership|award|winner|recognition|scholar|fellowship|"
    r"developer\s+groups?|student\s+chapter|branch|community)\b",
    re.IGNORECASE,
)
