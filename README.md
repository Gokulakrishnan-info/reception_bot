# Modular AI Reception Bot

This is a modular version of the AI Reception Bot, where the original monolithic `ai_reception_bot.py` file has been separated into logical modules for better maintainability and organization.

## Module Structure

### Core Modules

1. **`config.py`** - Configuration and constants
   - Database settings
   - AWS Bedrock configuration
   - File paths and thresholds
   - Logging setup

2. **`utils.py`** - Utility functions
   - Name extraction from user input
   - Phone number normalization (E.164 format)
   - JSON string extraction
   - Time-based greetings
   - Helper functions

3. **`wake_word_agent.py`** - Wake word detection
   - Listens for "Jarvis" wake word
   - Handles wake word detection with instant camera activation

4. **`face_recognition_agent.py`** - Facial recognition
   - DeepFace integration for face recognition
   - Camera management and face detection
   - Employee identification

5. **`chat_agent.py`** - AI chat functionality
   - AWS Bedrock integration
   - Employee query processing
   - JSON response handling
   - Access control for employee information

6. **`voice_agent.py`** - Voice interface
   - Speech recognition and synthesis
   - Amazon Polly TTS integration
   - Interruption detection
   - Multiple question handling

7. **`avatar_agent.py`** - Visual avatar interface
   - PyQt6-based modern UI (with Tkinter fallback)
   - Animated avatar states (idle, speaking, listening)
   - Real-time visual feedback

8. **`ai_reception_bot.py`** - Main coordination module
   - Orchestrates all agents
   - Main conversation loop
   - Query processing and routing
   - Attendance tracking

9. **`main.py`** - Entry point
   - Application startup
   - AWS credential verification
   - UI initialization

### Supporting Files

- **`twilio_sms.py`** - SMS notification functionality
- **`aws_config.py`** - AWS credentials management

## Usage

### Running the Bot

```bash
cd Modular_AI_Bot
python main.py
```

## Environment Variables (.env)

Create a `.env` file in `Modular_AI_Bot/` (do not commit it) to store secrets:

```
# AWS (optional if using AWS CLI/role)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=us-east-1

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_NAME=Employee
DB_USER=root
DB_PASSWORD=your_password

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
```

The app will automatically load `.env` if `python-dotenv` is installed.

### Individual Module Usage

You can import and use individual modules as needed:

```python
from wake_word_agent import WakeWordAgent
from face_recognition_agent import FaceRecognitionAgent
from chat_agent import ChatAgent

# Initialize specific agents
wake_agent = WakeWordAgent()
face_agent = FaceRecognitionAgent()
chat_agent = ChatAgent()

# Use them independently
if wake_agent.detect_wake_word():
    name, confidence = face_agent.recognize_facye_from_camera()
    response = chat_agent.process_general_query("Hello")
```

## Benefits of Modular Structure

1. **Maintainability** - Each module has a single responsibility
2. **Reusability** - Modules can be used independently
3. **Testing** - Individual modules can be tested in isolation
4. **Debugging** - Easier to locate and fix issues
5. **Extensibility** - New features can be added as separate modules
6. **Code Organization** - Clear separation of concerns

## Dependencies

The modular structure maintains the same dependencies as the original:

- `opencv-python` (cv2)
- `deepface`
- `speech_recognition`
- `boto3`
- `pyaudio`
- `pandas`
- `sqlalchemy`
- `pymysql`
- `PyQt6` (optional, falls back to Tkinter)
- `twilio`

## Configuration

All configuration is centralized in `config.py`. Key settings include:

- Database connection strings
- AWS region and model IDs
- File paths for face database and attendance tracking
- Similarity thresholds for face recognition
- Wake word configuration

## Migration from Original

The modular version maintains full compatibility with the original functionality while providing better code organization. All features work exactly the same:

- Wake word detection ("Jarvis")
- Facial recognition with DeepFace
- AWS Bedrock-powered conversations
- Employee directory lookup
- SMS notifications via Twilio
- Attendance tracking
- Voice interface with Amazon Polly
- Visual avatar interface

## Development

To add new features:

1. Create a new module for the feature
2. Import it in `ai_reception_bot.py`
3. Initialize it in the `__init__` method
4. Integrate it into the conversation flow

This modular approach makes the codebase much more maintainable and easier to extend with new capabilities.
