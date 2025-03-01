import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import logging
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaskMatcher:
    """
    Handles task matching with multiple strategies:
    1. Exact matching
    2. Relevancy scoring
    3. Fuzzy matching as fallback
    """
    
    # Minimum score required for a match to be considered valid
    MATCH_THRESHOLD = 0.6
    
    # Weights for different matching criteria
    WEIGHTS = {
        'title_exact': 100,
        'title_contains': 50,
        'description_exact': 80,
        'description_contains': 40,
        'date_match': 30,
        'recency': 20
    }
    
    def __init__(self):
        # Cache for recently matched tasks
        self.recent_matches = {}
        
    def find_task(self, query: str, tasks_dict: Dict[str, List[Dict]], 
                  context: Optional[Dict] = None) -> Tuple[Optional[Dict], str, float]:
        """
        Find the most relevant task using multiple matching strategies.
        
        Args:
            query: User's search/edit query
            tasks_dict: Dictionary of tasks organized by date
            context: Optional context for matching (e.g., date range)
            
        Returns:
            Tuple of (matched_task, task_date, relevance_score)
        """
        logger.info(f"Finding task for query: {query}")
        
        # Clean and tokenize the query
        clean_query = self._clean_text(query)
        query_terms = set(clean_query.split())
        
        # Remove common words that don't help with matching
        stop_words = {'the', 'to', 'and', 'it', 'make', 'change', 'edit', 'move', 
                     'be', 'on', 'for', 'in', 'at', 'please', 'would', 'could'}
        query_terms = query_terms - stop_words
        
        logger.debug(f"Cleaned query terms: {query_terms}")
        
        best_match = None
        best_date = None
        highest_score = 0
        
        # Try exact matching first
        exact_match = self._find_exact_match(query_terms, tasks_dict)
        if exact_match:
            logger.info("Found exact match")
            return exact_match
            
        # If no exact match, try relevancy scoring
        for date_str, date_tasks in tasks_dict.items():
            for task in date_tasks:
                score = self._calculate_relevance_score(
                    query_terms=query_terms,
                    task=task,
                    date_str=date_str,
                    context=context
                )
                
                logger.debug(f"Task: {task['title']}, Date: {date_str}, Score: {score}")
                
                if score > highest_score:
                    highest_score = score
                    best_match = task
                    best_date = date_str
        
        # Only return match if it meets threshold
        if highest_score >= self.MATCH_THRESHOLD:
            logger.info(f"Found best match: {best_match['title']} with score {highest_score}")
            # Cache this match for future reference
            self._cache_match(best_match['group_id'], {
                'task': best_match,
                'date': best_date,
                'score': highest_score,
                'timestamp': datetime.now()
            })
            return best_match, best_date, highest_score
            
        logger.warning("No suitable match found")
        return None, None, 0
        
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for matching."""
        # Convert to lowercase
        text = text.lower()
        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
        
    def _find_exact_match(self, query_terms: set, tasks_dict: Dict) -> Optional[Tuple[Dict, str, float]]:
        """Try to find an exact match based on title or description."""
        for date_str, date_tasks in tasks_dict.items():
            for task in date_tasks:
                title_terms = set(self._clean_text(task['title']).split())
                desc_terms = set(self._clean_text(task.get('description', '')).split())
                
                # Check for exact title match
                if query_terms == title_terms:
                    return task, date_str, 1.0
                    
                # Check for exact description match
                if query_terms == desc_terms:
                    return task, date_str, 0.9
                    
        return None
        
    def _calculate_relevance_score(self, query_terms: set, task: Dict, 
                                 date_str: str, context: Optional[Dict]) -> float:
        """
        Calculate relevance score based on multiple criteria.
        
        Scoring factors:
        - Exact matches in title/description
        - Partial matches
        - Date proximity
        - Recent interactions
        """
        score = 0
        
        # Title matching
        title_terms = set(self._clean_text(task['title']).split())
        matching_title_terms = query_terms & title_terms
        
        if query_terms == title_terms:
            score += self.WEIGHTS['title_exact']
        else:
            score += len(matching_title_terms) * self.WEIGHTS['title_contains']
            
        # Description matching
        if task.get('description'):
            desc_terms = set(self._clean_text(task['description']).split())
            matching_desc_terms = query_terms & desc_terms
            
            if query_terms == desc_terms:
                score += self.WEIGHTS['description_exact']
            else:
                score += len(matching_desc_terms) * self.WEIGHTS['description_contains']
                
        # Date proximity scoring
        task_date = datetime.strptime(date_str, '%Y-%m-%d')
        current_date = datetime.now()
        days_diff = abs((task_date - current_date).days)
        if days_diff < 7:  # Boost score for recent/upcoming tasks
            score += (7 - days_diff) * self.WEIGHTS['recency']
            
        # Consider recent interactions
        if task['group_id'] in self.recent_matches:
            recent_match = self.recent_matches[task['group_id']]
            time_diff = (datetime.now() - recent_match['timestamp']).total_seconds()
            if time_diff < 300:  # Within last 5 minutes
                score *= 1.2  # 20% boost
                
        # Normalize score to 0-1 range
        max_possible_score = sum(self.WEIGHTS.values())
        normalized_score = score / max_possible_score
        
        return normalized_score
        
    def _cache_match(self, group_id: str, match_data: Dict):
        """Cache a matched task for future reference."""
        self.recent_matches[group_id] = match_data
        # Clean old cache entries
        current_time = datetime.now()
        self.recent_matches = {
            k: v for k, v in self.recent_matches.items()
            if (current_time - v['timestamp']).total_seconds() < 3600  # 1 hour cache
        } 