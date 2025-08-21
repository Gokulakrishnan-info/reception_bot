#!/usr/bin/env python3
"""
Test script to verify appointment scheduling functionality
"""

import logging
from ai_reception_bot import CalendarAgent, DirectoryAgent
from utils import extract_appointment_details, parse_time_string, parse_date_string

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def test_appointment_functionality():
    """Test the appointment scheduling functionality"""
    
    print("🧪 Testing Appointment Scheduling Functionality")
    print("=" * 50)
    
    # Initialize agents
    calendar_agent = CalendarAgent()
    directory_agent = DirectoryAgent()
    
    # Test 1: Extract appointment details
    print("\n1. Testing appointment details extraction:")
    test_input = "schedule an appointment with Ramu today at 3:00 PM"
    details = extract_appointment_details(test_input)
    print(f"Input: {test_input}")
    print(f"Extracted: {details}")
    
    # Test 2: Parse time and date
    print("\n2. Testing time and date parsing:")
    time_str = "3:00 PM"
    date_str = "today"
    
    parsed_time = parse_time_string(time_str)
    parsed_date = parse_date_string(date_str)
    
    print(f"Time '{time_str}' -> {parsed_time}")
    print(f"Date '{date_str}' -> {parsed_date}")
    
    # Test 3: Check if employee exists
    print("\n3. Testing employee lookup:")
    employee_name = "Ramu"
    employee = directory_agent.search_employee(employee_name)
    print(f"Employee '{employee_name}': {'Found' if employee else 'Not found'}")
    
    if employee:
        print(f"Employee details: {employee}")
    
    # Test 4: Check availability
    print("\n4. Testing availability check:")
    if employee and parsed_time and parsed_date:
        is_available, message = calendar_agent.check_availability(
            employee_name, parsed_date, parsed_time
        )
        print(f"Availability: {is_available} - {message}")
        
        # Test 5: Schedule appointment if available
        if is_available:
            print("\n5. Testing appointment scheduling:")
            success, result = calendar_agent.schedule_appointment(
                "Test User", employee_name, parsed_date, parsed_time
            )
            print(f"Scheduling result: {success} - {result}")
        
        # Test 6: Get available slots
        print("\n6. Testing available slots:")
        slots = calendar_agent.get_available_slots(employee_name, parsed_date)
        print(f"Available slots: {slots}")
    
    # Test 7: Check existing appointments
    print("\n7. Testing appointment lookup:")
    appointments = calendar_agent.check_appointment("Test User")
    print(f"Appointments for Test User: {appointments}")
    
    print("\n✅ Appointment functionality test completed!")

if __name__ == "__main__":
    test_appointment_functionality()
