'''
Helpers for annotation-layer link extraction
'''

import re
from PyPDF2 import PdfReader
from src.helpers.patterns import _LINK_MARKER_RE


def _get_pdf_links(reader: PdfReader) -> list:
    """
    Extract all hyperlink annotations from a PDF.
    Returns list of dicts: {page, uri, rect=[x0,y0,x1,y1]}
    """
    links = []
    for page_num, page in enumerate(reader.pages):
        annots = page.get('/Annots')
        if not annots:
            continue

        for annot in annots:
            try:
                obj = annot.get_object() if hasattr(annot, 'get_object') else annot
                if obj.get('/Subtype') != '/Link':
                    continue

                action = obj.get('/A', {})
                uri = str(action.get('/URI', '')) if action else ''
                if not uri:
                    continue

                rect = [float(x) for x in obj.get('/Rect', [])]
                links.append({'page': page_num, 'uri': uri, 'rect': rect})
            except Exception:
                continue

    return links


def _get_text_positions(page) -> list:
    """
    Extract (text, x, y) tuples from a page using PyPDF2 visitor.
    y is in PDF units from the bottom of the page.
    """
    items = []

    def visitor(text, cm, tm, font_dict, font_size):
        if text and text.strip():
            items.append((text.strip(), tm[4], tm[5]))

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:
        pass

    return items


def _nearest_text(page_items: list, rect: list, tolerance: float = 30.0) -> str:
    """
    Find the text item whose bounding-box centre is closest to the link rect.
    rect = [x0, y0, x1, y1] in PDF coordinates.
    """
    if not rect or len(rect) < 4:
        return ""

    rx_mid = (rect[0] + rect[2]) / 2
    ry_mid = (rect[1] + rect[3]) / 2

    best_text, best_dist = "", float('inf')
    for text, tx, ty in page_items:
        dist = ((tx - rx_mid) ** 2 + (ty - ry_mid) ** 2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best_text = text

    return best_text if best_dist < tolerance * 5 else ""


def _classify_link(uri: str, anchor_text: str) -> dict:
    """
    Given a URI and its anchor text, return a classification dict.
    Returns None if the link should be ignored.
    """
    uri_lower = uri.lower()

    if 'linkedin.com/in/' in uri_lower:
        return {'type': 'linkedin', 'uri': uri}

    if 'linkedin.com' in uri_lower:
        return {'type': 'linkedin', 'uri': uri}

    if 'github.io' in uri_lower:
        return {'type': 'portfolio', 'uri': uri}

    if 'github.com' in uri_lower:
        path = uri.replace('https://github.com/',
                           '').replace('http://github.com/', '')
        parts = [p for p in path.split('/') if p]

        if len(parts) == 1:
            return {'type': 'github_profile', 'uri': uri}

        # It's a repository link — it belongs to a project
        repo_name = parts[1] if len(parts) > 1 else parts[0]

        return {'type': 'project_github', 'uri': uri, 'anchor': anchor_text}

    if 'kaggle.com' in uri_lower:
        return {'type': 'kaggle', 'uri': uri}

    if 'huggingface.co' in uri_lower:
        return {'type': 'huggingface', 'uri': uri}

    # Portfolio / website heuristic: anchor text says "Portfolio" or "Website"
    anchor_lower = anchor_text.lower()
    if any(w in anchor_lower for w in ['portfolio', 'website', 'personal']):
        return {'type': 'portfolio', 'uri': uri}

    return {'type': 'other', 'uri': uri, 'anchor': anchor_text}


def _build_link_markers(reader: PdfReader) -> str:
    """
    Extract all annotation links and return a block of __LINK_ marker strings
    that are injected at the top of the extracted text.
    """
    raw_links = _get_pdf_links(reader)
    if not raw_links:
        return ""

    # Pre-compute text positions per page
    page_text_pos = {}
    for page_num, page in enumerate(reader.pages):
        page_text_pos[page_num] = _get_text_positions(page)

    markers = []
    seen_uris = set()

    for link in raw_links:
        uri = link['uri']
        if uri in seen_uris:
            continue

        seen_uris.add(uri)

        page_items = page_text_pos.get(link['page'], [])
        anchor = _nearest_text(page_items, link['rect'])
        classified = _classify_link(uri, anchor)
        if classified is None:
            continue

        t = classified['type']
        if t == 'linkedin':
            markers.append(f"__LINK_linkedin:{uri}")
        elif t == 'portfolio':
            markers.append(f"__LINK_portfolio:{uri}")
        elif t == 'github_profile':
            markers.append(f"__LINK_github:{uri}")
        elif t == 'kaggle':
            markers.append(f"__LINK_kaggle:{uri}")
        elif t == 'huggingface':
            markers.append(f"__LINK_huggingface:{uri}")
        elif t == 'project_github':
            # anchor is the "View Project" text or the project name
            markers.append(f"__LINK_project_github:{anchor}:{uri}")
        else:
            markers.append(f"__LINK_other:{uri}")

    return "\n".join(markers) + "\n" if markers else ""


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
