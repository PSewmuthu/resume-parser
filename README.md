# Resume Parser

A sophisticated NLP-powered resume parsing system that extracts and structures entity information from resumes in multiple formats (PDF, DOCX, TXT) into structured JSON output.

## Overview

This project automatically processes resumes using advanced natural language processing techniques to extract key information such as:

- **Personal Information**: Names, emails, phone numbers, addresses, and links
- **Professional Profiles**: LinkedIn, GitHub, Portfolio, Kaggle, HuggingFace, Twitter profiles
- **Education**: Degrees, institutions, GPA, graduation dates
- **Work Experience**: Job titles, companies, dates, descriptions, and technologies
- **Skills & Technologies**: Programming languages, frameworks, tools, and technical skills
- **Projects**: Project titles, descriptions, links, and associated technologies
- **Certifications & Awards**: Professional certifications and achievements

## Features

✅ **Multi-Format Support** - Processes PDF, DOCX, and TXT resume files  
✅ **Advanced Text Extraction** - Handles PDF annotations and links  
✅ **NLP-Powered Entity Recognition** - Uses spaCy for accurate entity extraction  
✅ **Robust Date Parsing** - Intelligently extracts and normalizes date ranges  
✅ **Pattern-Based Matching** - Comprehensive regex patterns for various entity types  
✅ **Text Normalization** - Cleans OCR artifacts and markdown formatting  
✅ **Structured JSON Output** - Machine-readable output for downstream processing  
✅ **Progress Tracking** - Real-time processing feedback with tqdm

## Project Structure

```
resume-parser/
├── main.py                          # Main entry point for processing
├── requirements.txt                 # Python dependencies
├── src/
│   ├── text_extractor.py           # Multi-format text extraction (PDF, DOCX, TXT)
│   ├── entity_extractor.py         # Core entity extraction and structuring
│   └── helpers/
│       ├── patterns.py             # Comprehensive regex patterns for all entity types
│       ├── text_cleaner.py         # Text normalization and OCR cleaning
│       ├── date_extractor.py       # Date parsing and range extraction
│       ├── link_extractor.py       # URL and social media link extraction
│       └── block_extractor.py      # Section-based text splitting and block extraction
└── data/
    ├── raw_resumes/                # Input: Raw resume files (PDF, DOCX, TXT)
    └── processed/                  # Output: Extracted JSON files
```

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Setup

1. **Clone the repository**

```bash
git clone https://github.com/PSewmuthu/resume-parser.git
cd resume-parser
```

2. **Create a virtual environment** (recommended)

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Download spaCy language model**

```bash
python -m spacy download en_core_web_sm
```

## Usage

### Basic Usage

Place your resume files in the `data/raw_resumes/` directory, then run:

```bash
python main.py
```

The script will:

1. Scan the `data/raw_resumes/` directory for PDF, DOCX, and TXT files
2. Extract text from each file using format-specific extractors
3. Parse entities from the extracted text using NLP and pattern matching
4. Save structured JSON output to `data/processed/`

### Input Formats

- **PDF Files** (`.pdf`) - Extracted with PyPDF2, supports embedded links
- **Word Documents** (`.docx`) - Extracted with python-docx
- **Text Files** (`.txt`) - Plain text files with UTF-8, Latin-1, or CP1252 encoding

### Output Format

Each processed resume generates a JSON file with the following structure:

```json
{
  "personal_info": {
    "name": "...",
    "email": "...",
    "phone": "...",
    "address": "...",
    "links": {
      "linkedin": "...",
      "github": "...",
      "portfolio": "...",
      ...
    }
  },
  "education": [
    {
      "degree": "...",
      "institution": "...",
      "gpa": "...",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM"
    }
  ],
  "experience": [
    {
      "job_title": "...",
      "company": "...",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM",
      "description": "...",
      "technologies": ["..."]
    }
  ],
  "projects": [
    {
      "title": "...",
      "description": "...",
      "link": "...",
      "technologies": ["..."]
    }
  ],
  "skills": ["..."],
  "certifications": ["..."],
  "awards": ["..."]
}
```

## Key Components

### TextExtractor (`src/text_extractor.py`)

Handles multi-format text extraction with:

- PDF text extraction with annotation link preservation
- DOCX table and paragraph extraction
- Automatic encoding detection for text files
- Deduplication of PDF double-accumulation artifacts

### EntityExtractor (`src/entity_extractor.py`)

Core extraction engine featuring:

- spaCy NLP-based named entity recognition
- Regex pattern-based entity matching
- Section-aware parsing (Education, Experience, Skills, etc.)
- Hierarchical block extraction for structured sections

### Helper Modules

- **patterns.py** - 30+ regex patterns for different entity types
- **text_cleaner.py** - OCR artifact removal, markdown stripping, whitespace normalization
- **date_extractor.py** - Fuzzy date parsing with range support
- **link_extractor.py** - Social media and portfolio link extraction
- **block_extractor.py** - Intelligent section splitting (experience, projects, education)

## Dependencies

Key dependencies include:

- **spacy** - NLP framework for entity recognition
- **PyPDF2** - PDF text extraction
- **python-docx** - DOCX file parsing
- **python-dateutil** - Flexible date parsing
- **tqdm** - Progress bar visualization
- **requests** - HTTP utilities
- **rich** - Terminal formatting

See `requirements.txt` for complete dependency list.

## Contributing

This project is part of an internship program at Gamage Recruiters. Contributions should follow the existing code structure and include proper documentation.

## Performance Notes

- Processing speed depends on file format and complexity
- PDF files may process slower than DOCX due to extraction complexity
- Large batch processing uses tqdm for real-time progress tracking
- All processing is done locally with no external API calls

## Known Limitations

- Date extraction relies on fuzzy parsing and pattern matching
- Embedded images in resumes are not processed
- Language support limited to English resumes
- Formatting variations may affect entity extraction accuracy

## Future Enhancements

- Support for additional languages
- Image/embedded content extraction
- Batch job matching against extracted skills
- API server for remote processing
- Web UI for interactive parsing
- Resume quality scoring
- Duplicate resume detection

---

**Last Updated**: June 2026
