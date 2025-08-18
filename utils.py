#!/usr/bin/env python3
"""
Utilities module for Modular AI Bot
Contains helper functions and utility methods
"""

import re
import json
import logging
from datetime import datetime

def extract_name_from_request(user_input):
    """Extract employee name from user input using regex patterns"""
    patterns = [
        # Meeting/visiting/lookup intents
        r"(?:want to\s+|need to\s+|like to\s+)?(?:meet|see|visit|talk to|speak to|call|connect with|ping)\s+([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)",
        r"(?:looking for|searching for|find)\s+([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)",
        r"(?:what is|tell me|get|find|search for|show me|give me|provide|what's)\s+(?:the\s+)?(?:email|phone|department|position|salary|joining date|join date|details?|information?)\s+(?:of|for|about)\s+([a-zA-Z\s]+)",
        r"(?:email|phone|department|position|salary|joining date|join date|details?|information?)\s+(?:of|for|about)\s+([a-zA-Z\s]+)",
        r"([a-zA-Z\s]+)\s+(?:email|phone|department|position|salary|joining date|join date)",
        r"([a-zA-Z\s]+)\s+(?:details?|information?)",
        r"who\s+is\s+([a-zA-Z\s]+)",
        r"([a-zA-Z\s]+)\s+(?:is|works|employee)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def normalize_e164(phone_number, default_country_code="+91"):
    """Normalize phone number to E.164 format"""
    if not phone_number:
        return None
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', str(phone_number))
    
    # If it starts with country code, return as is
    if digits_only.startswith('91') and len(digits_only) == 12:
        return f"+{digits_only}"
    
    # If it's a 10-digit number, assume India (+91)
    if len(digits_only) == 10:
        return f"+91{digits_only}"
    
    # If it's already in E.164 format, return as is
    if digits_only.startswith('91') and len(digits_only) == 12:
        return f"+{digits_only}"
    
    # Default fallback
    return f"{default_country_code}{digits_only}"

def extract_json_string(text):
    """Extract JSON string from text response"""
    try:
        # Look for JSON-like patterns
        json_pattern = r'\{[^{}]*"[^"]*"[^{}]*\}'
        matches = re.findall(json_pattern, text)
        
        if matches:
            # Try to parse the first match
            for match in matches:
                try:
                    parsed = json.loads(match)
                    return match
                except json.JSONDecodeError:
                    continue
        
        # If no valid JSON found, return the original text
        return text
    except Exception as e:
        logging.error(f"Error extracting JSON: {e}")
        return text

def fallback_extract_field_name(user_input):
    """Fallback method to extract field and name if AI doesn't return valid JSON"""
    # Field mapping with synonyms
    field_mapping = {
        "email": ["email", "email id", "email address", "mail", "e-mail"],
        "department": ["department", "dept", "team", "division", "unit"],
        "phone": ["phone", "phone number", "mobile", "mobile number", "contact", "contact number", "telephone"],
        "salary": ["salary", "pay", "ctc", "compensation", "earnings", "income"],
        "position": ["position", "role", "job title", "designation", "title"],
        "join_date": ["joining date", "join date", "hire date", "start date", "date of joining"]
    }
    
    # Default field
    field = "name"
    
    # Check for field keywords in user input
    user_input_lower = user_input.lower()
    for field_key, synonyms in field_mapping.items():
        if any(synonym in user_input_lower for synonym in synonyms):
            field = field_key
            break
    
    # Extract name using regex patterns
    name_patterns = [
        r"(?:what is|tell me|get|find|search for|show me|give me|provide|what's)\s+(?:the\s+)?(?:email|phone|department|position|salary|joining date|join date|details?|information?)\s+(?:of|for|about)\s+([a-zA-Z\s]+)",
        r"(?:email|phone|department|position|salary|joining date|join date|details?|information?)\s+(?:of|for|about)\s+([a-zA-Z\s]+)",
        r"([a-zA-Z\s]+)\s+(?:email|phone|department|position|salary|joining date|join date)",
        r"([a-zA-Z\s]+)\s+(?:details?|information?)",
        r"who\s+is\s+([a-zA-Z\s]+)",
        r"([a-zA-Z\s]+)\s+(?:is|works|employee)",
    ]
    
    name = None
    for pattern in name_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            break
    
    return {"field": field or "name", "name": name}

def get_time_greeting():
    """Get appropriate greeting based on current time"""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"

def _get_ordinal(n):
    """Convert number to ordinal form (1st, 2nd, 3rd, etc.)"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"
