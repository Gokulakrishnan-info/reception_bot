# AI Reception Bot - Visual Flowchart

## Main Bot Flow

```
┌─────────────────┐
│   BOT STARTUP   │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  WAKE WORD      │
│  DETECTION      │ ◄── "Hey Jarvis"
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  FACE           │
│  RECOGNITION    │ ◄── Camera Activation
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  USER TYPE      │
│  DETERMINATION  │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│EMPLOYEE │ │VISITOR  │
│(Known)  │ │(Unknown)│
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│Log      │ │No       │
│Attendance│ │Attendance│
│Log      │ │Log      │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│"Hi      │ │"Hello!  │
│[Name],  │ │Welcome. │
│[Time]!  │ │How can  │
│How can  │ │I assist │
│I help?" │ │you?"    │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌─────────────────┐
│  CONVERSATION   │
│     LOOP        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  LISTEN FOR     │
│  USER INPUT     │ ◄── Voice Recognition
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  QUERY          │
│  CLASSIFICATION │
└─────────┬───────┘
          │
          ▼
```

## Query Processing Flow

```
┌─────────────────┐
│  QUERY          │
│  CLASSIFICATION │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│GENERAL  │ │SPECIFIC │
│KNOWLEDGE│ │QUERIES  │
│QUESTION │ │         │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│Process  │ │Check    │
│via      │ │User     │
│AI       │ │Type     │
│Bedrock  │ │         │
└────┬────┘ └────┬────┘
     │           │
     │     ┌─────┴─────┐
     │     │           │
     │     ▼           ▼
     │ ┌─────────┐ ┌─────────┐
     │ │EMPLOYEE │ │VISITOR  │
     │ │QUERIES  │ │QUERIES  │
     │ └────┬────┘ └────┬────┘
     │      │           │
     │      ▼           ▼
     │ ┌─────────┐ ┌─────────┐
     │ │Full     │ │Limited  │
     │ │Access   │ │Access   │
     │ │         │ │         │
     │ └────┬────┘ └────┬────┘
     │      │           │
     └──────┴─────┬─────┘
                  │
                  ▼
```

## Detailed Query Types

```
┌─────────────────┐
│  QUERY TYPES    │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│GENERAL  │ │EMPLOYEE │
│KNOWLEDGE│ │DETAILS  │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│"Who is  │ │"What is │
│president│ │Gokul's  │
│of India"│ │email?"  │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│AI       │ │JSON     │
│Response │ │Response │
│via      │ │Format   │
│Bedrock  │ │         │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌─────────────────┐
│  DEPARTMENT     │
│  LOCATION       │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│"Where is HR     │
│department?"     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│Send SMS to Alex │
│(Office Boy)     │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│"Please wait,    │
│Alex will assist │
│you. I notified  │
│him."            │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  MEETING        │
│  REQUESTS       │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│"I want to meet  │
│Gokul"           │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│Search Employee  │
│in Database      │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│FOUND    │ │NOT      │
│         │ │FOUND    │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│Send SMS │ │"Sorry,  │
│to       │ │couldn't │
│Employee │ │find     │
│         │ │[Name]"  │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│"I've    │ │End      │
│notified │ │Response │
│[Name].  │ │         │
│Please   │ │         │
│wait."   │ │         │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
```

## Avatar State Management

```
┌─────────────────┐
│  AVATAR STATES  │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│IDLE     │ │LISTENING│
│(Default)│ │(Ears)   │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│THINKING │ │PROCESSING│
│(Bubbles)│ │(Gears)  │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│SPEAKING │ │HAPPY    │
│(Mouth)  │ │(Smile)  │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌─────────────────┐
│  RETURN TO      │
│     IDLE        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  WAIT FOR       │
│  NEXT INPUT     │
└─────────────────┘
```

## Error Handling Flow

```
┌─────────────────┐
│  ERROR          │
│  DETECTION      │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────┐
│VOICE    │ │DATABASE │
│RECOGN.  │ │FAILURE  │
│FAILURE  │ │         │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│"I didn't│ │Fallback │
│catch    │ │to CSV   │
│that.    │ │file     │
│Please   │ │         │
│repeat." │ │         │
└────┬────┘ └────┬────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│Listen   │ │Continue │
│Again    │ │with     │
│         │ │Limited  │
│         │ │Function │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           │
           ▼
┌─────────────────┐
│  SMS FAILURE    │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│"I tried to      │
│notify [Name],   │
│but there was    │
│an issue with    │
│the SMS."        │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  CONTINUE       │
│  CONVERSATION   │
└─────────────────┘
```

## Exit Flow

```
┌─────────────────┐
│  EXIT COMMANDS  │
│"bye", "goodbye" │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│"Okay, feel free │
│to ask me anytime│
│Have a great day!"│
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  CLEANUP        │
│  RESOURCES      │
└─────────┬───────┘
          │
          ▼
┌─────────────────┐
│  RETURN TO      │
│  WAKE WORD      │
│  DETECTION      │
└─────────────────┘
```

## Key Decision Points

1. **User Type**: Employee vs Visitor
2. **Query Type**: General vs Specific
3. **Access Level**: Full vs Limited
4. **Response Format**: Natural vs JSON
5. **Avatar State**: Based on action type
6. **Error Handling**: Graceful degradation

This flowchart shows how the bot intelligently routes different types of queries and maintains appropriate access controls while providing a smooth user experience.
