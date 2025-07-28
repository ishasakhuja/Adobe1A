#!/usr/bin/env python3
"""
Adobe India Hackathon - Round 1A: Enhanced PDF Outline Extractor
Extracts structured outline (title and headings) from PDF documents with advanced content detection
"""

import os
import json
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
import fitz  # PyMuPDF
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedPDFOutlineExtractor:
    """Enhanced PDF outline extractor with sophisticated content detection"""
    
    def __init__(self):
        self.doc = None
        self.font_sizes = []
        self.common_font_size = None
        self.extracted_title = ""
        self.min_font_size_threshold = 8
        self.title_search_pages = 3
        
    def process_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Main method to process a PDF and extract outline"""
        logger.info(f"Processing PDF: {pdf_path}")
        
        try:
            self.doc = fitz.open(pdf_path)
            logger.info(f"Document has {len(self.doc)} pages")
            
            # Analyze document fonts
            self._analyze_document_fonts()
            
            # Extract title using enhanced method
            title = self._extract_title_enhanced()
            self.extracted_title = title.lower().strip()
            
            # Extract outline using enhanced method with content detection
            outline = self._extract_outline_enhanced()
            
            return {
                "title": title,
                "outline": outline
            }
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            return {"title": "Error", "outline": []}
        finally:
            if self.doc:
                self.doc.close()
    
    def _analyze_document_fonts(self) -> None:
        """Analyze font sizes across the document to establish baseline"""
        font_sizes = []
        
        # Analyze first few pages for font patterns
        for page_num in range(min(3, len(self.doc))):
            page = self.doc[page_num]
            blocks = page.get_text("dict")
            
            for block in blocks.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                font_sizes.append(span["size"])
        
        self.font_sizes = font_sizes
        self.common_font_size = Counter(font_sizes).most_common(1)[0][0] if font_sizes else 12
        logger.info(f"Common font size detected: {self.common_font_size}")
    
    def _extract_title_enhanced(self) -> str:
        """Enhanced title extraction using multiple strategies"""
        # Strategy 1: Try to get title from document outline/bookmarks
        try:
            outline = self.doc.get_toc()
            if outline and len(outline) > 0:
                first_bookmark = outline[0][1].strip()
                if (first_bookmark and 
                    not first_bookmark.lower().startswith(('table of contents', 'contents', 'toc')) and
                    len(first_bookmark) > 3):
                    return self._clean_text(first_bookmark)
        except:
            pass
        
        # Strategy 2: Extract from document text using font analysis
        return self._extract_title_from_text()
    
    def _extract_title_from_text(self) -> str:
        """Extract title by analyzing text formatting"""
        if not self.doc or len(self.doc) == 0:
            return "Unknown Title"
        
        # Look only at first page for title
        page = self.doc[0]
        blocks = page.get_text("dict")
        candidates = []
        
        for block in blocks.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    max_size = 0
                    y_pos = float('inf')
                    flags = 0
                    
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            line_text += text + " "
                            max_size = max(max_size, span["size"])
                            y_pos = min(y_pos, span.get("bbox", [0, 0, 0, 0])[1])
                            flags |= span["flags"]
                    
                    line_text = line_text.strip()
                    
                    if self._is_potential_title(line_text, max_size, flags):
                        candidates.append({
                            'text': line_text,
                            'size': max_size,
                            'y_pos': y_pos
                        })
        
        if candidates:
            # Sort by font size (descending), then by position
            candidates.sort(key=lambda x: (-x['size'], x['y_pos']))
            
            # Combine top candidates if they're close in size/position
            combined = "  ".join(c['text'] for c in candidates[:2])
            return self._clean_text(combined)
        
        return "Unknown Title"
    
    def _is_potential_title(self, text: str, size: float, flags: int) -> bool:
        """Check if text could be a title"""
        if not text or len(text) < 3 or len(text) > 150:
            return False
        
        # Skip common non-title text
        skip_words = ['copyright', 'version', 'page', '©', 'confidential', 'draft', 'revision', 'date', 'author']
        if any(skip.lower() in text.lower() for skip in skip_words):
            return False
        
        # Check formatting indicators
        is_bold = flags & (1 << 4)  # Bold flag
        is_large = size > self.common_font_size * 1.2
        
        return is_large or is_bold
    
    def _extract_outline_enhanced(self) -> List[Dict[str, Any]]:
        """Enhanced outline extraction with content validation"""
        return self._extract_headings_from_text()
    
    def _extract_headings_from_text(self) -> List[Dict[str, Any]]:
        """Extract headings by analyzing text formatting and content"""
        headings = []
        thresholds = self._calculate_size_thresholds()
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            blocks = page.get_text("dict")
            page_headings = self._extract_page_headings(blocks, page_num, thresholds)
            headings.extend(page_headings)
        
        # Post-process headings
        headings = self._post_process_headings(headings)
        
        # Filter headings that have meaningful content after them
        headings = self._filter_headings_with_subtext(headings)
        
        return headings
    
    def _calculate_size_thresholds(self) -> Dict[str, float]:
        """Calculate font size thresholds for different heading levels"""
        baseline = self.common_font_size or 12
        return {
            "h1": baseline * 1.4,
            "h2": baseline * 1.2,
            "h3": baseline * 1.1
        }
    
    def _extract_page_headings(self, blocks: Dict, page_num: int, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        """Extract headings from a single page"""
        headings = []
        prev = None
        
        for block in blocks.get("blocks", []):
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                line_data = self._analyze_line(line)
                if not line_data:
                    continue
                
                text = line_data['text'].lower().strip()
                
                # Skip common metadata on non-first pages
                if text in {"overview", "version", "date", "remarks", "identifier", "reference"} and page_num != 0:
                    continue
                
                # Skip title
                if text == self.extracted_title:
                    continue
                
                if self._is_heading_candidate(line_data, thresholds):
                    # Special case: combine with previous if it's "syllabus"
                    if prev and line_data['text'].lower().strip() == 'syllabus':
                        prev['text'] += " " + line_data['text']
                        continue
                    
                    level = self._determine_heading_level(line_data, thresholds)
                    
                    heading = {
                        "level": level,
                        "text": self._clean_text(line_data['text']),
                        "page": page_num,  # 0-based for internal processing
                        "confidence": line_data.get('confidence', 0.5),
                        "bbox": line_data.get('bbox')
                    }
                    headings.append(heading)
                    prev = heading
        
        return headings
    
    def _analyze_line(self, line: Dict) -> Optional[Dict[str, Any]]:
        """Analyze a line of text for heading characteristics"""
        line_text = ""
        max_size = 0
        flags = 0
        bbox = None
        
        for span in line["spans"]:
            text = span["text"].strip()
            if text:
                line_text += text + " "
                max_size = max(max_size, span["size"])
                flags |= span["flags"]
                if bbox is None:
                    bbox = span.get("bbox", [0, 0, 0, 0])
        
        line_text = line_text.strip()
        
        if not line_text or len(line_text) < 2:
            return None
        
        confidence = self._calculate_confidence(line_text, max_size, flags)
        
        return {
            'text': line_text,
            'size': max_size,
            'flags': flags,
            'bbox': bbox,
            'confidence': confidence
        }
    
    def _calculate_confidence(self, text: str, size: float, flags: int) -> float:
        """Calculate confidence score for heading detection"""
        confidence = 0.0
        
        # Size-based confidence
        if size > self.common_font_size * 1.3:
            confidence += 0.3
        elif size > self.common_font_size * 1.1:
            confidence += 0.2
        
        # Bold text
        if flags & (1 << 4):  # Bold flag
            confidence += 0.2
        
        # Pattern matching
        if self._matches_heading_patterns(text):
            confidence += 0.3
        
        # Length-based confidence
        if 5 <= len(text) <= 100:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _matches_heading_patterns(self, text: str) -> bool:
        """Check if text matches common heading patterns"""
        patterns = [
            r'^\d+\.?\s+[A-Z]',  # "1. Introduction"
            r'^\d+\.\d+\.?\s+',  # "1.1 Background"
            r'^(Chapter|Section|Part)\s+\d+',  # "Chapter 1"
            r'^[A-Z][A-Z\s]{2,}$',  # All caps headings
            r'^[A-Z][a-z]+(\s+[A-Z][a-z]*)*$',  # Title case
            r'^(Abstract|Introduction|Conclusion|References|Bibliography|Acknowledgments?)$'  # Common section names
        ]
        
        return any(re.match(pattern, text.strip(), re.IGNORECASE) for pattern in patterns)
    
    def _is_heading_candidate(self, line_data: Dict, thresholds: Dict[str, float]) -> bool:
        """Check if a line is a potential heading"""
        text = line_data['text']
        size = line_data['size']
        
        # Basic filters
        if len(text) > 200 or len(text) < 3:
            return False
        
        # Must meet size threshold OR pattern matching, with minimum confidence
        meets_size = size >= thresholds['h3']
        meets_pattern = self._matches_heading_patterns(text)
        meets_confidence = line_data['confidence'] > 0.4
        
        return (meets_size or meets_pattern) and meets_confidence
    
    def _determine_heading_level(self, line_data: Dict, thresholds: Dict[str, float]) -> str:
        """Determine the heading level (H1, H2, H3)"""
        text = line_data['text']
        size = line_data['size']
        
        # Pattern-based level detection
        if re.match(r'^\d+\.?\s+', text.strip()):
            return "H1"
        elif re.match(r'^\d+\.\d+\.?\s+', text.strip()):
            return "H2"
        elif re.match(r'^\d+\.\d+\.\d+\.?\s+', text.strip()):
            return "H3"
        
        # Size-based level detection
        if size >= thresholds['h1']:
            return "H1"
        elif size >= thresholds['h2']:
            return "H2"
        else:
            return "H3"
    
    def _has_content_after_heading(self, heading: Dict[str, Any], next_heading: Optional[Dict[str, Any]]) -> bool:
        """Check if there's meaningful content after a heading"""
        start_page = heading['page']
        end_page = next_heading['page'] if next_heading else min(start_page + 1, len(self.doc) - 1)
        
        for page_num in range(start_page, end_page + 1):
            page = self.doc[page_num]
            blocks = page.get_text("dict").get("blocks", [])
            
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = " ".join(span["text"].strip() for span in line["spans"] if span["text"].strip())
                        if not line_text:
                            continue
                        
                        # Skip if it's the heading itself
                        if heading["text"].lower() in line_text.lower():
                            continue
                        
                        # Skip if it's another heading
                        if self._matches_heading_patterns(line_text):
                            continue
                        
                        # Check for paragraph text (long sentences)
                        if len(line_text) > 40 and not line_text.isupper():
                            return True
                        
                        # Check for bullet/numbered lists
                        if re.match(r"^\s*[\u2022\-\*•]\s+\S+", line_text):  # bullets like • - * etc
                            return True
                        if re.match(r"^\s*\(?\d+[\.\)]\s+\S+", line_text):  # numbered list
                            return True
                
                elif block.get("type") == 1:  # Image/table/figure
                    return True
        
        return False
    
    def _filter_headings_with_subtext(self, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter headings to keep only those with meaningful content or subheadings"""
        result = []
        
        for i, heading in enumerate(headings):
            next_heading = headings[i + 1] if i + 1 < len(headings) else None
            
            # Check if this heading has subheadings (children)
            has_children = False
            for j in range(i + 1, len(headings)):
                if headings[j]['page'] > heading['page'] + 1:
                    break
                if int(headings[j]['level'][1]) > int(heading['level'][1]):
                    has_children = True
                    break
            
            # Check if this heading has meaningful content after it
            has_content = self._has_content_after_heading(heading, next_heading)
            
            # Keep heading if it has children or content
            if has_children or has_content:
                # Clean up the heading before adding to result
                clean_heading = {k: v for k, v in heading.items() if k not in ['confidence', 'bbox']}
                # Convert to 1-based page numbering for output
                clean_heading['page'] = clean_heading['page'] + 1
                result.append(clean_heading)
        
        return result
    
    def _post_process_headings(self, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process headings to remove duplicates and sort"""
        if not headings:
            return headings
        
        # Remove duplicates
        seen = set()
        unique_headings = []
        
        for heading in headings:
            key = (heading['text'], heading['page'])
            if key not in seen:
                seen.add(key)
                unique_headings.append(heading)
        
        # Sort by page and position
        unique_headings.sort(key=lambda x: (x['page'], x.get('bbox', [0])[1] if x.get('bbox') else 0))
        
        return unique_headings
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Ensure proper encoding
        text = text.encode('utf-8', 'ignore').decode('utf-8')
        
        return text


def process_all_pdfs(input_dir: str, output_dir: str):
    """Process all PDFs in input directory"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    extractor = EnhancedPDFOutlineExtractor()
    
    # Find all PDF files
    pdf_files = list(input_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    for pdf_file in pdf_files:
        try:
            # Process PDF
            result = extractor.process_pdf(str(pdf_file))
            
            # Save JSON output
            output_file = output_path / f"{pdf_file.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully processed {pdf_file.name}")
            logger.info(f"Title: {result['title']}")
            logger.info(f"Found {len(result['outline'])} headings")
            logger.info(f"Output saved to: {output_file.name}")
            print("-" * 50)  # Visual separator
            
        except Exception as e:
            logger.error(f"Error processing {pdf_file.name}: {e}")


def main():
    """Main entry point"""
    # Docker-friendly hardcoded paths
    input_dir = "/app/input"
    output_dir = "/app/output"
    
    # Check if directories exist
    if not os.path.exists(input_dir):
        logger.error(f"Input directory {input_dir} does not exist")
        sys.exit(1)
    
    logger.info("Starting Enhanced PDF outline extraction with content detection")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Output directory: {output_dir}")
    
    process_all_pdfs(str(input_dir), str(output_dir))
    logger.info("Enhanced PDF outline extraction completed")

if __name__ == "__main__":
    main()