import re
import logging
from typing import Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntentDetector:
    """
    Detects user intent from input messages and classifies them as conversational,
    task-related, or other specific intents.
    
    This allows the chatbot to respond appropriately to casual conversation
    versus calendar task operations. Conversational intents are routed to the
    LLM for dynamic response generation.
    """
    
    # Common greetings and conversational phrases
    CONVERSATIONAL_PATTERNS = [
        r'^(?:hi|hello|hey|greetings|howdy|good\s+(?:morning|afternoon|evening))(?:\s+.*)?$',
        r'^how\s+(?:are|is|have|was)\s+(?:you|your|the).*',
        r'^what(?:\'s|\s+is)\s+(?:up|new|going\s+on).*',
        r'^(?:tell|give)\s+me\s+(?:about|some).*',
        r'^(?:thanks|thank\s+you|ty|thx).*',
        r'^(?:nice|good|great)\s+to\s+(?:meet|see|talk\s+to)\s+you.*',
        r'^(?:how|what)\s+(?:do|can|could)\s+you\s+(?:work|do|help).*',
        r'^(?:who|what)\s+are\s+you.*',
        r'^(?:bye|goodbye|see\s+you|talk\s+(?:to\s+you|later)).*'
    ]
    
    # Task-related patterns
    TASK_PATTERNS = [
        r'(?:schedule|add|create|set\s+up|plan|book)\s+(?:a|an)?',
        r'(?:remind|reminder|remind\s+me)\s+(?:to|about)?',
        r'(?:meeting|appointment|event|task|todo|to\-do|call)\s+(?:with|for|at|on|about)?',
        r'(?:on|at|for|by)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        r'(?:on|at|for|by)\s+(?:tomorrow|next\s+week|next\s+month|today)',
        r'(?:on|at|for|by)\s+(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)|noon|midnight)',
        r'(?:due|deadline|by)\s+(?:date|time)?'
    ]
    
    # Edit-related patterns (already in edit_detector.py, but included here for completeness)
    EDIT_PATTERNS = [
        r'(?:change|update|modify|edit|alter)',
        r'(?:move|reschedule|postpone|advance)',
        r'(?:rename|retitle)',
        r'(?:delete|remove|cancel)'
    ]
    
    # Inquiry patterns for asking about tasks
    INQUIRY_PATTERNS = [
        r'(?:what|which|show|list|display)\s+(?:events|tasks|appointments|meetings)',
        r'(?:do\s+I\s+have|is\s+there|are\s+there)\s+(?:any|some)',
        r'(?:what(?:\'s|\s+is)\s+(?:on|in))\s+(?:my\s+)?(?:calendar|schedule)'
    ]
    
    def detect_intent(self, user_input: str) -> Tuple[str, float]:
        """
        Detect the intent of a user input and return the intent type and confidence score.
        
        Args:
            user_input: The user's input message
            
        Returns:
            Tuple of (intent_type, confidence_score) where intent_type is one of:
            - 'conversational': General conversation
            - 'task_creation': Creating a new task
            - 'edit_request': Modifying an existing task
            - 'inquiry': Asking about existing tasks
            - 'unknown': Couldn't determine intent
        """
        logger.info(f"Detecting intent for: {user_input}")
        
        # Clean and normalize the input
        cleaned_input = user_input.lower().strip()
        
        # Check for conversational patterns first
        for pattern in self.CONVERSATIONAL_PATTERNS:
            if re.search(pattern, cleaned_input, re.IGNORECASE):
                logger.info(f"Detected conversational intent (pattern: {pattern})")
                return 'conversational', 0.95
        
        # Check for task creation patterns
        task_matches = 0
        for pattern in self.TASK_PATTERNS:
            if re.search(pattern, cleaned_input, re.IGNORECASE):
                task_matches += 1
        
        # Check for edit patterns
        edit_matches = 0
        for pattern in self.EDIT_PATTERNS:
            if re.search(pattern, cleaned_input, re.IGNORECASE):
                edit_matches += 1
        
        # Check for inquiry patterns
        inquiry_matches = 0
        for pattern in self.INQUIRY_PATTERNS:
            if re.search(pattern, cleaned_input, re.IGNORECASE):
                inquiry_matches += 1
        
        # Determine the intent based on pattern matches
        if task_matches > 0:
            confidence = min(0.5 + (task_matches * 0.1), 0.95)
            logger.info(f"Detected task creation intent (confidence: {confidence})")
            return 'task_creation', confidence
        
        if edit_matches > 0:
            confidence = min(0.5 + (edit_matches * 0.1), 0.95)
            logger.info(f"Detected edit request intent (confidence: {confidence})")
            return 'edit_request', confidence
        
        if inquiry_matches > 0:
            confidence = min(0.5 + (inquiry_matches * 0.1), 0.95)
            logger.info(f"Detected inquiry intent (confidence: {confidence})")
            return 'inquiry', confidence
        
        # If no clear patterns matched, default to conversational with low confidence
        logger.info("No clear intent detected, defaulting to conversational with low confidence")
        return 'conversational', 0.3 