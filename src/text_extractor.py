'''
Extracts raw text from cv files with different formats (pdf, docx, txt).
'''

import os
import docx
from docx.oxml.ns import qn
from PyPDF2 import PdfReader
from src.helpers.link_extractor import _build_link_markers


class TextExtractor:
    def __init__(self, file_path):
        self.file_path = file_path

    def extract(self, file_path=None):
        if file_path is None:
            file_path = self.file_path

        if not os.path.isfile(file_path):
            raise ValueError("File does not exist.")

        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension == '.pdf':
            return self.extract_pdf(file_path)
        elif file_extension == '.docx':
            return self.extract_docx(file_path)
        elif file_extension == '.txt':
            return self.extract_text(file_path)
        else:
            raise ValueError("Unsupported file format.")

    def extract_text(self, file_path=None):
        if file_path is None:
            file_path = self.file_path

        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue

        raise ValueError(
            "Unable to decode the file with the provided encodings.")

    def extract_docx(self, file_path=None):
        if file_path is None:
            file_path = self.file_path

        try:
            doc = docx.Document(file_path)
            lines = []
            # Use w:t element iteration to capture ALL text including hyperlink anchor text
            for para in doc.paragraphs:
                # Extract every w:t element in the paragraph (runs + hyperlink runs)
                full_text = "".join(
                    t.text for t in para._element.iter(qn("w:t")) if t.text)
                lines.append(full_text)
            return "\n".join(lines)
        except Exception as e:
            raise ValueError(f"Error extracting DOCX file: {e}")

    def extract_pdf(self, file_path=None):
        if file_path is None:
            file_path = self.file_path

        try:
            reader = PdfReader(file_path)

            # Extract annotation-layer hyperlinks as structured markers
            link_markers = _build_link_markers(reader)

            # Extract text content from all pages
            text = ''
            for page in reader.pages:
                page_text = page.extract_text() or ''
                text += page_text + '\n'

            # Inject link markers at the top so entity_extractor can always find them
            return link_markers + text

        except Exception as e:
            raise ValueError(f"Error extracting PDF file: {e}")


if __name__ == "__main__":
    # For testing purposes, we can randomly select a file from the raw_resumes directory
    import random

    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    print(text)
