#!/usr/bin/env python3
"""
Main AI Reception Bot Module
Coordinates all agents and handles the main logic
"""

import time
import logging
import re
import threading
from datetime import datetime
from sqlalchemy import text

from config import WAKE_WORD, ATTENDANCE_XLSX
from utils import extract_name_from_request, normalize_e164, get_time_greeting, _get_ordinal
from wake_word_agent import WakeWordAgent
from face_recognition_agent import FaceRecognitionAgent
from chat_agent import ChatAgent
from voice_agent import VoiceAgent
from enhanced_avatar_agent import EnhancedAvatarAgent as AvatarAgent
from twilio_sms import send_sms

class CalendarAgent:
    """Agent 5: Calendar Integration (Placeholder)"""
    
    def __init__(self):
        self.appointments = {}  # Placeholder for calendar data
        
    def check_appointment(self, person_name, date=None):
        """Check if person has appointment (placeholder)"""
        # This would integrate with Google Calendar or Outlook API
        logging.info(f" Checking appointment for {person_name}")
        return f"I found an appointment for {person_name} at 2:00 PM today."
        
    def schedule_appointment(self, person_name, time, date):
        """Schedule appointment (placeholder)"""
        logging.info(f" Scheduling appointment for {person_name}")
        return f"Appointment scheduled for {person_name} on {date} at {time}."

class DirectoryAgent:
    """Agent 6: Employee Directory Lookup"""
    
    def __init__(self):
        from config import DB_ENGINE, BACKUP_CSV
        from sqlalchemy import text
        import pandas as pd
        
        self.engine = DB_ENGINE
        self.backup_csv = BACKUP_CSV
        
    def search_employee(self, name, field=None):
        """Search employee in database or CSV"""
        try:
            # Try MySQL first
            with self.engine.connect() as conn:
                if field:
                    query = text(f"SELECT {field} FROM employees WHERE LOWER(name) = LOWER(:name)")
                    result = conn.execute(query, {"name": name}).fetchone()
                else:
                    query = text("SELECT * FROM employees WHERE LOWER(name) = LOWER(:name)")
                    result = conn.execute(query, {"name": name}).fetchone()
                    
                if result:
                    # Normalize SQLAlchemy Row to dictionary
                    try:
                        row_dict = dict(result._mapping)
                    except Exception:
                        try:
                            row_dict = dict(result)
                        except Exception:
                            # Fallback to raw result if conversion fails
                            row_dict = { }
                    # Ensure a standard 'mobile' key exists if phone number is stored under other names
                    if 'mobile' not in row_dict:
                        for alt_key in ['phone_number', 'phone', 'mobile_number', 'contact']:
                            if alt_key in row_dict:
                                row_dict['mobile'] = row_dict[alt_key]
                                break
                    return row_dict
                    
        except Exception as e:
            logging.warning(f"Database error: {e}")
            
        # Fallback to CSV
        try:
            import pandas as pd
            df = pd.read_csv(self.backup_csv)
            row = df[df["name"].str.lower() == name.lower()]
            if not row.empty:
                return row.iloc[0].to_dict()
        except Exception as e:
            logging.error(f"CSV error: {e}")
            
        return None
        
    def get_department_info(self, department):
        """Get department information"""
        try:
            with self.engine.connect() as conn:
                query = text("SELECT * FROM employees WHERE LOWER(department) = LOWER(:dept)")
                results = conn.execute(query, {"dept": department}).fetchall()
                return results
        except:
            return []
            
    def find_employee_by_query(self, query):
        """Find employee based on natural language query"""
        # This would use NLP to extract employee name and field
        return self.search_employee("John Doe", "email")  # Placeholder

class AttendanceAgent:
    """Agent 7: Attendance logging and lookup using Excel file."""

    def __init__(self, xlsx_path: str = ATTENDANCE_XLSX):
        self.xlsx_path = xlsx_path

    def _ensure_file(self):
        import os
        import pandas as pd
        # Ensure parent directory exists
        parent_dir = os.path.dirname(self.xlsx_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        # Create the file if missing
        if not os.path.exists(self.xlsx_path):
            df = pd.DataFrame(columns=["date", "name", "arrival_time"])
            df.to_excel(self.xlsx_path, index=False)

    def log_arrival(self, name: str):
        """Log arrival for a known face if not already logged today."""
        try:
            import os
            import pandas as pd
            self._ensure_file()
            today = datetime.now().date()
            now_time = datetime.now().strftime("%I:%M %p").lstrip("0")
            df = pd.read_excel(self.xlsx_path)
            # Normalize columns
            if not {"date", "name", "arrival_time"}.issubset(df.columns):
                df = pd.DataFrame(columns=["date", "name", "arrival_time"])  # reset if malformed
            # Check if already logged
            mask = (pd.to_datetime(df["date"]).dt.date == today) & (df["name"].str.lower() == name.lower())
            if not mask.any():
                df.loc[len(df)] = [today, name, now_time]
                df.to_excel(self.xlsx_path, index=False)
                logging.info(f"Attendance logged for {name} at {now_time}")
            else:
                logging.info(f"Attendance already logged for {name} today")
        except Exception as e:
            logging.warning(f"Failed to log attendance for {name}: {e}")

    def lookup_today(self, name: str):
        """Return arrival time string if present today, else None."""
        try:
            import os
            import pandas as pd
            if not os.path.exists(self.xlsx_path):
                return None
            df = pd.read_excel(self.xlsx_path)
            if df.empty:
                return None
            today = datetime.now().date()
            mask = (pd.to_datetime(df["date"]).dt.date == today) & (df["name"].str.lower() == name.lower())
            if mask.any():
                # If there are multiple entries (edge case), return the earliest time today
                sub = df[mask].copy()
                if "arrival_time" not in sub.columns:
                    return None
                # Build full datetime strings for robust comparison
                try:
                    sub["arrival_dt"] = pd.to_datetime(
                        pd.to_datetime(sub["date"]).dt.strftime("%Y-%m-%d") + " " + sub["arrival_time"].astype(str),
                        errors="coerce"
                    )
                    earliest = sub.nsmallest(1, "arrival_dt").iloc[0]
                    # Return only the time portion as originally stored
                    return str(earliest["arrival_time"]) if pd.notna(earliest["arrival_dt"]) else str(earliest["arrival_time"]) 
                except Exception:
                    # Fallback: return the first occurrence if parsing fails
                    row = sub.iloc[0]
                    return str(row.get("arrival_time"))
            return None
        except Exception as e:
            logging.warning(f"Attendance lookup failed for {name}: {e}")
            return None
    
    def get_all_present_today(self):
        """Return list of all employees present today with their arrival times."""
        try:
            import os
            import pandas as pd
            if not os.path.exists(self.xlsx_path):
                return []
            df = pd.read_excel(self.xlsx_path)
            if df.empty:
                return []
            today = datetime.now().date()
            mask = pd.to_datetime(df["date"]).dt.date == today
            present_employees = df[mask].copy()
            if present_employees.empty:
                return []
            # If duplicates exist for a name, keep the earliest arrival for today
            try:
                present_employees["arrival_dt"] = pd.to_datetime(
                    pd.to_datetime(present_employees["date"]).dt.strftime("%Y-%m-%d") + " " + present_employees["arrival_time"].astype(str),
                    errors="coerce"
                )
                present_employees.sort_values(["name", "arrival_dt"], inplace=True)
                earliest = present_employees.groupby("name", as_index=False).first()[["name", "arrival_time"]]
                return earliest.to_dict('records')
            except Exception:
                # Fallback without de-dup
                return present_employees[["name", "arrival_time"]].to_dict('records')
        except Exception as e:
            logging.warning(f"Failed to get present employees: {e}")
            return []

class AIReceptionBot:
    """Main AI Reception Bot that coordinates all agents"""
    
    def __init__(self):
        # Initialize all agents
        self.wake_agent = WakeWordAgent(WAKE_WORD)
        self.face_agent = FaceRecognitionAgent()
        self.chat_agent = ChatAgent()
        self.calendar_agent = CalendarAgent()
        self.directory_agent = DirectoryAgent()
        self.voice_agent = VoiceAgent()
        self.avatar_agent = AvatarAgent()  # Add PyQt6 avatar
        self.attendance_agent = AttendanceAgent(ATTENDANCE_XLSX)
        
        # State management
        self.is_active = False
        self.current_user = None
        self.should_stop = False  # Flag to stop the bot gracefully
        
    def row_to_dict(self, employee):
        """Convert SQLAlchemy Row or other mapping to a plain dict."""
        if isinstance(employee, dict):
            return employee
        try:
            return dict(employee._mapping)  # SQLAlchemy Row
        except Exception:
            try:
                return dict(employee)
            except Exception:
                return {}

    def normalize_e164(self, mobile_number, default_country_code="+91"):
        """Normalize a phone number to E.164. Assumes India (+91) if no country code.
        Returns None if cannot be normalized.
        """
        return normalize_e164(mobile_number, default_country_code)

    def get_mobile_from_employee(self, employee):
        """Extract and normalize mobile number from an employee record (dict or Row)."""
        data = self.row_to_dict(employee)
        # Prefer unified 'mobile' key; fall back to known alternatives
        mobile = (
            data.get('mobile')
            or data.get('phone_number')
            or data.get('phone')
            or data.get('mobile_number')
            or data.get('contact')
        )
        mobile_e164 = self.normalize_e164(mobile)
        return mobile_e164

    def get_greeting(self, name, is_employee=True):
        """Generate appropriate greeting based on time and user type"""
        time_greeting = get_time_greeting()
            
        if is_employee:
            greeting = f"Hi {name}, {time_greeting}! How can I assist you?"
            self.voice_agent.speak(greeting)
            return greeting
        else:
            greeting = f"Hi, {time_greeting}! How may I assist you?"
            self.voice_agent.speak(greeting)
            return greeting
            
    def conversation_loop(self, user_name, is_employee=True):
        """Main conversation loop with realistic receptionist behavior"""
        pending_input = None
        
        while True:
            # Check if we should stop
            if hasattr(self, 'should_stop') and self.should_stop:
                logging.info("🛑 Conversation loop shutdown requested")
                break
            
            # Get user input
            if pending_input:
                user_input = pending_input
                pending_input = None
                logging.info(f"📝 Processing pending input: {user_input}")
            else:
                # Listen for user input
                self.avatar_agent.show_listening()
                user_input, questions = self.voice_agent.listen_for_multiple_questions()
                self.avatar_agent.show_idle()

            # If we have parsed questions, handle them first (even if raw user_input is empty)
            if questions and len(questions) >= 1:
                if len(questions) > 1:
                    logging.info(f"📝 Processing {len(questions)} separate questions")
                    self.voice_agent.speak("I heard you ask several questions. Let me address them one by one.")
                    time.sleep(0.5)
                # Process each question separately
                for i, question in enumerate(questions, 1):
                    if len(questions) > 1 and i > 1:
                        self.avatar_agent.show_speaking()
                        self.voice_agent.speak(f"Now for your {_get_ordinal(i)} question:")
                        self.avatar_agent.show_idle()
                        time.sleep(0.3)
                    response, is_handled = self.process_query(question, user_name, is_employee)
                    if response:
                        self.avatar_agent.show_speaking()
                        self.voice_agent.speak(response)
                        self.avatar_agent.show_idle()
                        time.sleep(0.5)
                logging.info("Questions processed - continuing conversation naturally...")
                continue

            # No parsed questions and no raw input -> retry once, then gracefully stay active
            if not user_input:
                self.voice_agent.speak("I didn't catch that. Could you please repeat?")
                time.sleep(0.5)
                self.avatar_agent.show_listening()
                user_input, questions = self.voice_agent.listen_for_multiple_questions()
                self.avatar_agent.show_idle()
                # If we now have questions, loop to top to handle them
                if questions and len(questions) >= 1:
                    continue
                if not user_input:
                    # Don't exit to sleep immediately; just continue listening loop
                    logging.info("No input after retry; staying active and waiting for next utterance...")
                    continue

            # Single question - process normally
            response, is_handled = self.process_query(user_input, user_name, is_employee)
            if response:
                self.avatar_agent.show_speaking()
                self.voice_agent.speak(response)
                self.avatar_agent.show_idle()
                time.sleep(0.5)
            logging.info("Single question processed - continuing conversation naturally...")
            continue
            
            logging.info(f"User ({user_name}): {user_input}")
            
            # Check for goodbye/exit commands
            if any(word in user_input.lower() for word in ["bye", "goodbye", "see you", "exit", "leave"]):
                self.voice_agent.speak("Okay, feel free to ask me anytime. Have a great day!")
                break
        
    def extract_name_from_request(self, user_input):
        """Extract name from user input using enhanced regex patterns"""
        return extract_name_from_request(user_input)

    def check_employee_presence(self, employee):
        # Simulate presence (random or always present for now)
        # Replace with real attendance check if available
        import random
        return random.choice([True, False])

    def handle_meeting_request(self, user_input):
        name = self.extract_name_from_request(user_input)
        if not name:
            response = "I'm sorry, I didn't catch the name. Could you please repeat the name of the person you want to meet?"
            self.avatar_agent.show_speaking()
            self.voice_agent.speak(response)
            self.avatar_agent.show_idle()
            return
        employee = self.directory_agent.search_employee(name)
        if not employee:
            response = f"Sorry, I couldn't find anyone named {name} in our employee directory."
            self.avatar_agent.show_speaking()
            self.voice_agent.speak(response)
            self.avatar_agent.show_idle()
            return
        # Check presence
        is_present = self.check_employee_presence(employee)
        if is_present:
            response = f"Yes, {name} is available. I've notified them that you're here. Please wait a moment."
            self.avatar_agent.show_speaking()
            self.voice_agent.speak(response)
            self.avatar_agent.show_idle()
            # Use the imported send_sms function with normalized phone
            mobile = self.get_mobile_from_employee(employee)
            if mobile:
                logging.info(f"Sending SMS to {name} at {mobile}")
                sms_sent = send_sms(mobile, "You have a visitor at the reception asking for you.")
                if not sms_sent:
                    logging.warning(f"SMS to {name} failed - likely trial account restriction")
            else:
                logging.info(f"No valid mobile number found for {name}")
        else:
            response = f"{name} is not in the office today. I will inform our receptionist, Alex. Please take a seat."
            self.avatar_agent.show_speaking()
            self.voice_agent.speak(response)
            self.avatar_agent.show_idle()

    def process_query(self, user_input, user_name, is_employee):
        """Process user query through appropriate agents"""
        sensitive_keywords = ["email", "mobile", "phone", "salary", "join", "joining date", "position"]
        user_lower = user_input.lower()

        # Department queries FIRST for everyone
        if self.chat_agent.is_department_query(user_input):
            logging.info(f"Processing department query: {user_input}")
            dept_result = self.chat_agent.process_department_query(user_input)
            response = dept_result["response"]
            representative = dept_result["representative"]
            department = dept_result["department"]

            # Send SMS notification to the department representative
            try:
                employee = self.directory_agent.search_employee(representative)
                if employee:
                    mobile = self.get_mobile_from_employee(employee)
                    if mobile:
                        logging.info(f"Sending SMS to {representative} at {mobile} for {department} assistance request")
                        sms_message = f"Reception: A visitor is asking about {department} department location. Please assist them."
                        send_sms(mobile, sms_message)
                    else:
                        logging.info(f"{representative} found but has no valid mobile number; skipping SMS")
                else:
                    logging.info(f"Could not find '{representative}' in directory; skipping SMS")
            except Exception as e:
                logging.warning(f"Failed to notify {representative} via SMS: {e}")

            return (response, False)

        # Employee detail queries must be handled BEFORE general knowledge for employees
        employee_detail_keywords = [
            "email", "email id", "mail", "gmail", "e-mail",
            "phone", "mobile", "department", "position", "detail"
        ]
        if is_employee and any(keyword in user_lower for keyword in employee_detail_keywords):
            logging.info("Search for Employee Details (employee priority)")
            self.avatar_agent.show_processing()
            self.chat_agent.current_user = user_name
            response = self.chat_agent.process_employee_query(user_input)
            return (response, False)

        # General knowledge keywords (used to allow only employees to ask)
        general_question_keywords = [
            "who is", "what is", "when is", "where is", "how is", "why is",
            "who was", "what was", "when was", "where was", "how was", "why was",
            "who are", "what are", "when are", "where are", "how are", "why are",
            "president", "prime minister", "capital", "country", "city", "weather",
            "time", "date", "today", "tomorrow", "yesterday", "current", "latest",
            "news", "information", "fact", "facts", "tell me about", "explain",
            "define", "meaning", "definition", "history", "background"
        ]

        # If it's a general knowledge question
        if any(keyword in user_lower for keyword in general_question_keywords):
            if not is_employee:
                return ("Please ask where a department is or whom you want to meet.", False)
            logging.info("Processing General Knowledge Question (employee)")
            self.avatar_agent.show_thinking()
            response = self.chat_agent.process_general_query(user_input)
            return (response, False)
        
        # If unknown user asks for employee details (other than name), do not provide info
        if not is_employee and any(keyword in user_lower for keyword in sensitive_keywords):
            name = self.extract_name_from_request(user_input)
            if name:
                response = f"I'm sorry, I can't provide you that information. Do you want me to notify {name} that you are here?"
                self.avatar_agent.show_speaking()
                self.voice_agent.speak(response)
                self.avatar_agent.show_idle()
                # Listen for yes/no - allow complete responses
                self.avatar_agent.show_listening()
                follow_up = self.voice_agent.listen_until_complete(max_total_time=15)
                self.avatar_agent.show_idle()
                if follow_up and 'yes' in follow_up.lower():
                    employee = self.directory_agent.search_employee(name)
                    if employee:
                        mobile = self.get_mobile_from_employee(employee)
                        if mobile:
                            logging.info(f"Sending SMS to {name} at {mobile}")
                            sms_sent = send_sms(mobile, "You have a visitor at the reception asking for you.")
                            # Speak a consistent, user-friendly message regardless of SMS status
                            if not sms_sent:
                                logging.warning(f"SMS to {name} failed or not configured; proceeding without blocking user flow")
                            self.avatar_agent.show_speaking()
                            self.voice_agent.speak(f"I've notified {name}. Please wait in the reception.")
                            self.avatar_agent.show_idle()
                        else:
                            self.avatar_agent.show_speaking()
                            self.voice_agent.speak(f"Yes, {name} works here, but I couldn't notify them (no mobile number found).")
                            self.avatar_agent.show_idle()
                    else:
                        self.avatar_agent.show_speaking()
                        self.voice_agent.speak(f"Sorry, I couldn't find anyone named {name} in our employee directory. Please wait, our receptionist Alex will meet you shortly.")
                        self.avatar_agent.show_idle()
                else:
                    self.avatar_agent.show_speaking()
                    self.voice_agent.speak("Okay. If you need anything else, let me know.")
                    self.avatar_agent.show_idle()
                return ("", True)
            else:
                return ("I'm sorry, I didn't catch the name. Could you please repeat the name of the person you want to meet?", True)
        # If unknown user wants to meet/see/visit someone, notify immediately (robust)
        if not is_employee and any(word in user_lower for word in ["meet", "see", "visit", "talk to", "speak to", "looking for", "find", "call"]):
            name = self.extract_name_from_request(user_input)
            if name:
                logging.info(f"Looking for employee: {name}")
                employee = self.directory_agent.search_employee(name)
                if employee:
                    logging.info(f"Employee found: {employee}")
                    data = self.row_to_dict(employee)
                    logging.info(f"Available fields: {list(data.keys())}")
                    mobile = self.get_mobile_from_employee(data)
                    logging.info(f"Mobile number (normalized): {mobile}")
                    if mobile:
                        logging.info(f"Sending SMS to {name} at {mobile}")
                        sms_sent = send_sms(mobile, "You have a visitor at the reception asking for you.")
                        if sms_sent:
                            self.avatar_agent.show_speaking()
                            self.voice_agent.speak(f"I've notified {name}. Please wait in the reception.")
                            self.avatar_agent.show_idle()
                        else:
                            logging.warning(f"SMS to {name} failed or not configured; proceeding without blocking user flow")
                            self.avatar_agent.show_speaking()
                            self.voice_agent.speak(f"I've notified {name}. Please wait in the reception.")
                            self.avatar_agent.show_idle()
                        # Mark as handled but allow outer loop to continue and ask follow-up
                        return ("", True)
                    else:
                        logging.info(f"No mobile number found for {name}")
                        self.avatar_agent.show_speaking()
                        self.voice_agent.speak(f"Yes, {name} works here, but I couldn't notify them (no mobile number found).")
                        self.avatar_agent.show_idle()
                        return ("", True)
                else:
                    logging.info(f"Employee {name} not found in database")
                    self.avatar_agent.show_speaking()
                    self.voice_agent.speak(f"Sorry, I couldn't find anyone named {name} in our employee directory.")
                    self.avatar_agent.show_idle()
                    return ("", True)
            else:
                return ("I'm sorry, I didn't catch the name. Could you please repeat the name of the person you want to meet?", True)
        # For visitors: restrict to dept/location or meeting requests
        if not is_employee:
            # If the input looks like a general knowledge question, politely restrict
            if any(keyword in user_lower for keyword in general_question_keywords):
                return ("Please ask where a department is or whom you want to meet.", False)
            # Allow very limited name verification only if phrased explicitly
            name = self.extract_name_from_request(user_input)
            if name and any(phrase in user_lower for phrase in ["does", "do", "work here", "is here", "present", "in this company", "employee"]):
                employee = self.directory_agent.search_employee(name)
                if employee:
                    return (f"Yes, {name} works here.", False)
                else:
                    return (f"Sorry, I couldn't find anyone named {name} in our employee directory.", False)
            # Fallback restriction for visitors
            return ("Please ask where a department is or whom you want to meet.", False)
        # Normal logic for employees
        # Check for greetings first
        if any(greeting in user_input.lower() for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "how are you"]):
            # Show happy state for greetings
            self.avatar_agent.show_happy()
            return (self.chat_agent.process_greeting(user_input), False)
        # Check for appointment-related queries
        if any(word in user_input.lower() for word in ["appointment", "meeting", "schedule"]):
            # Show processing state while checking calendar
            self.avatar_agent.show_processing()
            response = self.calendar_agent.check_appointment(user_name)
            return (response, False)
        # (Department queries handled earlier and employee details handled above)
        # Check for employee queries (only if not a department query)
        if is_employee and any(keyword in user_lower for keyword in ["salary", "join", "joining date"]):
            logging.info("Search for Employee Details. ")
            # Show processing state while searching
            self.avatar_agent.show_processing()
            # Set the current user for the ChatAgent to enable access control
            self.chat_agent.current_user = user_name
            response = self.chat_agent.process_employee_query(user_input)
            return (response, False)
        # Check for meeting/visit requests
        if any(word in user_lower for word in ["meet", "see", "visit", "talk to", "speak to", "looking for", "find", "call"]):
            self.handle_meeting_request(user_input)
            return ("", True)
        
        # Rule-based quick answers for common facilities/directions
        lower_q = user_lower
        # Restroom directions
        if any(key in lower_q for key in ["rest room", "restroom", "washroom", "toilet"]):
            return ("The restroom is near the lift, just to your right.", False)

        # Check for employee presence queries
        presence_keywords = ["present", "here", "attendance", "came", "arrived", "in office", "at work"]
        if any(keyword in user_lower for keyword in presence_keywords):
            # Check for general "who is present" questions
            if any(word in user_lower for word in ["who", "employees", "people", "staff"]) and "present" in user_lower:
                logging.info("Checking all present employees today")
                present_employees = self.attendance_agent.get_all_present_today()
                if present_employees:
                    employee_list = []
                    for emp in present_employees:
                        employee_list.append(f"{emp['name']} (arrived at {emp['arrival_time']})")
                    response = f"Today, the following employees are present: {', '.join(employee_list)}."
                else:
                    response = "No employees are recorded as present today."
                return (response, False)
            
            # Extract employee name from the query
            name = self.extract_name_from_request(user_input)
            if name:
                logging.info(f"Checking attendance for {name}")
                arrival_time = self.attendance_agent.lookup_today(name)
                if arrival_time:
                    response = f"Yes, {name} is present today. They arrived at {arrival_time}."
                else:
                    response = f"No, {name} is not present today according to our attendance records."
                return (response, False)
            else:
                # If no specific name mentioned, ask for clarification
                response = "I can check attendance for specific employees. Please tell me the name of the person you want to check, or ask 'who is present today' for a list of all present employees."
                return (response, False)

        # General conversation (employees only)
        if is_employee:
            logging.info("Processing General Question (employee)")
            self.avatar_agent.show_thinking()
            response = self.chat_agent.process_general_query(user_input)
            return (response, False)
        else:
            return ("Please ask where a department is or whom you want to meet.", False)
        
    def run(self):
        """Main bot execution loop"""
        logging.info("🤖 AI Reception Bot Starting...")
        
        # Main loop 
        while True:
            try:
                # Check if we should stop
                if hasattr(self, 'should_stop') and self.should_stop:
                    logging.info("🛑 Bot shutdown requested by UI")
                    break
                
                # Wait for wake word
                if not self.wake_agent.detect_wake_word_with_instant_camera(self.face_agent):
                    break
                
                # Activate system immediately
                self.is_active = True
                self.avatar_agent.show_speaking()
                self.voice_agent.speak("Hello! I'm here to help you. Let me recognize you.")
                self.avatar_agent.show_idle()
                
                # Face recognition - starts immediately after wake word
                name, confidence = self.face_agent.recognize_facye_from_camera()
                is_employee = name != "Unknown"
                
                if is_employee:
                    self.current_user = name
                    # Time-based greeting for known face
                    time_greeting = get_time_greeting()
                    greeting = f"Hi {name}, {time_greeting}! How can I help you today?"
                    # Log attendance on recognition
                    try:
                        self.attendance_agent.log_arrival(name)
                    except Exception as e:
                        logging.warning(f"Attendance log failed for {name}: {e}")
                else:
                    self.current_user = "Visitor"
                    # Time-based greeting for unknown face
                    time_greeting = get_time_greeting()
                    greeting = f"Hello! Welcome. May I know your name, or how can I assist you today?"
                self.avatar_agent.show_speaking()
                self.voice_agent.speak(greeting)
                self.avatar_agent.show_idle()
                time.sleep(0.5)
                self.conversation_loop(name if is_employee else "Visitor", is_employee)
                
                # Return to sleep
                self.is_active = False
            except KeyboardInterrupt:
                logging.info("👋 Shutting down...")
                break
            except Exception as e:
                logging.exception(f"❌ Error in main loop: {e}")
                self.avatar_agent.show_speaking()
                self.voice_agent.speak("I encountered an error. Please try again.")
                self.avatar_agent.show_idle()
                time.sleep(0.7)
        # Cleanup
        if self.avatar_agent and not self.avatar_agent.closed:
            self.avatar_agent.on_close()
        
        # Clean up pre-initialized camera
        self.face_agent.cleanup_camera()
