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
import socket

from config import WAKE_WORD, ATTENDANCE_XLSX
from utils import extract_name_from_request, normalize_e164, get_time_greeting, _get_ordinal
from wake_word_agent import WakeWordAgent
# Prefer new import path if available without triggering static import errors
import importlib
try:
    FaceRecognitionAgent = importlib.import_module('face_agent').FaceRecognitionAgent
except Exception:
    # Backward compatibility
    from face_recognition_agent import FaceRecognitionAgent
from chat_agent import ChatAgent
from voice_agent import VoiceAgent
from enhanced_avatar_agent import EnhancedAvatarAgent as AvatarAgent
from twilio_sms import send_sms

class CalendarAgent:
    """Agent 5: Calendar Integration with actual appointment management"""
    
    def __init__(self):
        import sqlite3
        import os
        
        self.db_path = "appointments.db"
        # Optional MySQL engine (for real appointments)
        try:
            from config import DB_ENGINE
            self.mysql_engine = DB_ENGINE
        except Exception:
            self.mysql_engine = None
        
        # Initialize storage
        self.init_database()
        if self.mysql_engine is not None:
            self._init_mysql()

    def _init_mysql(self):
        """Initialize MySQL tables if engine is available."""
        try:
            from sqlalchemy import text
            with self.mysql_engine.begin() as conn:
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS appointments (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        requester_name VARCHAR(255) NOT NULL,
                        employee_name VARCHAR(255) NOT NULL,
                        appointment_date DATE NOT NULL,
                        appointment_time TIME NOT NULL,
                        duration_minutes INT DEFAULT 60,
                        status VARCHAR(32) DEFAULT 'scheduled',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                ))
                conn.execute(text(
                    """
                    CREATE TABLE IF NOT EXISTS employee_availability (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        employee_name VARCHAR(255) NOT NULL,
                        date DATE NOT NULL,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        is_available TINYINT(1) DEFAULT 1,
                        UNIQUE KEY uniq_emp_day (employee_name, date, start_time)
                    )
                    """
                ))
            logging.info("MySQL appointments tables ensured")
        except Exception as e:
            logging.warning(f"MySQL init skipped/failed: {e}")
        
    def init_database(self):
        """Initialize the appointments database"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create appointments table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_name TEXT NOT NULL,
                    employee_name TEXT NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    duration_minutes INTEGER DEFAULT 60,
                    status TEXT DEFAULT 'scheduled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create availability table for employee schedules
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS employee_availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT NOT NULL,
                    date DATE NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    is_available BOOLEAN DEFAULT 1,
                    UNIQUE(employee_name, date, start_time)
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("Appointments database initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize appointments database: {e}")
    
    def check_availability(self, employee_name, date, time, duration_minutes=60):
        """Check if an employee is available at the specified time"""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert date and time to datetime objects
            if isinstance(date, str):
                if date == "today":
                    date = datetime.now().date()
                elif date == "tomorrow":
                    date = (datetime.now() + timedelta(days=1)).date()
                else:
                    # Try to parse the date string
                    from utils import parse_date_string
                    parsed_date = parse_date_string(date)
                    if parsed_date:
                        date = parsed_date
                    else:
                        return False, "Invalid date format"
            
            if isinstance(time, str):
                from utils import parse_time_string
                parsed_time = parse_time_string(time)
                if parsed_time:
                    time = parsed_time
                else:
                    return False, "Invalid time format"
            
            # Convert to datetime for comparison
            appointment_datetime = datetime.combine(date, time)
            end_datetime = appointment_datetime + timedelta(minutes=duration_minutes)
            
            # Check if there are conflicting appointments (prefer MySQL when available)
            start_str = time.strftime('%H:%M:%S')
            end_str = end_datetime.time().strftime('%H:%M:%S')
            conflicts = []
            if getattr(self, 'mysql_engine', None) is not None:
                try:
                    from sqlalchemy import text
                    with self.mysql_engine.begin() as conn_mysql:
                        # Try new schema first: participant/date/time (assume 60-min duration)
                        rows = conn_mysql.execute(text(
                            """
                            SELECT 1 FROM appointments
                            WHERE participant = :emp
                              AND date = :dt
                              AND time < :end_ts
                              AND ADDTIME(time, '01:00:00') > :start_ts
                            LIMIT 1
                            """
                        ), {"emp": employee_name, "dt": date, "start_ts": start_str, "end_ts": end_str}).fetchall()
                        conflicts = rows
                        if not conflicts:
                            # Legacy schema fallback
                            rows = conn_mysql.execute(text(
                                """
                                SELECT 1 FROM appointments
                                WHERE employee_name = :emp
                                  AND appointment_date = :dt
                                  AND status = 'scheduled'
                                  AND appointment_time < :end_ts
                                  AND ADDTIME(appointment_time, SEC_TO_TIME(duration_minutes*60)) > :start_ts
                                LIMIT 1
                                """
                            ), {"emp": employee_name, "dt": date, "start_ts": start_str, "end_ts": end_str}).fetchall()
                            conflicts = rows
                except Exception as e:
                    logging.warning(f"MySQL conflict check failed, falling back to SQLite logic: {e}")
            
            if not conflicts:
                try:
                    # Try new schema: participant/date/time in SQLite (assume 60-min)
                    cursor.execute('''
                        SELECT 1 FROM appointments
                        WHERE participant = ? AND date = ?
                          AND time < ?
                          AND time(time, '+60 minutes') > ?
                        LIMIT 1
                    ''', (employee_name, date, end_str, start_str))
                    conflicts = cursor.fetchall()
                except Exception:
                    # Legacy schema
                    cursor.execute('''
                        SELECT * FROM appointments 
                        WHERE employee_name = ? 
                        AND appointment_date = ? 
                        AND status = 'scheduled'
                        AND (
                            (appointment_time < ? AND time(appointment_time, printf('+%d minutes', duration_minutes)) > ?)
                        )
                    ''', (employee_name, date, end_str, start_str))
                    conflicts = cursor.fetchall()
            
            # Check employee availability (working hours)
            availability = None
            if getattr(self, 'mysql_engine', None) is not None:
                try:
                    from sqlalchemy import text
                    with self.mysql_engine.begin() as conn_mysql:
                        row = conn_mysql.execute(text(
                            """
                            SELECT start_time, end_time FROM employee_availability
                            WHERE employee_name = :emp AND date = :dt AND is_available = 1
                            LIMIT 1
                            """
                        ), {"emp": employee_name, "dt": date}).fetchone()
                        availability = row
                except Exception as e:
                    logging.warning(f"MySQL availability check failed, falling back to SQLite: {e}")
            if availability is None:
                cursor.execute('''
                    SELECT start_time, end_time FROM employee_availability 
                    WHERE employee_name = ? AND date = ? AND is_available = 1
                ''', (employee_name, date))
                availability = cursor.fetchone()
            
            conn.close()
            
            if conflicts:
                return False, f"Employee has conflicting appointments at that time"
            
            # Default working hours if no specific availability set
            if not availability:
                # Assume 9 AM to 6 PM working hours
                start_time = datetime.strptime("09:00", "%H:%M").time()
                end_time = datetime.strptime("18:00", "%H:%M").time()
            else:
                start_time = datetime.strptime(availability[0], "%H:%M").time()
                end_time = datetime.strptime(availability[1], "%H:%M").time()
            
            # Check if appointment time is within working hours
            if time < start_time or end_datetime.time() > end_time:
                return False, f"Appointment time is outside working hours ({start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')})"
            
            return True, "Available"
            
        except Exception as e:
            logging.error(f"Error checking availability: {e}")
            return False, f"Error checking availability: {str(e)}"
    
    def schedule_appointment(self, requester_name, employee_name, date, time, duration_minutes=60):
        """Schedule an appointment if available"""
        try:
            # First check availability
            is_available, message = self.check_availability(employee_name, date, time, duration_minutes)
            
            if not is_available:
                return False, message
            
            # Schedule the appointment (prefer MySQL when available)
            inserted = False
            if getattr(self, 'mysql_engine', None) is not None:
                try:
                    from sqlalchemy import text
                    with self.mysql_engine.begin() as conn_mysql:
                        # Try new schema first: organizer/participant/date/time
                        conn_mysql.execute(text(
                            """
                            INSERT INTO appointments (organizer, participant, date, time)
                            VALUES (:org, :part, :dt, :tm)
                            """
                        ), {
                            "org": requester_name,
                            "part": employee_name,
                            "dt": date,
                            "tm": time.strftime('%H:%M:%S') if hasattr(time, 'strftime') else time,
                        })
                    inserted = True
                except Exception:
                    try:
                        # Fallback to legacy schema
                        with self.mysql_engine.begin() as conn_mysql:
                            conn_mysql.execute(text(
                                """
                                INSERT INTO appointments (requester_name, employee_name, appointment_date, appointment_time, duration_minutes)
                                VALUES (:rq, :emp, :dt, :tm, :dur)
                                """
                            ), {
                                "rq": requester_name,
                                "emp": employee_name,
                                "dt": date,
                                "tm": time.strftime('%H:%M:%S') if hasattr(time, 'strftime') else time,
                                "dur": duration_minutes,
                            })
                        inserted = True
                    except Exception as e2:
                        logging.warning(f"MySQL insert failed (both schemas), falling back to SQLite: {e2}")
            
            if not inserted:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                try:
                    # Try new schema first
                    cursor.execute('''
                        INSERT INTO appointments (organizer, participant, date, time)
                        VALUES (?, ?, ?, ?)
                    ''', (requester_name, employee_name, date, time.strftime('%H:%M:%S') if hasattr(time, 'strftime') else time))
                except Exception:
                    # Legacy schema
                    cursor.execute('''
                        INSERT INTO appointments (requester_name, employee_name, appointment_date, appointment_time, duration_minutes)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (requester_name, employee_name, date, time.strftime('%H:%M:%S') if hasattr(time, 'strftime') else time, duration_minutes))
                conn.commit()
                conn.close()
            
            logging.info(f"Appointment scheduled: {requester_name} with {employee_name} on {date} at {time}")
            return True, "Appointment scheduled successfully"
            
        except Exception as e:
            logging.error(f"Error scheduling appointment: {e}")
            return False, f"Error scheduling appointment: {str(e)}"
    
    def get_available_slots(self, employee_name, date, duration_minutes=60):
        """Get available time slots for an employee on a specific date"""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            if isinstance(date, str):
                from utils import parse_date_string
                parsed_date = parse_date_string(date)
                if parsed_date:
                    date = parsed_date
                else:
                    return []
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get working hours
            cursor.execute('''
                SELECT start_time, end_time FROM employee_availability 
                WHERE employee_name = ? AND date = ? AND is_available = 1
            ''', (employee_name, date))
            
            availability = cursor.fetchone()
            
            if not availability:
                # Default working hours: 9 AM to 6 PM
                start_time = datetime.strptime("09:00", "%H:%M").time()
                end_time = datetime.strptime("18:00", "%H:%M").time()
            else:
                start_time = datetime.strptime(availability[0], "%H:%M").time()
                end_time = datetime.strptime(availability[1], "%H:%M").time()
            
            # Get existing appointments
            cursor.execute('''
                SELECT appointment_time, duration_minutes FROM appointments 
                WHERE employee_name = ? AND appointment_date = ? AND status = 'scheduled'
                ORDER BY appointment_time
            ''', (employee_name, date))
            
            existing_appointments = cursor.fetchall()
            conn.close()
            
            # Generate time slots
            slots = []
            current_time = start_time
            
            while current_time <= end_time:
                slot_end = (datetime.combine(date, current_time) + timedelta(minutes=duration_minutes)).time()
                
                if slot_end <= end_time:
                    # Check if this slot conflicts with existing appointments
                    slot_available = True
                    for appt_time, appt_duration in existing_appointments:
                        # Convert string time to datetime.time if needed
                        if isinstance(appt_time, str):
                            appt_time_obj = datetime.strptime(appt_time, '%H:%M:%S').time()
                        else:
                            appt_time_obj = appt_time
                        
                        appt_end = (datetime.combine(date, appt_time_obj) + timedelta(minutes=appt_duration)).time()
                        
                        # Check for overlap
                        if not (slot_end <= appt_time_obj or current_time >= appt_end):
                            slot_available = False
                            break
                    
                    if slot_available:
                        slots.append(current_time.strftime("%I:%M %p"))
                
                # Move to next slot (30-minute intervals)
                current_time = (datetime.combine(date, current_time) + timedelta(minutes=30)).time()
            
            return slots
            
        except Exception as e:
            logging.error(f"Error getting available slots: {e}")
            return []
        
    def check_appointment(self, person_name, date=None):
        """Check existing appointments for a person (legacy method)"""
        try:
            appointments = []
            # Prefer MySQL if available
            if getattr(self, 'mysql_engine', None) is not None:
                from sqlalchemy import text
                with self.mysql_engine.begin() as conn_mysql:
                    if date:
                        rows = conn_mysql.execute(text(
                            """
                            SELECT requester_name, employee_name, appointment_date, appointment_time, status
                            FROM appointments
                            WHERE (requester_name = :p OR employee_name = :p) AND appointment_date = :dt
                            ORDER BY appointment_time
                            """
                        ), {"p": person_name, "dt": date}).fetchall()
                    else:
                        rows = conn_mysql.execute(text(
                            """
                            SELECT requester_name, employee_name, appointment_date, appointment_time, status
                            FROM appointments
                            WHERE requester_name = :p OR employee_name = :p
                            ORDER BY appointment_date, appointment_time
                            """
                        ), {"p": person_name}).fetchall()
                    appointments = rows
            
            if not appointments:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                if date:
                    cursor.execute('''
                        SELECT requester_name, employee_name, appointment_date, appointment_time, status FROM appointments 
                        WHERE (requester_name = ? OR employee_name = ?) AND appointment_date = ?
                        ORDER BY appointment_time
                    ''', (person_name, person_name, date))
                else:
                    cursor.execute('''
                        SELECT requester_name, employee_name, appointment_date, appointment_time, status FROM appointments 
                        WHERE requester_name = ? OR employee_name = ?
                        ORDER BY appointment_date, appointment_time
                    ''', (person_name, person_name))
                appointments = cursor.fetchall()
                conn.close()
            
            if appointments:
                return f"I found {len(appointments)} appointment(s) for {person_name}."
            else:
                return f"No appointments found for {person_name}."
                
        except Exception as e:
            logging.error(f"Error checking appointments: {e}")
            return f"Error checking appointments: {str(e)}"

    def fetch_today_appointments_for_user(self, user_name):
        """Return two lists: (as_organizer, as_participant) for today's date.
        Each item: (time_str, counterpart_name)
        Prefer MySQL, fallback to SQLite.
        """
        try:
            from datetime import datetime
            today = datetime.now().date()
            as_org = []
            as_part = []
            if getattr(self, 'mysql_engine', None) is not None:
                with self.mysql_engine.begin() as conn_mysql:
                    try:
                        # Try new schema
                        rows_org = conn_mysql.execute(text(
                            """
                            SELECT time, participant FROM appointments
                            WHERE organizer = :u AND date = :dt
                            ORDER BY time
                            """
                        ), {"u": user_name, "dt": today}).fetchall()
                        rows_part = conn_mysql.execute(text(
                            """
                            SELECT time, organizer FROM appointments
                            WHERE participant = :u AND date = :dt
                            ORDER BY time
                            """
                        ), {"u": user_name, "dt": today}).fetchall()
                        as_org = [(str(r[0]), str(r[1])) for r in rows_org]
                        as_part = [(str(r[0]), str(r[1])) for r in rows_part]
                    except Exception:
                        # Fallback to legacy schema
                        rows_org = conn_mysql.execute(text(
                            """
                            SELECT appointment_time, employee_name FROM appointments
                            WHERE requester_name = :u AND appointment_date = :dt AND status = 'scheduled'
                            ORDER BY appointment_time
                            """
                        ), {"u": user_name, "dt": today}).fetchall()
                        rows_part = conn_mysql.execute(text(
                            """
                            SELECT appointment_time, requester_name FROM appointments
                            WHERE employee_name = :u AND appointment_date = :dt AND status = 'scheduled'
                            ORDER BY appointment_time
                            """
                        ), {"u": user_name, "dt": today}).fetchall()
                        as_org = [(str(r[0]), str(r[1])) for r in rows_org]
                        as_part = [(str(r[0]), str(r[1])) for r in rows_part]
            else:
                import sqlite3
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                try:
                    try:
                        # Try new schema
                        cur.execute("SELECT time, participant FROM appointments WHERE organizer = ? AND date = ? ORDER BY time", (user_name, today))
                        as_org = [(t, p) for (t, p) in cur.fetchall()]
                        cur.execute("SELECT time, organizer FROM appointments WHERE participant = ? AND date = ? ORDER BY time", (user_name, today))
                        as_part = [(t, o) for (t, o) in cur.fetchall()]
                    except Exception:
                        # Fallback to legacy schema
                        cur.execute("SELECT appointment_time, employee_name FROM appointments WHERE requester_name = ? AND appointment_date = ? AND status = 'scheduled' ORDER BY appointment_time", (user_name, today))
                        as_org = [(t, p) for (t, p) in cur.fetchall()]
                        cur.execute("SELECT appointment_time, requester_name FROM appointments WHERE employee_name = ? AND appointment_date = ? AND status = 'scheduled' ORDER BY appointment_time", (user_name, today))
                        as_part = [(t, o) for (t, o) in cur.fetchall()]
                finally:
                    conn.close()
            # Normalize HH:MM strings
            def fmt(ts):
                try:
                    return datetime.strptime(str(ts), "%H:%M:%S").strftime("%I:%M %p")
                except Exception:
                    try:
                        return datetime.strptime(str(ts), "%H:%M").strftime("%I:%M %p")
                    except Exception:
                        return str(ts)
            as_org = [(fmt(t), n) for (t, n) in as_org]
            as_part = [(fmt(t), n) for (t, n) in as_part]
            return as_org, as_part
        except Exception as e:
            logging.warning(f"Failed to fetch today's appointments: {e}")
            return [], []

    def cancel_appointment(self, requester_name, date=None, time=None, employee_name=None):
        """Cancel appointments for requester. If date/time provided, cancel that slot; else cancel today's next.
        Returns (cancelled_count, message).
        """
        try:
            cancelled = 0
            # Prefer MySQL
            if getattr(self, 'mysql_engine', None) is not None:
                from sqlalchemy import text
                with self.mysql_engine.begin() as conn_mysql:
                    if date and time:
                        res = conn_mysql.execute(text(
                            """
                            DELETE FROM appointments
                            WHERE requester_name = :rq
                            AND appointment_date = :dt
                            AND appointment_time = :tm
                            """
                        ), {"rq": requester_name, "dt": date, "tm": time if isinstance(time, str) else time.strftime('%H:%M:%S')})
                        cancelled += res.rowcount if hasattr(res, 'rowcount') else 0
                    elif date:
                        res = conn_mysql.execute(text(
                            """
                            DELETE FROM appointments
                            WHERE requester_name = :rq AND appointment_date = :dt
                            """
                        ), {"rq": requester_name, "dt": date})
                        cancelled += res.rowcount if hasattr(res, 'rowcount') else 0
                    else:
                        # Default: cancel all today's
                        from datetime import datetime
                        today = datetime.now().date()
                        res = conn_mysql.execute(text(
                            """
                            DELETE FROM appointments
                            WHERE requester_name = :rq AND appointment_date = :dt
                            """
                        ), {"rq": requester_name, "dt": today})
                        cancelled += res.rowcount if hasattr(res, 'rowcount') else 0
                if cancelled:
                    return cancelled, "Appointment cancelled."
            # SQLite fallback
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if date and time:
                cursor.execute('''
                    DELETE FROM appointments
                    WHERE requester_name = ? AND appointment_date = ? AND appointment_time = ?
                ''', (requester_name, date, time if isinstance(time, str) else time.strftime('%H:%M:%S')))
            elif date:
                cursor.execute('''
                    DELETE FROM appointments
                    WHERE requester_name = ? AND appointment_date = ?
                ''', (requester_name, date))
            else:
                from datetime import datetime
                today = datetime.now().date()
                cursor.execute('''
                    DELETE FROM appointments
                    WHERE requester_name = ? AND appointment_date = ?
                ''', (requester_name, today))
            cancelled = cursor.rowcount
            conn.commit()
            conn.close()
            return cancelled, ("Appointment cancelled." if cancelled else "No matching appointment found.")
        except Exception as e:
            logging.error(f"Error cancelling appointment: {e}")
            return 0, f"Error cancelling appointment: {str(e)}"

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
    
    def __init__(self, avatar_agent=None, face_agent=None):
        # Initialize all agents
        self.wake_agent = WakeWordAgent(WAKE_WORD)
        self.face_agent = face_agent or FaceRecognitionAgent()
        self.chat_agent = ChatAgent()
        self.calendar_agent = CalendarAgent()
        self.directory_agent = DirectoryAgent()
        self.voice_agent = VoiceAgent()
        # Accept injected avatar, or create default EnhancedAvatarAgent
        self.avatar_agent = avatar_agent or AvatarAgent()
        self.attendance_agent = AttendanceAgent(ATTENDANCE_XLSX)
        
        # State management
        self.is_active = False
        self.current_user = None
        self.should_stop = False  # Flag to stop the bot gracefully
        # Lightweight conversation memory
        self.dialog_context = {}
        # Rotating fallback/help prompts to avoid repetition
        self._fallback_variations = [
            "I can assist with scheduling meetings, finding employees, or guiding you around.",
            "I'm here to help with appointments and directions. What would you like?",
            "I can help you schedule, locate employees, or provide directions.",
            "Need help with a meeting or directions? I can assist you.",
        ]
        self._fallback_idx = 0

    def say(self, text: str):
        """Speak with barge-in support if available; fall back to speak."""
        try:
            interrupted, partial = self.voice_agent.speak_with_interruption_detection(text)
            return interrupted, partial
        except Exception:
            self.voice_agent.speak(text)
            return False, None
    
    def get_rotating_help_prompt(self):
        """Return a help prompt variant, rotating to avoid repetition."""
        try:
            prompt = self._fallback_variations[self._fallback_idx % len(self._fallback_variations)]
            self._fallback_idx += 1
            return prompt
        except Exception:
            return "I can assist with scheduling meetings, finding employees, or guiding you around."

    def safe_listen_with_backoff(self, max_attempts=2, max_total_time=10):
        """Wrap listen_with_retry with one retry on network errors (e.g., getaddrinfo)."""
        try:
            # Attempt 1: try once; if we capture valid text, stop immediately
            first_input, first_questions = self.voice_agent.listen_with_retry(max_attempts=1, max_total_time=max_total_time)
            if first_input or (first_questions and len(first_questions) > 0):
                return first_input, first_questions
            # Only retry if attempt 1 failed
            time.sleep(0.3)
            return self.voice_agent.listen_with_retry(max_attempts=1, max_total_time=max_total_time)
        except (socket.gaierror, OSError) as e:
            logging.warning(f"STT error: {e}. Retrying once after backoff...")
            time.sleep(1.0)
            try:
                # Final retry: single attempt
                return self.voice_agent.listen_with_retry(max_attempts=1, max_total_time=max_total_time)
            except Exception as e2:
                logging.error(f"STT failed after retry: {e2}")
                self.avatar_agent.show_speaking()
                self.say("I'm having trouble hearing you clearly right now. Could you try again in a moment?")
                self.avatar_agent.show_idle()
                return ("", None)
        except Exception as e:
            # Any unexpected error -> graceful message
            logging.error(f"STT unexpected error: {e}")
            self.avatar_agent.show_speaking()
            self.say("I'm having trouble hearing you clearly right now. Could you try again in a moment?")
            self.avatar_agent.show_idle()
            return ("", None)

    def safe_listen_until_complete(self, max_total_time=15):
        """Wrap listen_until_complete with one retry on network errors."""
        try:
            return self.voice_agent.listen_until_complete(max_total_time=max_total_time)
        except (socket.gaierror, OSError) as e:
            logging.warning(f"STT (until_complete) error: {e}. Retrying once after backoff...")
            time.sleep(1.0)
            try:
                return self.voice_agent.listen_until_complete(max_total_time=max_total_time)
            except Exception as e2:
                logging.error(f"STT (until_complete) failed after retry: {e2}")
                self.avatar_agent.show_speaking()
                self.say("I'm having trouble hearing you clearly right now. Could you try again in a moment?")
                self.avatar_agent.show_idle()
                return ""
        except Exception as e:
            logging.error(f"STT (until_complete) unexpected error: {e}")
            self.avatar_agent.show_speaking()
            self.say("I'm having trouble hearing you clearly right now. Could you try again in a moment?")
            self.avatar_agent.show_idle()
            return ""

    def parse_time_robust(self, text_time):
        """Parse time string robustly using utils first, then dateparser if available."""
        try:
            from utils import parse_time_string
            t = parse_time_string(text_time)
            if t:
                # Validate hour range implicitly handled by parser; still ensure attribute exists
                return t
        except Exception:
            pass
        # Fallback to dateparser if installed
        try:
            import dateparser
            dt = dateparser.parse(text_time)
            if dt:
                return dt.time()
        except Exception:
            pass
        return None

    def parse_date_robust(self, text_date):
        """Parse date string robustly using utils first, then dateparser if available."""
        try:
            from utils import parse_date_string
            d = parse_date_string(text_date)
            if d:
                return d
        except Exception:
            pass
        try:
            import dateparser
            dt = dateparser.parse(text_date)
            if dt:
                return dt.date()
        except Exception:
            pass
        return None
        
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
            
            # If awaiting a follow-up (e.g., time confirmation), handle that first
            if self.dialog_context.get('pending_action') == 'waiting_for_time':
                # Prompt once to choose time if we don't have input yet
                if not self.dialog_context.get('waiting_prompted'):
                    self.avatar_agent.show_speaking()
                    self.say("Please tell me a time that works for you from the available options.")
                    self.avatar_agent.show_idle()
                    self.dialog_context['waiting_prompted'] = True
            
            # Get user input
            if pending_input:
                user_input = pending_input
                pending_input = None
                logging.info(f"📝 Processing pending input: {user_input}")
            else:
                # Listen for user input with better patience using retry method
                self.avatar_agent.show_listening()
                user_input, questions = self.safe_listen_with_backoff(max_attempts=2, max_total_time=10)
                self.avatar_agent.show_idle()
                
                # Log what we received
                logging.info(f"📝 Received input: '{user_input}', questions: {questions}")

            # N-times self-identification shortcut (run BEFORE any other handling)
            if user_input and not is_employee:
                ul = user_input.lower()
                try:
                    if (("work" in ul and "here" in ul) or
                        re.search(r"\bi\s*(am|’m|'m)\s*(already\s+)?(an?\s+)?(employee|staff)\b", ul) or
                        re.search(r"\bi\s*(am|’m|'m)\s*(already\s+)?(working\s+here|work\s+here)\b", ul) or
                        "i already work here" in ul or
                        "i am already working" in ul or
                        "i am already an employee" in ul):
                        resp, _handled = self.handle_employee_self_identification()
                        if resp == "RECOGNITION_SUCCESS":
                            user_name = self.current_user
                            is_employee = True
                        # Either way, handled this turn
                        continue
                except Exception as e:
                    logging.warning(f"Self-identification shortcut failed: {e}")

            # Identity mismatch triggers immediate re-recognition (works even if is_employee)
            if user_input:
                ul = user_input.lower()
                mismatch_patterns = [
                    r"\bi'?m\s+not\s+" + re.escape(str(user_name).lower()) + r"\b" if user_name else None,
                    r"\bi\s+am\s+not\s+" + re.escape(str(user_name).lower()) + r"\b" if user_name else None,
                    r"you\s+(recognized|recognised)\s+me\s+wrong",
                    r"that's\s+not\s+me",
                    r"that is\s+not\s+me",
                    r"you\s+mis(recognized|identified)\s+me",
                    r"wrong\s+person",
                ]
                try:
                    if any(p and re.search(p, ul) for p in mismatch_patterns):
                        self.avatar_agent.show_speaking()
                        self.say("Thanks for clarifying. Let me recheck your identity.")
                        self.avatar_agent.show_idle()
                        resp, _handled = self.handle_employee_self_identification()
                        if resp == "RECOGNITION_SUCCESS":
                            user_name = self.current_user
                            is_employee = True
                        continue
                except Exception:
                    pass

            # Check for polite responses that should end the conversation gracefully
            if user_input:
                user_lower = user_input.lower().strip()
                farewell_phrases = [
                    "thank", "thank you", "thanks", "thankyou", "thank you very much", "thanks a lot",
                    "bye", "goodbye", "see you", "that's all", "that’s all",
                    "i'm done", "i am done", "no thanks", "no thank you"
                ]
                if any(f in user_lower for f in farewell_phrases):
                    # Tailor response based on gratitude vs. goodbye
                    is_thanks = any(t in user_lower for t in ["thank", "thank you", "thanks", "thankyou"]) 
                    farewell_response = "You're welcome! Have a great day." if is_thanks else "Goodbye! Have a great day."
                    self.avatar_agent.show_speaking()
                    self.say(farewell_response)
                    self.avatar_agent.show_idle()
                    break

            # If we have parsed questions, handle them first (even if raw user_input is empty)
            logging.info(f"🔍 Debug: questions={questions}, len={len(questions) if questions else 0}")
            if questions and len(questions) >= 1:
                # Special handling: if we are waiting for a time selection, try to parse a time from questions
                if self.dialog_context.get('pending_action') == 'waiting_for_time':
                    scheduled = False
                    for question in questions:
                        sel_time = self.parse_time_robust(question)
                        if sel_time:
                            who = self.dialog_context.get('person')
                            sel_date = self.dialog_context.get('date')
                            success, result_message = self.calendar_agent.schedule_appointment(
                                user_name, who, sel_date, sel_time
                            )
                            # Clear context regardless to avoid repeated prompts
                            self.dialog_context.clear()
                            if success:
                                time_str = sel_time.strftime("%I:%M %p")
                                try:
                                    is_today = hasattr(sel_date, 'strftime') and (sel_date == datetime.now().date())
                                except Exception:
                                    is_today = False
                                date_str = "today" if is_today else (sel_date.strftime("%B %d, %Y") if hasattr(sel_date, 'strftime') else str(sel_date))
                                self.avatar_agent.show_speaking()
                                if date_str == "today":
                                    self.say(f"Your appointment with {who} at {time_str} today is confirmed.")
                                else:
                                    self.say(f"Your appointment with {who} at {time_str} on {date_str} is confirmed.")
                                self.avatar_agent.show_idle()
                            else:
                                self.avatar_agent.show_speaking()
                                self.say(result_message or "That slot is not available. Please choose another time.")
                                self.avatar_agent.show_idle()
                            scheduled = True
                            break
                    if scheduled:
                        continue
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

            # Handle dialog continuation: awaiting time selection for appointment
            if self.dialog_context.get('pending_action') == 'waiting_for_time' and user_input:
                try:
                    sel_time = self.parse_time_robust(user_input)
                    if sel_time:
                        who = self.dialog_context.get('person')
                        sel_date = self.dialog_context.get('date')
                        success, result_message = self.calendar_agent.schedule_appointment(
                            user_name, who, sel_date, sel_time
                        )
                        # Clear context
                        self.dialog_context.clear()
                        if success:
                            time_str = sel_time.strftime("%I:%M %p")
                            # Use 'today' wording when applicable
                            try:
                                is_today = hasattr(sel_date, 'strftime') and (sel_date == datetime.now().date())
                            except Exception:
                                is_today = False
                            date_str = "today" if is_today else (sel_date.strftime("%B %d, %Y") if hasattr(sel_date, 'strftime') else str(sel_date))
                            self.avatar_agent.show_speaking()
                            if date_str == "today":
                                self.say(f"Your appointment with {who} at {time_str} today is confirmed.")
                            else:
                                self.say(f"Your appointment with {who} at {time_str} on {date_str} is confirmed.")
                            self.avatar_agent.show_idle()
                            continue
                        else:
                            self.avatar_agent.show_speaking()
                            self.say(result_message or "That slot is not available. Please choose another time.")
                            self.avatar_agent.show_idle()
                            continue
                except Exception:
                    pass

            # Only retry listening if attempt 1 failed to capture anything
            if not user_input and not (questions and len(questions) >= 1):
                logging.info("Attempt 1 produced no input; prompting and retrying once")
                self.avatar_agent.show_speaking()
                self.voice_agent.speak(f"I didn't catch that clearly. {self.get_rotating_help_prompt()}")
                time.sleep(0.5)
                self.avatar_agent.show_listening()
                retry_input, retry_questions = self.safe_listen_with_backoff(max_attempts=2, max_total_time=8)
                self.avatar_agent.show_idle()
                if retry_questions and len(retry_questions) >= 1:
                    questions = retry_questions
                    # Let the questions processing block handle it on next loop iteration
                    continue
                elif retry_input:
                    user_input = retry_input
                else:
                    # Still nothing; continue loop to listen again naturally
                    continue

            # Single question - process normally
            response, is_handled = self.process_query(user_input, user_name, is_employee)
            
            # Check for special re-recognition response
            if response == "RECOGNITION_SUCCESS":
                # User was successfully re-recognized as employee
                # Update the conversation context
                user_name = self.current_user  # This should now be the recognized employee name
                is_employee = True
                logging.info(f"🔄 User type changed: {user_name} is now recognized as employee")
                continue  # Continue with the updated user context
            
            if response:
                self.avatar_agent.show_speaking()
                self.voice_agent.speak(response)
                self.avatar_agent.show_idle()
                time.sleep(0.5)
                
                # Don't ask follow-up if we're waiting for appointment time
                is_waiting_for_time = (
                    hasattr(self, 'dialog_context') and 
                    self.dialog_context.get('pending_action') == 'waiting_for_time'
                )
                
                # Only ask follow-up if not waiting for time and not asking for time input
                if not is_waiting_for_time and not (
                    "What time would you like to meet" in response or
                    "whom would you like to meet" in response or
                    "Please ask where a department is" in response
                ):
                    # Do not force follow-up here to avoid repetition; rely on user
                    pass
                    
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

    def handle_employee_re_recognition(self):
        """Handle re-recognition when unknown user claims to be an employee"""
        logging.info("🔍 Unknown user claims to be an employee - triggering re-recognition")
        self.avatar_agent.show_speaking()
        self.say("Sorry about that. I may have misrecognized you. Let me try again.")
        self.avatar_agent.show_idle()
        
        # Trigger re-recognition
        try:
            self.avatar_agent.show_processing()
            name, confidence = self.face_agent.recognize_facye_from_camera()
            self.avatar_agent.show_idle()
            
            if name != "Unknown":
                # Successfully recognized as employee
                logging.info(f"✅ Re-recognition successful: {name} (confidence: {confidence})")
                
                # Update current user
                self.current_user = name
                
                self.avatar_agent.show_speaking()
                self.say(f"Welcome {name}. How can I help you today?")
                self.avatar_agent.show_idle()
                
                # Log attendance for the newly recognized employee
                try:
                    self.attendance_agent.log_arrival(name)
                except Exception as e:
                    logging.warning(f"Attendance log failed for {name}: {e}")
                
                # Return special response to indicate user type change
                return ("RECOGNITION_SUCCESS", True)
            else:
                # Still couldn't recognize
                logging.info("❌ Re-recognition failed - still unknown")
                self.avatar_agent.show_speaking()
                self.say("Your face seems unclear. Please move closer or adjust your position, and look at the camera.")
                self.avatar_agent.show_idle()
                return ("", True)
                
        except Exception as e:
            logging.error(f"Error during re-recognition: {e}")
            self.avatar_agent.show_speaking()
            self.voice_agent.speak("I encountered an error during re-recognition. Please try again or ask our receptionist for assistance.")
            self.avatar_agent.show_idle()
            return ("", True)

    def handle_employee_self_identification(self):
        """Detect employee-claim phrases, retry recognition with limits, and fall back to name/ID."""
        logging.info("🪪 Handling employee self-identification flow")
        max_retries = 2  # 2 rounds of recognition retries
        attempts_per_round = 15

        self.avatar_agent.show_speaking()
        self.say("Sorry about that. Let me try to recognize you again.")
        self.avatar_agent.show_idle()

        for retry_round in range(max_retries):
            try:
                self.avatar_agent.show_processing()
                # Allow passing attempt limit to the recognizer if supported
                try:
                    name, confidence = self.face_agent.recognize_facye_from_camera(max_attempts=attempts_per_round)
                except TypeError:
                    # Fallback if method does not accept keyword args
                    name, confidence = self.face_agent.recognize_facye_from_camera()
                self.avatar_agent.show_idle()

                if name != "Unknown":
                    logging.info(f"✅ Re-recognition success on round {retry_round+1}: {name} ({confidence})")
                    self.current_user = name
                    # Greet and log attendance
                    self.avatar_agent.show_speaking()
                    self.say(f"Welcome back, {name}. How can I help you today?")
                    self.avatar_agent.show_idle()
                    try:
                        self.attendance_agent.log_arrival(name)
                    except Exception as e:
                        logging.warning(f"Attendance log failed for {name}: {e}")
                    return ("RECOGNITION_SUCCESS", True)

                logging.info(f"❌ Re-recognition round {retry_round+1} failed")
                if retry_round < max_retries - 1:
                    # Encourage and try again
                    self.avatar_agent.show_speaking()
                    self.say("Please face the camera with good lighting. I will try once more.")
                    self.avatar_agent.show_idle()
            except Exception as e:
                logging.error(f"Error during self-identification re-recognition: {e}")
                # Break to fallback
                break

        # Fallback after retries exhausted
        self.avatar_agent.show_speaking()
        self.say("I couldn't recognize you. Could you please tell me your name or employee ID so I can assist you?")
        self.avatar_agent.show_idle()

        # Listen once for name/ID and save to context
        self.avatar_agent.show_listening()
        provided, _ = self.safe_listen_with_backoff(max_attempts=2, max_total_time=8)
        self.avatar_agent.show_idle()

        if provided:
            # Very light extraction: prefer an ID-like token, else take phrase as name
            extracted_id = None
            extracted_name = None
            try:
                import re
                m = re.search(r"\b([A-Z]{2,}\d{2,}|\d{5,})\b", provided)
                if m:
                    extracted_id = m.group(1)
                else:
                    extracted_name = provided.strip()
            except Exception:
                extracted_name = provided.strip()

            # Save in conversation context
            if extracted_name:
                self.current_user = extracted_name
                logging.info(f"📝 Saved self-reported name: {extracted_name}")
            if extracted_id:
                setattr(self, "current_user_id", extracted_id)
                logging.info(f"📝 Saved self-reported employee ID: {extracted_id}")

            self.avatar_agent.show_speaking()
            self.say("Thank you. How can I help you today?")
            self.avatar_agent.show_idle()
            return ("", True)

        # No input provided; keep it graceful
        self.avatar_agent.show_speaking()
        self.say("No problem. Whenever you're ready, tell me your name or employee ID, and I'll help you.")
        self.avatar_agent.show_idle()
        return ("", True)

    def handle_appointment_scheduling(self, user_input, user_name):
        """Handle appointment scheduling requests"""
        from utils import extract_appointment_details
        
        logging.info(f"🎯 Starting appointment scheduling for: {user_input}")
        
        # Extract appointment details from user input
        details = extract_appointment_details(user_input)
        logging.info(f"📋 Extracted details: {details}")
        
        if not details["person_name"]:
            return "I'm sorry, I didn't catch the name of the person you want to schedule with. Could you please repeat the name?"
        
        if not details["time"]:
            return "I need to know what time you'd like to schedule. Could you please specify a time?"
        
        if not details["date"]:
            return "I need to know what date you'd like to schedule. Could you please specify a date?"
        
        # Check if the employee exists
        employee = self.directory_agent.search_employee(details["person_name"])
        if not employee:
            return f"Sorry, I couldn't find anyone named {details['person_name']} in our employee directory."
        
        # Parse time and date
        appointment_time = self.parse_time_robust(details["time"])
        appointment_date = self.parse_date_robust(details["date"])
        
        if not appointment_time:
            return f"I couldn't understand the time '{details['time']}'. Please specify a time like '3:00 PM' or '2:30 AM'."
        
        if not appointment_date:
            return f"I couldn't understand the date '{details['date']}'. Please specify a date like 'today', 'tomorrow', or 'next Monday'."
        
        # Check availability
        logging.info(f"🔍 Checking availability for {details['person_name']} on {appointment_date} at {appointment_time}")
        is_available, message = self.calendar_agent.check_availability(
            details["person_name"], 
            appointment_date, 
            appointment_time
        )
        logging.info(f"📊 Availability result: {is_available} - {message}")
        
        if is_available:
            # Schedule the appointment
            success, result_message = self.calendar_agent.schedule_appointment(
                user_name,
                details["person_name"],
                appointment_date,
                appointment_time
            )
            
            if success:
                # Format the response
                time_str = appointment_time.strftime("%I:%M %p")
                try:
                    is_today = appointment_date == datetime.now().date()
                except Exception:
                    is_today = False
                date_str = "today" if is_today else appointment_date.strftime("%B %d, %Y")
                response = (
                    f"Your appointment with {details['person_name']} at {time_str} {date_str if date_str=='today' else f'on {date_str}'} is confirmed."
                )
                
                # Send SMS notification to the employee
                mobile = self.get_mobile_from_employee(employee)
                if mobile:
                    when_text = ("today at " + time_str) if date_str == "today" else (f"on {date_str} at {time_str}")
                    sms_message = f"New appointment scheduled: {user_name} wants to meet you {when_text}."
                    send_sms(mobile, sms_message)
                
                return response
            else:
                return f"Sorry, there was an error scheduling the appointment: {result_message}"
        else:
            # Get available slots for alternative times
            available_slots = self.calendar_agent.get_available_slots(
                details["person_name"], 
                appointment_date
            )
            
            if available_slots:
                # Save dialog context to await a chosen time
                try:
                    self.dialog_context = {
                        'pending_action': 'waiting_for_time',
                        'person': details['person_name'],
                        'date': appointment_date,
                        'slots': available_slots,
                    }
                except Exception:
                    pass
                # Suggest alternative times
                slots_text = ", ".join(available_slots[:5])  # Show first 5 slots
                if len(available_slots) > 5:
                    slots_text += f", and {len(available_slots) - 5} more slots"
                
                return f"{details['person_name']} is not available at {details['time']} on {details['date']}. Available times include: {slots_text}. Would you like to try another time?"
            else:
                return f"{details['person_name']} is not available at {details['time']} on {details['date']}. They have no available slots on that date. Would you like to try another date?"

    def process_query(self, user_input, user_name, is_employee):
        """Process user query through appropriate agents"""
        sensitive_keywords = ["email", "mobile", "phone", "salary", "join", "joining date", "position"]
        user_lower = user_input.lower()

        # Employee self-identification – handle FIRST for unknown users
        if not is_employee:
            try:
                if (
                    re.search(r"\bi\s*(am|’m|'m)\s*(already\s+)?(an?\s+)?(employee|staff)\b", user_lower)
                    or re.search(r"\bi\s*(am|’m|'m)\s*(already\s+)?(working\s+here|work\s+here)\b", user_lower)
                    or "i already work here" in user_lower
                    or "i am already working" in user_lower
                    or "i am already an employee" in user_lower
                ):
                        return self.handle_employee_self_identification()
            except Exception:
                logging.info("Re-recognition not works")
                pass

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

        # Identity queries: "what is my name" / "who am I"
        if re.search(r"\b(what\s+is\s+my\s+name|who\s+am\s+i)\b", user_lower):
            # Prefer DB for role/department
            role_text = None
            try:
                emp = self.directory_agent.search_employee(user_name)
                if emp:
                    data = self.row_to_dict(emp)
                    role_text = data.get('role') or data.get('position') or data.get('department')
            except Exception:
                pass
            if role_text:
                return (f"You are {user_name}. You are working as {role_text}.", False)
            return (f"You are {user_name}.", False)

        # Identity queries: "who is {name}"
        who_is_match = re.search(r"\bwho\s+is\s+([a-zA-Z][a-zA-Z ]{1,50})\b", user_lower)
        if who_is_match:
            target_name = who_is_match.group(1).strip().title()
            # 1) Check employees table
            emp = self.directory_agent.search_employee(target_name)
            if emp:
                data = self.row_to_dict(emp)
                role_text = data.get('role') or data.get('position') or data.get('department')
                if role_text:
                    return (f"{target_name} is {role_text}.", False)
                return (f"{target_name} is an employee.", False)
            # 2) Infer visitors from appointments as organizer/participant not in employees
            try:
                # If they appear in appointments as organizer or participant but not in employees, consider visitor
                as_org, as_part = self.calendar_agent.fetch_today_appointments_for_user(target_name)
                if as_org or as_part:
                    return (f"{target_name} is a visitor.", False)
            except Exception:
                pass
            return (f"I don't see anyone named {target_name} in our records.", False)

        # Note: General knowledge handling moved below after domain intents to avoid false positives

        # Cancel appointment intent
        cancel_phrases = ["cancel my appointment", "delete my appointment", "cancel appointment", "cancel meeting"]
        if any(p in user_lower for p in cancel_phrases):
            from datetime import datetime
            today = datetime.now().date()
            # naive parse time from text (fallback)
            chosen_time = None
            try:
                from utils import parse_time_string
                m = re.search(r"(\d{1,2}(:\d{2})?\s*(am|pm))", user_lower)
                if m:
                    chosen_time = parse_time_string(m.group(0))
            except Exception:
                pass
            count, msg = self.calendar_agent.cancel_appointment(user_name, date=today, time=chosen_time)
            return ("Cancelled." if count else msg, False)

        # My appointments today intent
        if re.search(r"\b(my|any) appointments? today\b", user_lower):
            as_org, as_part = self.calendar_agent.fetch_today_appointments_for_user(user_name)
            if not as_org and not as_part:
                return ("You don't have any appointments today.", False)
            parts = []
            if as_org:
                parts.append("as organizer: " + ", ".join([f"{t} with {n}" for t, n in as_org]))
            if as_part:
                parts.append("with you: " + ", ".join([f"{t} with {n}" for t, n in as_part]))
            return ("Your appointments today — " + "; ".join(parts) + ".", False)

        # Notify employee intent
        notify_match = re.search(r"notify\s+([a-zA-Z ]+)\s+that\s+i'?m\s+here", user_lower)
        if notify_match:
            target = notify_match.group(1).strip().title()
            employee = self.directory_agent.search_employee(target)
            if employee:
                mobile = self.get_mobile_from_employee(employee)
                if mobile:
                    send_sms(mobile, f"Reception: {user_name} is here to see you.")
                    return (f"I have notified {target}.", False)
                return (f"I found {target} but could not notify them.", False)
            return (f"I couldn't find {target} in our directory.", False)
        
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
                follow_up = self.safe_listen_until_complete(max_total_time=15)
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
                return (self.get_rotating_help_prompt(), False)
            # Allow very limited name verification only if phrased explicitly
            name = self.extract_name_from_request(user_input)
            if name and any(phrase in user_lower for phrase in ["does", "do", "work here", "is here", "present", "in this company", "employee"]):
                employee = self.directory_agent.search_employee(name)
                if employee:
                    return (f"Yes, {name} works here.", False)
                else:
                    return (f"Sorry, I couldn't find anyone named {name} in our employee directory.", False)
            # Fallback restriction for visitors
            return (self.get_rotating_help_prompt(), False)
        # Normal logic for employees
        # Check for greetings first
        if any(greeting in user_input.lower() for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "how are you"]):
            # Show happy state for greetings
            self.avatar_agent.show_happy()
            return (self.chat_agent.process_greeting(user_input), False)
        
        # Check for appointment-related queries FIRST (before general knowledge)
        if any(word in user_input.lower() for word in ["appointment", "meeting", "schedule"]):
            logging.info(f"🔍 Detected appointment-related query: {user_input}")
            # Check if this is a scheduling request (has time and date)
            from utils import extract_appointment_details
            details = extract_appointment_details(user_input)
            logging.info(f"📅 Extracted appointment details: {details}")
            
            if details["time"] and details["date"] and details["person_name"]:
                # This is a scheduling request - handle it
                logging.info(f"✅ Processing appointment scheduling request: {details}")
                self.avatar_agent.show_processing()
                response = self.handle_appointment_scheduling(user_input, user_name)
                return (response, False)
            else:
                # This is a general appointment query - check existing appointments
                logging.info(f"ℹ️ General appointment query - checking existing appointments")
                self.avatar_agent.show_processing()
                response = self.calendar_agent.check_appointment(user_name)
                return (response, False)
        # Check for meeting/visit requests (before general knowledge)
        if any(word in user_lower for word in ["meet", "see", "visit", "talk to", "speak to", "looking for", "find", "call"]):
            # Check if this might be a scheduling request
            from utils import extract_appointment_details
            details = extract_appointment_details(user_input)
            
            if details["person_name"] and (details["time"] or details["date"]):
                # This looks like a scheduling request - handle it
                logging.info(f"Processing meeting request as scheduling: {details}")
                self.avatar_agent.show_processing()
                response = self.handle_appointment_scheduling(user_input, user_name)
                return (response, False)
            else:
                # This is a general meeting request - handle normally
                self.handle_meeting_request(user_input)
                return ("", True)
        
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

        # Check if unknown user claims to be an employee - trigger re-recognition
        employee_claim_keywords = [
            "i work here", "i am an employee", "i'm an employee", "i work at this company", 
            "i'm a staff member", "i work for this company", "i'm staff", "i work here", 
            "i'm an employee here", "i work for you", "i'm part of the staff", "i'm a team member",
            "you didn't recognize me", "you should know me", "i work in this office"
        ]
        if not is_employee and any(phrase in user_lower for phrase in employee_claim_keywords):
            return self.handle_employee_self_identification()

        # General knowledge (employees only) - placed at the end to avoid overshadowing domain intents
        if is_employee and any(keyword in user_lower for keyword in general_question_keywords):
            logging.info("Processing General Knowledge Question (employee)")
            self.avatar_agent.show_thinking()
            response = self.chat_agent.process_general_query(user_input)
            return (response, False)
        else:
            return ("I'm here to help you with directions, appointments, and connecting you with employees. How can I assist you today?", False)
        
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
