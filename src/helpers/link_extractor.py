'''
Helpers for annotation-layer link extraction
'''

import re
from PyPDF2 import PdfReader
from src.helpers.patterns import _LINK_MARKER_RE


def extract_link_markers(raw_text: str) -> dict:
    """
    Parse __LINK_* markers injected by text_extractor from the PDF annotation layer.
    Returns dict with keys: linkedin, portfolio, github, kaggle, huggingface,
    project_githubs (list of {anchor, uri} dicts).
    Also returns cleaned_text with markers stripped out.
    """
    result = {
        'linkedin': '', 'portfolio': '', 'github': '',
        'kaggle': '', 'huggingface': '',
        'project_githubs': [],  # list of {'anchor': str, 'uri': str}
    }
    clean_lines = []

    for line in raw_text.splitlines():
        m = _LINK_MARKER_RE.match(line.strip())
        if m:
            ltype = m.group('type').lower()
            rest = m.group('rest')
            if ltype == 'linkedin':
                result['linkedin'] = rest
            elif ltype == 'portfolio':
                result['portfolio'] = rest
            elif ltype in ('github', 'github_profile'):
                result['github'] = rest
            elif ltype == 'kaggle':
                result['kaggle'] = rest
            elif ltype == 'huggingface':
                result['huggingface'] = rest
            elif ltype == 'project_github':
                # rest = "anchor:uri" or ":uri" (empty anchor)
                colon_idx = rest.find(':http')
                if colon_idx != -1:
                    anchor = rest[:colon_idx]
                    uri = rest[colon_idx + 1:]
                else:
                    anchor, uri = '', rest
                result['project_githubs'].append(
                    {'anchor': anchor, 'uri': uri})
            # skip 'other' markers
        else:
            clean_lines.append(line)

    result['cleaned_text'] = '\n'.join(clean_lines)
    return result


def _repo_keywords(uri: str) -> set:
    """Extract searchable keywords from a GitHub repo URI."""
    repo = uri.rstrip('/').split('/')[-1]
    words = re.split(r'[-_0-9]+', repo.lower())
    return {w for w in words if len(w) > 2}


def _project_keywords(name: str) -> set:
    words = re.split(r'[\s\-_]+', name.lower())
    return {w for w in words if len(w) > 2}


def _match_project_githubs(projects: list, project_githubs: list) -> list:
    """
    For each project_github URL, find the best-matching project by keyword overlap.
    Unmatched URLs are assigned to projects in order as fallback.
    Returns projects list with 'github' field added where matched.
    """
    if not project_githubs:
        return projects

    unmatched_urls = list(project_githubs)
    matched_indices = set()

    # Pass 1: keyword overlap matching
    for pg in list(unmatched_urls):
        slug_kws = _repo_keywords(pg['uri'])
        best_score, best_idx = 0, -1
        for i, proj in enumerate(projects):
            if i in matched_indices:
                continue
            name_kws = _project_keywords(proj.get('name', ''))
            score = len(slug_kws & name_kws)
            if score > best_score:
                best_score, best_idx = score, i
        if best_score > 0 and best_idx >= 0:
            projects[best_idx]['github'] = pg['uri']
            matched_indices.add(best_idx)
            unmatched_urls.remove(pg)

    # Pass 2: assign remaining URLs to projects without github, in order
    unmatched_projects = [i for i in range(
        len(projects)) if i not in matched_indices and 'github' not in projects[i]]
    for pg, proj_idx in zip(unmatched_urls, unmatched_projects):
        projects[proj_idx]['github'] = pg['uri']

    return projects
