# PDF Outline Extractor - Adobe India Hackathon Round 1A

## Overview

This solution extracts structured outlines (title and headings H1-H3) from PDF documents using intelligent font analysis. It processes PDFs to identify hierarchical document structure without relying solely on font sizes.

## Approach

### 1. Text Block Extraction

- Uses PyMuPDF to extract all text blocks with font metadata (size, family, page number)
- Captures bounding box information for spatial analysis

### 2. Font Hierarchy Analysis

- Identifies body text as the most frequently used font size
- Determines heading fonts as sizes larger than body text
- Maps top 3 heading font sizes to H1, H2, H3 levels respectively

### 3. Title Extraction

- Searches first 2 pages for title candidates
- Prioritizes largest fonts with reasonable text length (5-100 characters)
- Applies cleaning logic to remove common prefixes

### 4. Heading Detection

- Extracts headings based on font hierarchy mapping
- Filters false positives (page numbers, figure captions, etc.)
- Removes duplicate headings while preserving document order
- Cleans heading text by removing numbering patterns

## Models and Libraries Used

- **PyMuPDF (fitz)**: PDF text extraction and font analysis (~15MB)
- **Python Standard Library**: JSON processing, logging, file operations
- **No external ML models**: Pure rule-based approach for fast processing

## Key Features

- **Multilingual Support**: Unicode-aware text processing
- **Robust Font Analysis**: Doesn't rely solely on absolute font sizes
- **False Positive Filtering**: Intelligent filtering of non-heading content
- **Performance Optimized**: Processes 50-page PDFs well under 10 seconds
- **Modular Design**: Easy to extend for Round 1B requirements

## File Structure

```
├── main.py              # Main extraction logic
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── test_solution.py    # Local testing script
└── README.md           # This file
```

## Docker Build and Run

### Build Image

```bash
docker build --platform linux/amd64 -t pdf-extractor:latest .
```

### Run Solution (Adobe's Expected Command)

```bash
docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none pdf-extractor:latest
```

### Directory Structure for Testing

```
project-root/
├── input/
│   ├── document1.pdf
│   └── document2.pdf
└── output/
    ├── document1.json
    └── document2.json
```

## Local Testing

1. Install dependencies:

```bash
pip install PyMuPDF
```

2. Run test script:

```bash
python test_solution.py
```

3. Test with your own PDFs:

```bash
mkdir -p input output
# Place your PDFs in input/
python main.py
```

## Output Format

```json
{
  "title": "Understanding AI Systems",
  "outline": [
    { "level": "H1", "text": "Introduction", "page": 1 },
    { "level": "H2", "text": "What is Artificial Intelligence", "page": 2 },
    { "level": "H3", "text": "Machine Learning Basics", "page": 3 },
    { "level": "H1", "text": "Deep Learning", "page": 5 }
  ]
}
```

## Performance Specifications

- **Execution Time**: ≤ 10 seconds for 50-page PDF
- **Model Size**: ~15MB (PyMuPDF only)
- **Memory Usage**: ~50MB typical, scales with document size
- **Architecture**: AMD64 (x86_64) compatible
- **Network**: Fully offline, no internet calls

## Algorithm Strengths

1. **Font-Agnostic**: Works across different PDF creators and styles
2. **Language Independent**: Processes multilingual documents
3. **Hierarchy Preservation**: Maintains proper H1 > H2 > H3 relationships
4. **False Positive Reduction**: Advanced filtering for clean results
5. **Scalable**: Efficient processing of large document collections

## Limitations and Assumptions

- Assumes hierarchical font sizing (larger = higher level)
- Limited to 3 heading levels (H1, H2, H3)
- Title detection focused on first 2 pages
- Requires minimum readable font size (8pt)

## Future Enhancements (Round 1B Ready)

The modular design allows easy extension for:

- Semantic content analysis
- Section relevance scoring
- Cross-document relationship mapping
- Persona-driven content extraction

## Testing Recommendations

1. Test with academic papers (consistent formatting)
2. Test with business reports (varying styles)
3. Test with multilingual documents
4. Verify performance with 50-page documents
5. Check output JSON format compliance

## Troubleshooting

**Common Issues:**

- No headings extracted: Check if PDF has text (not scanned images)
- Wrong hierarchy: Document may not follow standard font sizing
- Missing title: Ensure title exists in first 2 pages with distinctive font

**Debug Mode:**
Enable detailed logging by modifying the logging level in main.py:

```python
logging.basicConfig(level=logging.DEBUG)
```
