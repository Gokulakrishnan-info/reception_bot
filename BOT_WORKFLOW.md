# AI Reception Bot - Complete Workflow

## Overview
The AI Reception Bot is a modular system that handles face recognition, voice interaction, employee queries, and general knowledge questions. It operates as a professional receptionist with different access levels for employees vs. visitors.

## System Architecture

### Core Agents
1. **WakeWordAgent** - Detects wake word ("Hey Jarvis")
2. **FaceRecognitionAgent** - Recognizes employees vs. visitors
3. **ChatAgent** - Handles AI conversations and employee queries
4. **VoiceAgent** - Manages speech recognition and text-to-speech
5. **AvatarAgent** - Provides visual feedback (PyQt6/Tkinter)
6. **DirectoryAgent** - Employee database lookups
7. **AttendanceAgent** - Tracks employee presence
8. **CalendarAgent** - Handles appointments (placeholder)
9. **SMS Agent** - Sends notifications via Twilio

## Complete Workflow

### 1. Initialization Phase
```
Bot Startup
├── Initialize all agents
├── Load face recognition database
├── Setup PyQt6 avatar window
├── Initialize voice recognition
└── Start listening for wake word
```

### 2. Wake Word Detection
```
User says "Hey Jarvis"
├── WakeWordAgent detects wake word
├── Activates camera for face recognition
└── Proceeds to user identification
```

### 3. User Identification
```
Face Recognition Process
├── Capture image from camera
├── Extract face embeddings
├── Compare with known employees
├── Determine: Employee or Visitor
└── Set access level accordingly
```

### 4. Greeting & Access Level Setup
```
Employee (Recognized Face):
├── Log attendance automatically
├── Greet: "Hi [Name], [Time Greeting]! How can I help you today?"
└── Grant full access to employee queries

Visitor (Unknown Face):
├── Greet: "Hello! Welcome. May I know your name, or how can I assist you today?"
└── Grant limited access (general questions + meeting requests)
```

### 5. Query Processing Workflow

#### 5.1 General Knowledge Questions (ALL USERS)
```
Keywords: "who is", "what is", "president", "capital", "weather", etc.
├── Show thinking avatar state
├── Process via ChatAgent.process_general_query()
├── Get response from AWS Bedrock AI
└── Speak response with speaking avatar state
```

#### 5.2 Employee-Specific Queries (EMPLOYEES ONLY)
```
Keywords: "email", "salary", "department", "details", etc.
├── Show processing avatar state
├── Check access control (current_user must be set)
├── Process via ChatAgent.process_employee_query()
├── Return JSON format response
└── Speak response with speaking avatar state
```

#### 5.3 Department Location Queries (ALL USERS)
```
Keywords: "where is HR", "IT department location", etc.
├── Detect department query pattern
├── Extract department name
├── Send SMS notification to Alex (office boy)
├── Response: "Please wait here, Alex will come and assist you. I have notified him."
└── Speak response with speaking avatar state
```

#### 5.4 Meeting/Visit Requests (ALL USERS)
```
Keywords: "meet", "see", "visit", "talk to", etc.
├── Extract employee name from request
├── Search employee in database
├── If found:
│   ├── Send SMS notification to employee
│   ├── Response: "I've notified [Name]. Please wait in the reception."
│   └── Speak response
└── If not found:
    ├── Response: "Sorry, I couldn't find anyone named [Name] in our employee directory."
    └── Speak response
```

#### 5.5 Employee Name Verification (VISITORS ONLY)
```
Keywords: Employee name only (without sensitive details)
├── Search employee in database
├── If found: "Yes, [Name] works here."
└── If not found: "Sorry, I couldn't find anyone named [Name] in our employee directory."
```

#### 5.6 Sensitive Information Requests (VISITORS BLOCKED)
```
Keywords: "email", "mobile", "phone", "salary", etc.
├── Block access to sensitive information
├── Offer to notify the employee instead
├── Listen for yes/no response
├── If yes: Send SMS notification
└── If no: "Okay. If you need anything else, let me know."
```

#### 5.7 Attendance Queries (EMPLOYEES ONLY)
```
Keywords: "present", "attendance", "who is here", etc.
├── Check attendance database
├── If specific employee: "Yes, [Name] is present today. They arrived at [Time]."
├── If general query: List all present employees with arrival times
└── Speak response
```

#### 5.8 Greetings (ALL USERS)
```
Keywords: "hello", "hi", "good morning", etc.
├── Show happy avatar state
├── Process via ChatAgent.process_greeting()
├── Return time-appropriate greeting
└── Speak response
```

#### 5.9 Facility Queries (ALL USERS)
```
Keywords: "restroom", "washroom", "toilet"
├── Quick response: "The restroom is near the lift, just to your right."
└── Speak response
```

#### 5.10 Appointment Queries (EMPLOYEES ONLY)
```
Keywords: "appointment", "meeting", "schedule"
├── Show processing avatar state
├── Check calendar (placeholder functionality)
├── Return appointment information
└── Speak response
```

### 6. Conversation Flow Management

#### 6.1 Multiple Questions Detection
```
If multiple questions detected:
├── Announce: "I heard you ask several questions. Let me address them one by one."
├── Process each question separately
├── Number responses: "Now for your [ordinal] question:"
└── Continue conversation naturally
```

#### 6.2 Natural Conversation Continuation
```
After each response:
├── Return to idle avatar state
├── Wait for next question
├── No repetitive "Do you have any other questions?"
└── Maintain professional receptionist behavior
```

### 7. Avatar State Management

#### 7.1 State Transitions
```
Idle → Listening → Processing/Thinking → Speaking → Idle
├── Idle: Default robot state
├── Listening: Robot with listening indicators
├── Processing: 3D gears animation
├── Thinking: 3D thought bubbles
├── Speaking: Animated mouth movement
└── Happy: For greetings
```

### 8. Error Handling & Fallbacks

#### 8.1 Voice Recognition Failures
```
If no input detected:
├── "I didn't catch that. Could you please repeat?"
├── Listen again with longer timeout
├── If still no input: "I'm having trouble hearing you. Please try again later."
└── Return to idle state
```

#### 8.2 Database Failures
```
If MySQL fails:
├── Log warning
├── Fallback to CSV file
├── Continue with limited functionality
└── Log error for debugging
```

#### 8.3 SMS Failures
```
If Twilio SMS fails:
├── Log warning
├── Inform user: "I tried to notify [Name], but there was an issue with the SMS."
├── Continue with other functionality
└── Don't block conversation flow
```

### 9. Exit Conditions

#### 9.1 User Exit Commands
```
Keywords: "bye", "goodbye", "see you", "exit", "leave"
├── Response: "Okay, feel free to ask me anytime. Have a great day!"
├── Close avatar window
├── Cleanup camera resources
└── Return to wake word detection
```

#### 9.2 System Shutdown
```
If shutdown requested:
├── Stop all agents gracefully
├── Close PyQt6 window
├── Release camera resources
└── Exit cleanly
```

## Access Control Matrix

| Query Type | Employee | Visitor | Response Format |
|------------|----------|---------|-----------------|
| General Knowledge | ✅ | ✅ | Natural language |
| Employee Details | ✅ | ❌ | JSON format |
| Department Location | ✅ | ✅ | Natural language |
| Meeting Requests | ✅ | ✅ | Natural language |
| Employee Name Check | ✅ | ✅ | Simple yes/no |
| Attendance | ✅ | ❌ | Natural language |
| Greetings | ✅ | ✅ | Natural language |
| Facilities | ✅ | ✅ | Natural language |
| Appointments | ✅ | ❌ | Natural language |

## Data Flow

```
User Input → Voice Recognition → Query Classification → Agent Processing → Response Generation → Text-to-Speech → Avatar Animation
```

## Security Features

1. **Face-based Access Control**: Only recognized employees get full access
2. **Sensitive Data Protection**: Visitors cannot access employee details
3. **Audit Trail**: All interactions are logged
4. **Graceful Degradation**: System continues working even if some components fail

## Integration Points

1. **AWS Bedrock**: AI conversation processing
2. **MySQL Database**: Employee information storage
3. **Twilio SMS**: Notification system
4. **Excel Files**: Attendance tracking
5. **PyQt6**: Visual avatar interface
6. **OpenCV**: Face recognition
7. **SpeechRecognition**: Voice input processing

This workflow ensures the bot operates as a professional, secure, and helpful receptionist while maintaining appropriate access controls and providing a smooth user experience.
