"""
Utility functions for parsing PDF drilling reports and extracting data.
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        s = str(value).strip()
        s = s.replace(',', '')
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", s)
        return float(m.group(0)) if m else default
    except Exception:
        return default


def _parse_date(date_str: str) -> Optional[str]:
    """Parse date string in various formats and return YYYY-MM-DD format.
    Prioritizes d-m-Y format (e.g., "18-11-2025") and full month names (e.g., "18 November 2025").
    """
    if not date_str:
        return None
    
    date_str = date_str.strip()
    # Remove common prefixes/suffixes
    date_str = re.sub(r'^(date|report\s*date|date\s*of\s*status)[:\s]+', '', date_str, flags=re.IGNORECASE).strip()
    
    # Prioritize formats found in actual PDFs
    formats = [
        '%d %B %Y',      # 18 November 2025 (from PDF image)
        '%d %b %Y',      # 18 Nov 2025
        '%B %d, %Y',     # November 18, 2025
        '%b %d, %Y',     # Nov 18, 2025
        '%d-%m-%Y',      # 18-11-2025
        '%d-%m-%y',      # 18-11-25
        '%d/%m/%Y',      # 18/11/2025
        '%d/%m/%y',      # 18/11/25
        '%d.%m.%Y',      # 18.11.2025 (Spud Date format)
        '%d.%m.%y',      # 18.11.25
        '%Y-%m-%d',      # 2025-11-18
        '%Y/%m/%d',      # 2025/11/18
        '%Y.%m.%d',      # 2025.11.18
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except Exception:
            continue
    
    return None


def extract_drilling_report_data(text: str, filename: str = None) -> Dict[str, Any]:
    """
    Extract drilling report data from PDF text.
    Based on the structure from populate_lithology.py and JSON format.
    
    Returns a dictionary with form field values.
    """
    data = {}
    text_upper = text.upper()
    original_text = text  # Keep original for case-sensitive extractions
    
    # Extract well name - try from filename first (e.g., SKL_DGR_25_18_11_2025.pdf -> Srikail-5)
    if filename:
        # Pattern: SKL -> Srikail, extract well name from filename
        if 'SKL' in filename.upper():
            data['well_name'] = 'Srikail-5'  # Common pattern from JSON
        else:
            # Try to extract from filename pattern
            well_match = re.search(r'([A-Z]+)[_-]', filename.upper())
            if well_match:
                well_code = well_match.group(1)
                # Map common codes (can be extended)
                well_map = {'SKL': 'Srikail-5'}
                data['well_name'] = well_map.get(well_code, well_code)
    
    # Also try to extract from text
    well_patterns = [
        r'well\s*name[:\s]+([A-Z0-9\-]+)',
        r'well[:\s]+([A-Z0-9\-]+)',
        r'([A-Z0-9\-]+)\s*well',
    ]
    for pattern in well_patterns:
        match = re.search(pattern, original_text, re.IGNORECASE)
        if match:
            well_name = match.group(1).strip()
            if well_name and len(well_name) > 2:  # Valid well name
                data['well_name'] = well_name
                break
    
    # Extract report number - look for patterns like "DGR 25" or "Report No. 25"
    report_no_patterns = [
        r'dgr\s*(\d+)',  # DGR 25
        r'report\s*no[\.:\s]+(\d+)',
        r'report\s*number[\.:\s]+(\d+)',
        r'report[\.:\s]+(\d+)',
    ]
    for pattern in report_no_patterns:
        match = re.search(pattern, text_upper, re.IGNORECASE)
        if match:
            try:
                data['report_no'] = int(match.group(1))
                break
            except ValueError:
                continue
    
    # Extract date - handle multiple formats including full month names
    # Pattern 1: "Report Date: 18 November 2025" or "18 November 2025"
    date_patterns = [
        (r'report\s*date[:\s]+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})', True),
        (r'report\s*date[:\s]+(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})', True),
        (r'date\s*of\s*status[:\s]+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})', True),
        (r'report\s*date[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', True),
        (r'date[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', True),
        (r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})', False),  # Full month name
        (r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})', False),  # Abbreviated month
        (r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})', False),  # Full year
        (r'(\d{1,2}[-/]\d{1,2}[-/]\d{2})', False),  # 2-digit year
    ]
    for pattern, case_sensitive in date_patterns:
        match = re.search(pattern, original_text if case_sensitive else text, re.IGNORECASE if not case_sensitive else 0)
        if match:
            parsed_date = _parse_date(match.group(1))
            if parsed_date:
                data['date'] = parsed_date
                break
    
    # Extract depths
    # Priority 1: Positional patterns (Value Value)
    # Format: Present Depth (m): <MD> <TVD>
    positional_patterns = [
        (r'Present Depth \(m\):\s*([\d.]+)(?:\s+[\d.]+)?', 'depth_end'),
        (r'Present Depth \(m\):\s*[\d.]+\s+([\d.]+)', 'depth_end_tvd'),
        (r'Previous Depth \(m\):\s*([\d.]+)(?:\s+[\d.]+)?', 'depth_start'),
        (r'Previous Depth \(m\):\s*[\d.]+\s+([\d.]+)', 'depth_start_tvd'),
    ]
    
    for pattern, key in positional_patterns:
        if key not in data:
            match = re.search(pattern, original_text, re.IGNORECASE)
            if match:
                val = _safe_float(match.group(1))
                if val > 0:
                    data[key] = val

    # Priority 2: Labeled patterns (MD: ... TVD: ...)
    # The format in some PDFs is:
    # Present Depth (m):
    # MD: 1499.40
    # TVD: 1433.34
    
    # Pattern 1: Look for "Present Depth (m):" section and extract MD/TVD values
    if 'depth_end' not in data or 'depth_end_tvd' not in data:
        present_section = re.search(
            r'present\s*depth\s*\(m\)[:\s]*\s*(?:.*?\n\s*)?md[:\s]+([0-9.,]+)\s*(?:.*?\n\s*)?tvd[:\s]+([0-9.,]+)',
            text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if present_section:
            md_val = _safe_float(present_section.group(1))
            tvd_val = _safe_float(present_section.group(2))
            if md_val > 0 and 'depth_end' not in data:
                data['depth_end'] = md_val
            if tvd_val > 0 and 'depth_end_tvd' not in data:
                data['depth_end_tvd'] = tvd_val
    
    # Pattern 2: Look for "Previous Depth (m):" section
    if 'depth_start' not in data or 'depth_start_tvd' not in data:
        previous_section = re.search(
            r'previous\s*depth\s*\(m\)[:\s]*\s*(?:.*?\n\s*)?md[:\s]+([0-9.,]+)\s*(?:.*?\n\s*)?tvd[:\s]+([0-9.,]+)',
            text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if previous_section:
            md_val = _safe_float(previous_section.group(1))
            tvd_val = _safe_float(previous_section.group(2))
            if md_val > 0 and 'depth_start' not in data:
                data['depth_start'] = md_val
            if tvd_val > 0 and 'depth_start_tvd' not in data:
                data['depth_start_tvd'] = tvd_val
    
    # Pattern 3: Try simpler patterns if above didn't match
    if 'depth_end' not in data:
        present_md = re.search(r'present\s*depth\s*\(m\)[:\s]*.*?md[:\s]+([0-9.,]+)', text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if present_md:
            val = _safe_float(present_md.group(1))
            if val > 0:
                data['depth_end'] = val
    
    if 'depth_start' not in data:
        previous_md = re.search(r'previous\s*depth\s*\(m\)[:\s]*.*?md[:\s]+([0-9.,]+)', text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if previous_md:
            val = _safe_float(previous_md.group(1))
            if val > 0:
                data['depth_start'] = val
    
    # Pattern 4: Direct patterns (fallback) - try without (m) format
    depth_patterns = [
        (r'present\s*depth\s*md[:\s]+([0-9.,]+)', 'depth_end'),
        (r'previous\s*depth\s*md[:\s]+([0-9.,]+)', 'depth_start'),
        (r'present\s*depth[:\s]+([0-9.,]+)', 'depth_end'),
        (r'previous\s*depth[:\s]+([0-9.,]+)', 'depth_start'),
        (r'depth\s*start[:\s]+([0-9.,]+)', 'depth_start'),
        (r'depth\s*end[:\s]+([0-9.,]+)', 'depth_end'),
        # Also try patterns that might match extracted text format
        (r'present.*?md[:\s]+([0-9.,]+)', 'depth_end'),
        (r'previous.*?md[:\s]+([0-9.,]+)', 'depth_start'),
    ]
    for pattern, key in depth_patterns:
        if key not in data:  # Don't overwrite if already found
            match = re.search(pattern, text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                val = _safe_float(match.group(1))
                if val > 0:
                    data[key] = val
    
    # Extract TVD depths - try simpler patterns if not already found
    if 'depth_end_tvd' not in data:
        present_tvd = re.search(r'present\s*depth\s*\(m\)[:\s]*.*?tvd[:\s]+([0-9.,]+)', text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if present_tvd:
            val = _safe_float(present_tvd.group(1))
            if val > 0:
                data['depth_end_tvd'] = val
    
    if 'depth_start_tvd' not in data:
        previous_tvd = re.search(r'previous\s*depth\s*\(m\)[:\s]*.*?tvd[:\s]+([0-9.,]+)', text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if previous_tvd:
            val = _safe_float(previous_tvd.group(1))
            if val > 0:
                data['depth_start_tvd'] = val
    
    # Pattern 4: Direct TVD patterns (fallback) - try without (m) format
    tvd_patterns = [
        (r'present\s*depth\s*tvd[:\s]+([0-9.,]+)', 'depth_end_tvd'),
        (r'previous\s*depth\s*tvd[:\s]+([0-9.,]+)', 'depth_start_tvd'),
        (r'present\s*tvd[:\s]+([0-9.,]+)', 'depth_end_tvd'),
        (r'previous\s*tvd[:\s]+([0-9.,]+)', 'depth_start_tvd'),
        # Also try patterns that might match extracted text format
        (r'present.*?tvd[:\s]+([0-9.,]+)', 'depth_end_tvd'),
        (r'previous.*?tvd[:\s]+([0-9.,]+)', 'depth_start_tvd'),
    ]
    for pattern, key in tvd_patterns:
        if key not in data:  # Don't overwrite if already found
            match = re.search(pattern, text_upper, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match:
                val = _safe_float(match.group(1))
                if val > 0:
                    data[key] = val
    
    # Extract Next Program (used as current_operation in populate_lithology.py)
    next_program_patterns = [
        r'next\s*program[:\s]+(.+?)(?:\n|$)',
        r'next\s*programme[:\s]+(.+?)(?:\n|$)',
    ]
    for pattern in next_program_patterns:
        match = re.search(pattern, original_text, re.IGNORECASE | re.MULTILINE)
        if match:
            data['current_operation'] = match.group(1).strip()[:500]
            data['next_program'] = match.group(1).strip()[:500]
            break
    
    # Extract current operation (if not set by next_program)
    if 'current_operation' not in data:
        operation_patterns = [
            r'current\s*operation[:\s]+(.+?)(?:\n|$)',
            r'operation[:\s]+(.+?)(?:\n|$)',
        ]
        for pattern in operation_patterns:
            match = re.search(pattern, original_text, re.IGNORECASE | re.MULTILINE)
            if match:
                data['current_operation'] = match.group(1).strip()[:500]
                break
    
    # Extract present activity
    activity_match = re.search(r'present\s*activity[:\s]+(.+?)(?:\n|$)', original_text, re.IGNORECASE | re.MULTILINE)
    if activity_match:
        data['present_activity'] = activity_match.group(1).strip()[:500]
    
    # Extract CSG information (casing)
    csg_patterns = [
        r'csg[:\s]+(.+?)(?:\n|last\s*csg|$)',
        r'casing[:\s]+(.+?)(?:\n|last\s*casing|$)',
    ]
    for pattern in csg_patterns:
        match = re.search(pattern, original_text, re.IGNORECASE | re.MULTILINE)
        if match:
            data['csg'] = match.group(1).strip()[:200]
            break
    
    # Extract Last CSG separately
    last_csg_patterns = [
        r'last\s*csg[:\s]+(.+?)(?:\n|$)',
        r'last\s*casing[:\s]+(.+?)(?:\n|$)',
    ]
    for pattern in last_csg_patterns:
        match = re.search(pattern, original_text, re.IGNORECASE | re.MULTILINE)
        if match:
            data['last_csg'] = match.group(1).strip()[:200]
            break
    
    # Extract gas show
    gas_show_patterns = [
        r'gas\s*show[:\s]+(.+?)(?:\n|$)',
        r'gas\s*indication[:\s]+(.+?)(?:\n|$)',
    ]
    for pattern in gas_show_patterns:
        match = re.search(pattern, original_text, re.IGNORECASE | re.MULTILINE)
        if match:
            data['gas_show'] = match.group(1).strip()[:500]
            break
    
    # Extract comments (general text at the end)
    if 'comments' not in data:
        comments_match = re.search(r'comments?[:\s]+(.+?)(?:\n\n|$)', original_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if comments_match:
            data['comments'] = comments_match.group(1).strip()[:1000]
    
    return data


def extract_lithology_data(text: str) -> List[Dict[str, Any]]:
    """
    Extract lithology data from PDF text.
    Based on the structure from populate_lithology.py JSON format.
    
    Returns a list of dictionaries, each representing a lithology interval.
    """
    lithologies = []
    original_text = text
    text_upper = text.upper()
    
    # Pattern to find depth intervals like "185-210 m" or "720-730m"
    depth_interval_pattern = r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*m\b'
    depth_matches = list(re.finditer(depth_interval_pattern, text, re.IGNORECASE))
    
    if not depth_matches:
        # Try alternative pattern without 'm'
        depth_interval_pattern = r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)'
        depth_matches = list(re.finditer(depth_interval_pattern, text, re.IGNORECASE))
    
    for i, depth_match in enumerate(depth_matches):
        depth_from = _safe_float(depth_match.group(1))
        depth_to = _safe_float(depth_match.group(2))
        
        if depth_from >= depth_to:  # Skip invalid ranges
            continue
        
        # Find text between this match and next match (or end, or next depth interval)
        start_pos = depth_match.end()
        if i + 1 < len(depth_matches):
            end_pos = depth_matches[i + 1].start()
        else:
            # Look for next section or end of lithology section
            next_section = re.search(r'\n\s*(?:formation|gas|summary|remarks)', text[start_pos:], re.IGNORECASE)
            end_pos = start_pos + (next_section.start() if next_section else len(text) - start_pos)
        
        interval_text = text[start_pos:end_pos]
        interval_text_upper = interval_text.upper()
        
        litho_data = {
            'depth_from': depth_from,
            'depth_to': depth_to,
            'shale_percentage': 0.0,
            'sand_percentage': 0.0,
            'clay_percentage': 0.0,
            'slit_percentage': 0.0,
            'coal_percentage': 0.0,
            'limestone_percentage': 0.0,
            'shale_description': '',
            'sand_description': '',
            'clay_description': '',
            'slit_description': '',
            'coal_description': '',
            'limestone_description': '',
            'description': ''
        }
        
        # Extract lithology components - look for patterns like:
        # "Sand: 80%" or "Sand: 80.0" or "Sand 80%" or "Sand 80"
        # Also handle "Trace" as percentage
        lithology_types = [
            ('sand', 'sand_percentage', 'sand_description'),
            ('shale', 'shale_percentage', 'shale_description'),
            ('clay', 'clay_percentage', 'clay_description'),
            ('silt', 'slit_percentage', 'slit_description'),
            ('slit', 'slit_percentage', 'slit_description'),  # Handle typo
            ('coal', 'coal_percentage', 'coal_description'),
            ('limestone', 'limestone_percentage', 'limestone_description'),
            ('lime', 'limestone_percentage', 'limestone_description'),
        ]
        
        descriptions = []
        
        for lith_type, pct_key, desc_key in lithology_types:
            # Pattern 1: "Sand: 80%" or "Sand: 80.0" or "Sand 80%"
            pattern1 = rf'{lith_type}[:\s]+(\d+\.?\d*)\s*%?'
            match1 = re.search(pattern1, interval_text_upper, re.IGNORECASE)
            
            # Pattern 2: "Sand" followed by percentage on same or next line
            pattern2 = rf'{lith_type}[:\s]*(?:\n\s*)?(\d+\.?\d*)\s*%?'
            match2 = re.search(pattern2, interval_text_upper, re.IGNORECASE | re.MULTILINE)
            
            # Pattern 3: Handle "Trace"
            pattern3 = rf'{lith_type}[:\s]*(?:trace|tr)'
            match3 = re.search(pattern3, interval_text_upper, re.IGNORECASE)
            
            pct_value = 0.0
            if match1:
                pct_value = _safe_float(match1.group(1))
            elif match2:
                pct_value = _safe_float(match2.group(1))
            elif match3:
                pct_value = 1.0  # Trace = 1.0 as per populate_lithology.py
            
            if pct_value > 0:
                litho_data[pct_key] = pct_value
                
                # Extract description - look for text after the type and percentage
                # Handle formats like:
                # "Sand: 80% Description text"
                # "Sand: Description text"  
                # "Sand Description text"
                # "Sand: Colorless to white, loose, transparent..."
                desc_patterns = [
                    # Pattern with percentage: "Sand: 80% Description"
                    rf'{lith_type}[:\s]+\d+\.?\d*\s*%?\s*[:\s]+(.+?)(?:\n\s*(?:Sand|Shale|Clay|Silt|Slit|Coal|Limestone|Lime|\d+\s*[-–]|\d+\s*m\b|$))',
                    # Pattern without percentage: "Sand: Description"
                    rf'{lith_type}[:\s]+(.+?)(?:\n\s*(?:Sand|Shale|Clay|Silt|Slit|Coal|Limestone|Lime|\d+\s*[-–]|\d+\s*m\b|$))',
                    # Pattern: "Sand Description" (no colon)
                    rf'{lith_type}\s+(.+?)(?:\n\s*(?:Sand|Shale|Clay|Silt|Slit|Coal|Limestone|Lime|\d+\s*[-–]|\d+\s*m\b|$))',
                ]
                
                for desc_pattern in desc_patterns:
                    desc_match = re.search(desc_pattern, interval_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    if desc_match:
                        desc = desc_match.group(1).strip()
                        # Clean up description - remove leading percentage if present
                        desc = re.sub(r'^\d+\.?\d*\s*%?\s*[:\s]*', '', desc)
                        # Remove common prefixes
                        desc = re.sub(r'^(colorless|sand|shale|clay|silt|coal|limestone|lime)[:\s]+', '', desc, flags=re.IGNORECASE)
                        desc = desc.strip()
                        
                        # Skip if description is just a number or too short
                        if desc and len(desc) > 5 and not desc.replace('.', '').replace(',', '').isdigit():
                            # Limit description length
                            if len(desc) > 200:
                                desc = desc[:197] + '...'
                            litho_data[desc_key] = desc
                            # Also add to general description (avoid duplicates)
                            desc_entry = f"{lith_type.title()}: {desc}"
                            if desc_entry not in descriptions:
                                descriptions.append(desc_entry)
                        break
        
        # Build general description from all components
        if descriptions:
            litho_data['description'] = '\n\n'.join(descriptions)
        
        # Only add if at least one percentage is non-zero
        if any(litho_data.get(k, 0) > 0 for k in ['shale_percentage', 'sand_percentage', 
                                                   'clay_percentage', 'slit_percentage',
                                                   'coal_percentage', 'limestone_percentage']):
            lithologies.append(litho_data)
    
    return lithologies


def parse_pdf_text(pdf_file) -> str:
    """
    Extract text from a PDF file.
    Uses pypdf (PyPDF2 successor), pdfplumber, or PyPDF2 if available.
    Handles Django uploaded file objects.
    """
    # Reset file pointer in case it was read before
    if hasattr(pdf_file, 'seek'):
        pdf_file.seek(0)
    
    try:
        # Try pypdf first (newer, already in requirements)
        import pypdf
        # pypdf can work with file-like objects
        pdf_reader = pypdf.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        # Reset file pointer after reading
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)
        return text
    except ImportError:
        try:
            # Fallback to PyPDF2 (older version)
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            if hasattr(pdf_file, 'seek'):
                pdf_file.seek(0)
            return text
        except ImportError:
            try:
                # Fallback to pdfplumber
                import pdfplumber
                text = ""
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                if hasattr(pdf_file, 'seek'):
                    pdf_file.seek(0)
                return text
            except ImportError:
                raise ImportError(
                    "Please install a PDF library: "
                    "pip install pypdf (or PyPDF2 or pdfplumber)"
                )
    except Exception as e:
        # Reset file pointer on error
        if hasattr(pdf_file, 'seek'):
            pdf_file.seek(0)
        raise Exception(f"Error reading PDF: {str(e)}")

