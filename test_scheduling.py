#!/usr/bin/env python3
"""
Test script for appointment scheduling functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_reception_bot import CalendarAgent
from utils import extract_appointment_details, parse_time_string, parse_date_string

def test_appointment_extraction():
    """Test appointment details extraction"""
    print("Testing appointment details extraction...")
    
    test_inputs = [
        "I want to schedule a meeting with Ramu at 3:00 p.m. today",
        "Can I meet with John tomorrow at 2:30 PM?",
        "Schedule appointment with Sarah next Monday at 10 AM",
        "I need to see Mike at 4:00 p.m. today"
    ]
    
    for test_input in test_inputs:
        print(f"\nInput: {test_input}")
        details = extract_appointment_details(test_input)
        print(f"Extracted: {details}")
        
        if details["time"]:
            parsed_time = parse_time_string(details["time"])
            print(f"Parsed time: {parsed_time}")
        
        if details["date"]:
            parsed_date = parse_date_string(details["date"])
            print(f"Parsed date: {parsed_date}")

def test_calendar_agent():
    """Test calendar agent functionality"""
    print("\n\nTesting Calendar Agent...")
    
    # Initialize calendar agent
    calendar = CalendarAgent()
    
    # Test availability check
    print("\nTesting availability check...")
    is_available, message = calendar.check_availability("Ramu", "today", "15:00")
    print(f"Ramu available at 3 PM today: {is_available} - {message}")
    
    # Test scheduling
    print("\nTesting appointment scheduling...")
    success, result = calendar.schedule_appointment("TestUser", "Ramu", "today", "15:00")
    print(f"Schedule appointment: {success} - {result}")
    
    # Test getting available slots
    print("\nTesting available slots...")
    slots = calendar.get_available_slots("Ramu", "today")
    print(f"Available slots for Ramu today: {slots}")

if __name__ == "__main__":
    test_appointment_extraction()
    test_calendar_agent()
    print("\nTest completed!")
