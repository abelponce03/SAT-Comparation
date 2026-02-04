"""
CNF Parser - Extract metadata from CNF files
"""

import re
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def parse_cnf_header(filepath: str) -> Dict[str, Optional[int]]:
    """
    Parse CNF file header to extract variables and clauses count.
    
    Returns:
        dict with 'num_variables', 'num_clauses', 'clause_variable_ratio'
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                
                # Look for problem line: p cnf <variables> <clauses>
                if line.startswith('p cnf'):
                    parts = line.split()
                    if len(parts) >= 4:
                        num_vars = int(parts[2])
                        num_clauses = int(parts[3])
                        
                        ratio = num_clauses / num_vars if num_vars > 0 else 0
                        
                        return {
                            'num_variables': num_vars,
                            'num_clauses': num_clauses,
                            'clause_variable_ratio': round(ratio, 2)
                        }
        
        logger.warning(f"No problem line found in {filepath}")
        return {
            'num_variables': None,
            'num_clauses': None,
            'clause_variable_ratio': None
        }
        
    except Exception as e:
        logger.error(f"Error parsing CNF {filepath}: {e}")
        return {
            'num_variables': None,
            'num_clauses': None,
            'clause_variable_ratio': None
        }


def classify_benchmark_family(filename: str, patterns: Dict[str, str]) -> str:
    """
    Classify benchmark into family based on filename patterns.
    
    Args:
        filename: Benchmark filename
        patterns: Dict of {family_name: regex_pattern}
    
    Returns:
        Family name or 'other'
    """
    filename_lower = filename.lower()
    
    for family, pattern in patterns.items():
        if re.search(pattern, filename_lower):
            return family
    
    return 'other'


def estimate_difficulty(num_variables: Optional[int], 
                       num_clauses: Optional[int],
                       ratio: Optional[float]) -> str:
    """
    Estimate benchmark difficulty based on size and ratio.
    
    Heuristic classification:
    - Easy: < 1000 variables or ratio < 3.0
    - Medium: 1000-10000 variables or ratio 3.0-5.0
    - Hard: > 10000 variables or ratio > 5.0
    """
    if num_variables is None or num_clauses is None:
        return 'unknown'
    
    if num_variables < 1000 or (ratio and ratio < 3.0):
        return 'easy'
    elif num_variables < 10000 or (ratio and ratio < 5.0):
        return 'medium'
    else:
        return 'hard'


def get_file_size_kb(filepath: str) -> int:
    """Get file size in KB"""
    try:
        return Path(filepath).stat().st_size // 1024
    except Exception as e:
        logger.error(f"Error getting file size for {filepath}: {e}")
        return 0


def calculate_checksum(filepath: str) -> str:
    """Calculate MD5 checksum of file"""
    import hashlib
    
    try:
        md5 = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating checksum for {filepath}: {e}")
        return ""


def parse_benchmark_metadata(filepath: str, 
                            family_patterns: Dict[str, str]) -> Dict:
    """
    Extract all metadata from a benchmark file.
    
    Args:
        filepath: Path to CNF file
        family_patterns: Dictionary of family patterns
    
    Returns:
        Dictionary with all benchmark metadata
    """
    path = Path(filepath)
    filename = path.name
    
    # Parse CNF header
    cnf_data = parse_cnf_header(filepath)
    
    # Classify family
    family = classify_benchmark_family(filename, family_patterns)
    
    # Estimate difficulty
    difficulty = estimate_difficulty(
        cnf_data['num_variables'],
        cnf_data['num_clauses'],
        cnf_data['clause_variable_ratio']
    )
    
    # Get file info
    size_kb = get_file_size_kb(filepath)
    checksum = calculate_checksum(filepath)
    
    return {
        'filename': filename,
        'filepath': str(path.absolute()),
        'family': family,
        'size_kb': size_kb,
        'num_variables': cnf_data['num_variables'],
        'num_clauses': cnf_data['num_clauses'],
        'clause_variable_ratio': cnf_data['clause_variable_ratio'],
        'difficulty': difficulty,
        'checksum': checksum
    }
