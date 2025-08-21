#!/usr/bin/env python3
"""
Demonstration of Appointment Scheduling Functionality
"""

import logging
from ai_reception_bot import CalendarAgent, DirectoryAgent
from utils import extract_appointment_details, parse_time_string, parse_date_string

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

def demo_appointment_scheduling():
    """Demonstrate the appointment scheduling functionality"""
    
    print("🎯 Appointment Scheduling Demo")
    print("=" * 50)
    
    # Initialize agents
    calendar_agent = CalendarAgent()
    directory_agent = DirectoryAgent()
    
    # Demo scenarios
    scenarios = [
        {
            "input": "schedule an appointment with Ramu today at 2:00 PM",
            "description": "Schedule with available time"
        },
        {
            "input": "book a meeting with Ramu tomorrow at 3:30 PM", 
            "description": "Book meeting for tomorrow"
        },
        {
            "input": "I want to meet with Ramu today at 3:00 PM",
            "description": "Alternative phrasing"
        },
        {
            "input": "set up an appointment with John today at 10:00 AM",
            "description": "Employee not found scenario"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📋 Scenario {i}: {scenario['description']}")
        print(f"Input: {scenario['input']}")
        
        # Extract details
        details = extract_appointment_details(scenario['input'])
        print(f"Extracted: {details}")
        
        if not details["person_name"]:
            print("❌ Could not extract person name")
            continue
            
        if not details["time"] or not details["date"]:
            print("❌ Missing time or date")
            continue
        
        # Check if employee exists
        employee = directory_agent.search_employee(details["person_name"])
        if not employee:
            print(f"❌ Employee '{details['person_name']}' not found")
            continue
        
        # Parse time and date
        appointment_time = parse_time_string(details["time"])
        appointment_date = parse_date_string(details["date"])
        
        if not appointment_time or not appointment_date:
            print("❌ Could not parse time or date")
            continue
        
        # Check availability
        is_available, message = calendar_agent.check_availability(
            details["person_name"], appointment_date, appointment_time
        )
        
        if is_available:
            # Schedule the appointment
            success, result = calendar_agent.schedule_appointment(
                "Demo User", details["person_name"], appointment_date, appointment_time
            )
            
            if success:
                time_str = appointment_time.strftime("%I:%M %p")
                date_str = appointment_date.strftime("%B %d, %Y")
                print(f"✅ Appointment scheduled: {details['person_name']} on {date_str} at {time_str}")
            else:
                print(f"❌ Failed to schedule: {result}")
        else:
            print(f"❌ Not available: {message}")
            
            # Get alternative slots
            slots = calendar_agent.get_available_slots(details["person_name"], appointment_date)
            if slots:
                print(f"📅 Available slots: {', '.join(slots[:5])}")
            else:
                print("📅 No available slots on this date")
    
    print(f"\n🎉 Demo completed! Check the database for scheduled appointments.")

if __name__ == "__main__":
    demo_appointment_scheduling()
