#!/usr/bin/env python3
"""
Utilities module for Modular AI Bot
Contains helper functions and utility methods
"""

import re
import json
import logging
from datetime import datetime, timedelta

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

def extract_appointment_details(user_input):
    """Extract appointment details from user input"""
    user_input_lower = user_input.lower()
    
    # Extract person name - specific patterns for appointment scheduling
    person_name = None
    appointment_name_patterns = [
        r"(?:schedule|book|make|set up|arrange)\s+(?:an?\s+)?(?:appointment|meeting|session)\s+(?:with|to meet|to see)\s+([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)",
        r"(?:appointment|meeting|session)\s+(?:with|to meet|to see)\s+([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)",
        r"(?:want to|need to|like to)\s+(?:schedule|book|make|set up|arrange)\s+(?:an?\s+)?(?:appointment|meeting|session)\s+(?:with|to meet|to see)\s+([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)",
        r"(?:with|to meet|to see)\s+([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)\s+(?:at|on|for)",
        r"([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)\s+(?:at|on|for)\s+(?:\d|today|tomorrow)",
        r"([A-Za-z][A-Za-z]+(?:\s+[A-Za-z][A-Za-z]+)*)\s+(?:today|tomorrow)\s+(?:at|for)"
    ]
    
    for pattern in appointment_name_patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            person_name = match.group(1).strip()
            break
    
    # If no specific appointment pattern found, try general name extraction
    if not person_name:
        person_name = extract_name_from_request(user_input)
    
    # Clean up the extracted name - remove common words that might be captured
    if person_name:
        # Remove common words that might be captured with the name
        cleanup_words = ['today', 'tomorrow', 'at', 'for', 'with', 'to', 'meet', 'see']
        name_parts = person_name.split()
        cleaned_parts = [part for part in name_parts if part.lower() not in cleanup_words]
        person_name = ' '.join(cleaned_parts).strip()
    
    # Extract time
    time_patterns = [
        r"(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)",
        r"(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)",
        r"(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)",
        r"(\d{1,2})\s*o'clock",
        r"(\d{1,2})\s*hrs",
        r"(\d{1,2})\s*hours"
    ]
    
    time_str = None
    for pattern in time_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            if len(match.groups()) == 3:  # hour:minute am/pm
                hour, minute, period = match.groups()
                minute = minute if minute else "00"
                time_str = f"{hour}:{minute} {period.upper()}"
            elif len(match.groups()) == 2:  # hour am/pm
                hour, period = match.groups()
                time_str = f"{hour}:00 {period.upper()}"
            break
    
    # Extract date
    date_patterns = [
        r"today",
        r"tomorrow", 
        r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        r"(\d{1,2})/(\d{1,2})/(\d{4})",
        r"(\d{1,2})-(\d{1,2})-(\d{4})",
        r"(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)",
        r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
    ]
    
    date_str = None
    for pattern in date_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            if pattern == r"today":
                date_str = "today"
            elif pattern == r"tomorrow":
                date_str = "tomorrow"
            elif pattern == r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)":
                date_str = match.group(1)
            else:
                date_str = match.group(0)
            break
    
    return {
        "person_name": person_name,
        "time": time_str,
        "date": date_str,
        "raw_input": user_input
    }

def parse_time_string(time_str):
    """Parse time string to datetime.time object"""
    if not time_str:
        return None
    
    try:
        # Handle various time formats
        time_str = time_str.lower().replace("a.m.", "am").replace("p.m.", "pm")
        
        # Parse time
        if ":" in time_str:
            time_part, period = time_str.split()
            hour, minute = map(int, time_part.split(":"))
        else:
            # Extract hour and assume minute is 0
            hour = int(re.search(r'\d+', time_str).group())
            minute = 0
            period = re.search(r'(am|pm)', time_str).group()
        
        # Convert to 24-hour format
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
            
        return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
    except Exception as e:
        logging.error(f"Error parsing time string '{time_str}': {e}")
        return None

def parse_date_string(date_str):
    """Parse date string to datetime.date object"""
    if not date_str:
        return None
    
    try:
        today = datetime.now().date()
        
        if date_str == "today":
            return today
        elif date_str == "tomorrow":
            return today + timedelta(days=1)
        elif date_str.lower() in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            # Find next occurrence of this weekday
            weekday_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }
            target_weekday = weekday_map[date_str.lower()]
            current_weekday = today.weekday()
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7
            return today + timedelta(days=days_ahead)
        else:
            # Try to parse specific date formats
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            # If all parsing fails, return None
            return None
    except Exception as e:
        logging.error(f"Error parsing date string '{date_str}': {e}")
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
