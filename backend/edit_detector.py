import re
from typing import Dict, Optional, List, Tuple
import logging
from datetime import datetime
from nltk.stem import PorterStemmer
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EditDetector:
    """
    Detects and classifies edit patterns in user queries.
    Supports partial word matching and weighted attribute detection.
    """
    
    # Edit type patterns with example matches
    EDIT_PATTERNS = {
        'title': [
            r'change\s+(?:the\s+)?(?:title|name)\s+(?:to|of)\s+(.+)',  # "change title to X"
            r'rename\s+(?:to|as)\s+(.+)',  # "rename to X"
            r'make\s+(?:the\s+)?title\s+(.+)'  # "make the title X"
        ],
        'date': [
            r'move\s+(?:to|for)\s+(.+)',  # "move to tomorrow"
            r'reschedule\s+(?:to|for)\s+(.+)',  # "reschedule to next week"
            r'change\s+(?:the\s+)?date\s+to\s+(.+)'  # "change date to Friday"
        ],
        'description': [
            r'change\s+(?:the\s+)?description\s+to\s+(.+)',  # "change description to X"
            r'update\s+(?:the\s+)?description\s+(?:to|with)\s+(.+)',  # "update description with X"
            r'add\s+description\s+(.+)'  # "add description X"
        ],
        'priority': [
            r'(?:set|change)\s+(?:the\s+)?priority\s+(?:to|as)\s+(.+)',  # "set priority to high"
            r'make\s+(?:it\s+)?(?:a\s+)?(.+)\s+priority'  # "make it high priority"
        ]
    }
    
    # Weights for different attributes when doing partial matching
    ATTRIBUTE_WEIGHTS = {
        'title': 1.0,
        'date': 0.9,
        'description': 0.8,
        'priority': 0.7
    }
    
    def __init__(self):
        """Initialize the EditDetector with necessary tools."""
        self.stemmer = PorterStemmer()
        # Cache for stemmed words to improve performance
        self.stem_cache = {}
        
    def detect_edit_type(self, query: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Detect the type of edit requested and extract the new value.
        
        Args:
            query: The user's edit request
            
        Returns:
            Tuple of (edit_type, new_value, confidence_score)
        """
        logger.info(f"Detecting edit type for query: {query}")
        
        # Clean the query
        clean_query = self._clean_text(query)
        
        # Try exact pattern matching first
        exact_match = self._match_exact_patterns(clean_query)
        if exact_match:
            logger.info(f"Found exact edit pattern match: {exact_match}")
            return exact_match
            
        # If no exact match, try partial matching
        partial_match = self._match_partial_patterns(clean_query)
        if partial_match:
            logger.info(f"Found partial edit pattern match: {partial_match}")
            return partial_match
            
        logger.warning("No edit pattern detected")
        return None, None, 0.0
        
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for pattern matching."""
        # Convert to lowercase
        text = text.lower()
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
        
    def _match_exact_patterns(self, query: str) -> Optional[Tuple[str, str, float]]:
        """Try to match exact edit patterns."""
        for edit_type, patterns in self.EDIT_PATTERNS.items():
            for pattern in patterns:
                match = re.match(pattern, query, re.IGNORECASE)
                if match:
                    new_value = match.group(1).strip()
                    return edit_type, new_value, 1.0
        return None
        
    def _match_partial_patterns(self, query: str) -> Optional[Tuple[str, str, float]]:
        """
        Try to match partial patterns using word stems and fuzzy matching.
        Uses a more flexible approach for finding edit intentions.
        """
        # Get stemmed words from query
        query_stems = self._get_stems(query)
        
        best_match = None
        highest_score = 0
        
        # Common edit action words and their stems
        edit_actions = {
            'change', 'update', 'modify', 'edit', 'set', 'make',
            'move', 'reschedule', 'rename', 'add'
        }
        
        # Check if query contains any edit action words
        has_edit_action = any(
            action in query or self.stemmer.stem(action) in query_stems
            for action in edit_actions
        )
        
        if not has_edit_action:
            return None
            
        # Try to identify the attribute being edited
        for attr_type, weight in self.ATTRIBUTE_WEIGHTS.items():
            # Look for attribute keywords
            attr_score = self._calculate_attribute_match_score(
                query, query_stems, attr_type
            )
            
            if attr_score * weight > highest_score:
                # Try to extract the new value
                new_value = self._extract_new_value(query, attr_type)
                if new_value:
                    highest_score = attr_score * weight
                    best_match = (attr_type, new_value, highest_score)
                    
        return best_match if highest_score >= 0.6 else None
        
    def _get_stems(self, text: str) -> List[str]:
        """Get stemmed words from text, using cache for performance."""
        words = text.split()
        stems = []
        for word in words:
            if word not in self.stem_cache:
                self.stem_cache[word] = self.stemmer.stem(word)
            stems.append(self.stem_cache[word])
        return stems
        
    def _calculate_attribute_match_score(self, query: str, 
                                       query_stems: List[str], 
                                       attr_type: str) -> float:
        """Calculate how well the query matches an attribute type."""
        # Attribute-specific keywords
        keywords = {
            'title': {'title', 'name', 'called', 'rename'},
            'date': {'date', 'when', 'schedule', 'move', 'reschedule'},
            'description': {'description', 'details', 'about', 'notes'},
            'priority': {'priority', 'importance', 'urgent', 'critical'}
        }
        
        attr_keywords = keywords.get(attr_type, set())
        stemmed_keywords = {self.stemmer.stem(k) for k in attr_keywords}
        
        # Check for exact keyword matches
        exact_matches = sum(1 for k in attr_keywords if k in query.split())
        # Check for stemmed matches
        stem_matches = sum(1 for k in stemmed_keywords if k in query_stems)
        
        return (exact_matches + 0.8 * stem_matches) / (len(attr_keywords) + 0.1)
        
    def _extract_new_value(self, query: str, attr_type: str) -> Optional[str]:
        """
        Extract the new value for the attribute from the query.
        Uses heuristics based on attribute type.
        """
        # Common words that might appear before the new value
        value_indicators = {'to', 'as', 'with', 'for'}
        
        words = query.split()
        for i, word in enumerate(words):
            if word in value_indicators and i < len(words) - 1:
                return ' '.join(words[i + 1:])
                
        # If no indicator words found, try to extract based on attribute type
        if attr_type == 'date':
            # Look for date-like patterns at the end
            date_pattern = r'(?:to|for|on)?\s*(.+?)(?:\s*$)'
            match = re.search(date_pattern, query)
            if match:
                return match.group(1).strip()
                
        return None 