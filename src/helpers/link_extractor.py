'''
Helpers for annotation-layer link extraction
'''

from PyPDF2 import PdfReader


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
