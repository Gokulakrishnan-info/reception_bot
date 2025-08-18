#!/usr/bin/env python3
"""
Wake Word Agent Module
Handles wake word detection functionality
"""

import speech_recognition as sr
import logging
from config import WAKE_WORD

class WakeWordAgent:
    """Agent 1: Wake Word Detection with Instant Camera Activation"""
    
    def __init__(self, wake_word=WAKE_WORD):
        self.wake_word = wake_word.lower()
        self.recognizer = sr.Recognizer()
        
    def detect_wake_word(self):
        """Listen for wake word and return True if detected"""
        with sr.Microphone() as source:
            logging.info(f"Waiting for wake word: '{self.wake_word}'")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while True:
                try:
                    logging.info("Listerning........")
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                    try:
                        text = self.recognizer.recognize_google(audio).lower().strip()
                        logging.info(f" Heard: {text}")
                        # Wake if the core name appears anywhere, allow slight variations like 'jarvi'
                        tokens = text.replace(".", " ").replace(",", " ").split()
                        if (
                            self.wake_word in text
                            or any(tok.startswith("jarvi") for tok in tokens)
                        ):
                            logging.info(" Wake word detected!")
                            return True
                    except sr.UnknownValueError:
                        pass
                except sr.WaitTimeoutError:
                    pass
                except KeyboardInterrupt:
                    logging.info(" Goodbye!")
                    return False
    
    def detect_wake_word_with_instant_camera(self, face_agent):
        """Listen for wake word and start camera immediately when detected"""
        with sr.Microphone() as source:
            logging.info(f"Waiting for wake word: '{self.wake_word}'")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while True:
                try:
                    logging.info("Listerning........")
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                    try:
                        text = self.recognizer.recognize_google(audio).lower().strip()
                        logging.info(f" Heard: {text}")
                        # Wake if the core name appears anywhere, allow slight variations like 'jarvi'
                        tokens = text.replace(".", " ").replace(",", " ").split()
                        if (
                            self.wake_word in text
                            or any(tok.startswith("jarvi") for tok in tokens)
                        ):
                            logging.info(" Wake word detected! Starting camera immediately...")
                            return True
                    except sr.UnknownValueError:
                        pass
                except sr.WaitTimeoutError:
                    pass
                except KeyboardInterrupt:
                    logging.info(" Goodbye!")
                    return False
