#!/usr/bin/env python3
"""
Voice Agent Module
Handles voice interface functionality
"""

import time
import logging
import threading
import speech_recognition as sr
import boto3
import pyaudio
from config import AWS_REGION

class VoiceAgent:
    """Agent 8: Voice Interface with Interruption Support"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
        # Enhanced noise filtering settings
        self.recognizer.energy_threshold = 4000  # Higher threshold to filter out background noise
        self.recognizer.dynamic_energy_threshold = True  # Automatically adjust based on environment
        self.recognizer.pause_threshold = 0.8  # Wait longer for pauses to avoid cutting off speech
        self.recognizer.non_speaking_duration = 0.5  # Shorter non-speaking duration for better responsiveness
        self.recognizer.phrase_threshold = 0.3  # Lower phrase threshold for better phrase detection
        
        # Voice isolation settings
        self.recognizer.ambient_duration = 1.0  # Longer ambient noise calibration
        self.recognizer.ambient_energy_ratio = 1.5  # Higher ratio for better voice isolation
        
        self.is_speaking = False
        self.speaking_thread = None
        self.interruption_detected = False
        self.interruption_text = None
        
        # Amazon Polly client for high-quality TTS
        self.polly_client = boto3.client("polly", region_name=AWS_REGION)
        
        # Audio playback configuration
        self._audio_sample_rate = 16000
        self._audio_channels = 1
        self._audio_format = pyaudio.paInt16
        
        # Microphone selection for better voice isolation
        self._select_best_microphone()
        
    def _select_best_microphone(self):
        """Select the best microphone for voice isolation"""
        try:
            # List all available microphones
            mic_list = sr.Microphone.list_microphone_names()
            logging.info(f"Available microphones: {mic_list}")
            
            # Prefer microphones with names suggesting better quality
            preferred_keywords = ['array', 'beam', 'noise', 'cancellation', 'studio', 'condenser']
            selected_mic = None
            
            for i, mic_name in enumerate(mic_list):
                mic_lower = mic_name.lower()
                if any(keyword in mic_lower for keyword in preferred_keywords):
                    selected_mic = i
                    logging.info(f"Selected preferred microphone: {mic_name} (index {i})")
                    break
            
            if selected_mic is None:
                # Fallback to default microphone
                selected_mic = sr.Microphone.list_microphone_names().index(sr.Microphone.list_microphone_names()[0])
                logging.info(f"Using default microphone: {mic_list[selected_mic]}")
            
            self.selected_microphone = selected_mic
            
        except Exception as e:
            logging.warning(f"Could not select optimal microphone: {e}")
            self.selected_microphone = None
        
    def speak_with_interruption_detection(self, text):
        """Speak text with barge-in enabled: stop TTS and capture user speech if they start talking."""
        try:
            self.is_speaking = True
            self.interruption_detected = False
            self.interruption_text = None
            # Start lightweight interruption listener in parallel
            listener = threading.Thread(target=self._listen_for_interruption, daemon=True)
            listener.start()
            # Speak (playback loop checks self.interruption_detected)
            self._speak_text(text)
        finally:
            self.is_speaking = False
        # Give the listener a brief moment to finalize recognition if it just triggered
        try:
            if 'listener' in locals() and listener.is_alive():
                listener.join(timeout=0.2)
        except Exception:
            pass
        return self.interruption_detected, (self.interruption_text or None)
        
    def _synthesize_polly_stream(self, text: str):
        """Synthesize speech with Amazon Polly and return streaming AudioStream.
        Prefer Neural voices: try a list of common Neural-supported voices and pick the first that works in this region.
        If no Neural voice works, fall back to Standard for the first candidate.
        """
        neural_candidates = [
            "Joanna",  # en-US (Neural widely available)
            "Matthew", # en-US (Neural widely available)
            "Amy",     # en-GB (Neural in many regions)
            "Brian",   # en-GB
            "Emma",    # en-GB
            "Kendra",  # en-US
            "Salli",   # en-US
        ]
        # Try Neural candidates in order
        for voice_id in neural_candidates:
            try:
                response = self.polly_client.synthesize_speech(
                    Text=text,
                    OutputFormat="pcm",
                    SampleRate=str(self._audio_sample_rate),
                    VoiceId=voice_id,
                    Engine="neural"
                )
                logging.info(f"Polly: using Neural voice '{voice_id}'")
                return response.get("AudioStream")
            except Exception as e:
                msg = str(e)
                if "does not support the selected engine" in msg.lower() or "validationexception" in msg.lower():
                    logging.info(f"Polly: {voice_id} doesn't support Neural in this region; trying next candidate")
                    continue
                # Other errors: try next candidate
                logging.warning(f"Polly Neural attempt failed for {voice_id}: {e}")
                continue
        # If none of the Neural candidates worked, fall back to Standard on the first candidate
        fallback_voice = neural_candidates[0]
        try:
            response = self.polly_client.synthesize_speech(
                Text=text,
                OutputFormat="pcm",
                SampleRate=str(self._audio_sample_rate),
                VoiceId=fallback_voice,
                Engine="standard"
            )
            logging.info(f"Polly: falling back to Standard voice '{fallback_voice}'")
            return response.get("AudioStream")
        except Exception as e2:
            logging.error(f"Polly synth fallback error: {e2}")
            return None

    def _play_pcm_stream_with_interrupt(self, audio_stream):
        """Play PCM from a streaming AudioStream using PyAudio with interruption support."""
        if audio_stream is None:
            return
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=self._audio_format,
            channels=self._audio_channels,
            rate=self._audio_sample_rate,
            output=True,
            frames_per_buffer=1024
        )
        try:
            chunk_size = 4096
            while True:
                if self.interruption_detected:
                    break
                data = audio_stream.read(chunk_size)
                if not data:
                    break
                stream.write(data)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def _speak_text(self, text):
        """Internal method to speak text via Amazon Polly with interrupt support, low latency."""
        try:
            logging.info(f"🗣️ Speaking (Polly): {text}")
            audio_stream = self._synthesize_polly_stream(text)
            self._play_pcm_stream_with_interrupt(audio_stream)
        except Exception as e:
            logging.error(f"Speech error: {e}")
            
    def _listen_for_interruption(self):
        """Listen for interruptions while speaking (continuous, more sensitive, uses selected mic)."""
        # Use selected microphone if available
        try:
            if hasattr(self, 'selected_microphone') and self.selected_microphone is not None:
                source = sr.Microphone(device_index=self.selected_microphone)
            else:
                source = sr.Microphone()
        except Exception:
            source = sr.Microphone()

        with source as mic:
            try:
                # Quick ambient calibration
                self.recognizer.adjust_for_ambient_noise(mic, duration=0.2)
            except Exception:
                pass

            # Continuously poll for speech while TTS is ongoing
            while self.is_speaking and not self.interruption_detected:
                try:
                    audio = self.recognizer.listen(mic, timeout=0.7, phrase_time_limit=3)
                    result = self.recognizer.recognize_google(audio)
                    if result and len(result.strip()) > 0:
                        logging.info(f"🔄 Interruption detected: {result}")
                        self.interruption_detected = True
                        self.interruption_text = result.strip()
                        break
                except sr.WaitTimeoutError:
                    # No speech in this short window; keep listening
                    continue
                except sr.UnknownValueError:
                    # Detected sound but couldn't parse words; keep listening for clearer speech
                    continue
                except Exception as e:
                    logging.error(f"Interruption detection error: {e}")
                    break
        
    def speak(self, text):
        """Synchronous speak using Amazon Polly."""
        try:
            self.interruption_detected = False
            self._speak_text(text)
            time.sleep(0.3)
        except Exception as e:
            logging.error(f"Speech error: {e}")
            
    def listen(self, timeout=10, phrase_time_limit=15):
        """Listen for speech input with enhanced noise filtering"""
        try:
            # Use selected microphone if available
            if hasattr(self, 'selected_microphone') and self.selected_microphone is not None:
                source = sr.Microphone(device_index=self.selected_microphone)
            else:
                source = sr.Microphone()
                
            with source as mic:
                logging.info("🎤 Listening with enhanced noise filtering...")
                
                # Enhanced ambient noise calibration
                logging.info("🔧 Calibrating for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(mic, duration=1.0)
                
                # Log current energy threshold for debugging
                logging.info(f"📊 Energy threshold: {self.recognizer.energy_threshold}")
                
                # Listen with enhanced settings
                audio = self.recognizer.listen(
                    mic, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                
                # Use Google's enhanced speech recognition
                result = self.recognizer.recognize_google(
                    audio,
                    language="en-US",  # Specify language for better accuracy
                    show_all=False  # Get only the best result
                )
                
                logging.info(f"✅ Heard: {result}")
                return result
                
        except sr.UnknownValueError:
            logging.info("🔇 Could not understand audio - possible background noise")
            return None
        except sr.RequestError as e:
            logging.error(f"Speech recognition error: {e}")
            return None
        except Exception as e:
            logging.error(f"Voice error: {e}")
            return None
            
    def calibrate_for_environment(self, duration=3):
        """Calibrate the recognizer for the current environment noise level"""
        try:
            if hasattr(self, 'selected_microphone') and self.selected_microphone is not None:
                source = sr.Microphone(device_index=self.selected_microphone)
            else:
                source = sr.Microphone()
                
            with source as mic:
                logging.info(f"🔧 Calibrating for environment noise (duration: {duration}s)...")
                logging.info("Please remain quiet during calibration...")
                
                # Adjust for ambient noise with longer duration
                self.recognizer.adjust_for_ambient_noise(mic, duration=duration)
                
                # Log the calibrated settings
                logging.info(f"📊 Calibrated energy threshold: {self.recognizer.energy_threshold}")
                logging.info(f"📊 Dynamic energy threshold: {self.recognizer.dynamic_energy_threshold}")
                
                return True
                
        except Exception as e:
            logging.error(f"Environment calibration failed: {e}")
            return False
            
    def test_voice_sensitivity(self):
        """Test and adjust voice sensitivity for optimal performance"""
        try:
            logging.info("🎤 Testing voice sensitivity...")
            logging.info("Please speak at normal volume for 5 seconds...")
            
            # Test current settings
            result = self.listen(timeout=5, phrase_time_limit=5)
            
            if result:
                logging.info(f"✅ Voice detected: '{result}'")
                logging.info(f"📊 Current energy threshold: {self.recognizer.energy_threshold}")
                
                # Ask user if sensitivity is good
                logging.info("Is the voice sensitivity good? (speak 'yes' or 'no')")
                response = self.listen_for_short_response(timeout=5, phrase_time_limit=3)
                
                if response and 'no' in response.lower():
                    # Adjust sensitivity
                    logging.info("Adjusting sensitivity...")
                    self.recognizer.energy_threshold = int(self.recognizer.energy_threshold * 0.8)
                    logging.info(f"📊 New energy threshold: {self.recognizer.energy_threshold}")
                    
                    # Test again
                    logging.info("Please test again...")
                    self.test_voice_sensitivity()
                else:
                    logging.info("✅ Voice sensitivity optimized!")
                    
            else:
                logging.warning("⚠️ No voice detected - adjusting sensitivity...")
                self.recognizer.energy_threshold = int(self.recognizer.energy_threshold * 0.7)
                logging.info(f"📊 Adjusted energy threshold: {self.recognizer.energy_threshold}")
                
        except Exception as e:
            logging.error(f"Voice sensitivity test failed: {e}")
                
    def listen_for_short_response(self, timeout=7, phrase_time_limit=7):
        """Listen for short responses like Yes/No"""
        with sr.Microphone() as source:
            logging.info(" Listening for short response...")
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                result = self.recognizer.recognize_google(audio)
                logging.info(f" Short response: {result}")
                return result
            except sr.UnknownValueError:
                logging.info(" Could not understand short response")
                return None
            except sr.WaitTimeoutError:
                logging.info(" Timeout waiting for short response")
                return None
            except Exception as e:
                logging.error(f"Short response error: {e}")
                return None

    def listen_until_complete(self, max_total_time=15):
        """
        Listen continuously until the user stops speaking or reaches max time.
        This prevents cutting off users asking long questions.
        """
        with sr.Microphone() as source:
            logging.info("🎤 Listening for your complete question...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Set timeout to max_total_time to wait for speech to start
            # Set phrase_time_limit to allow complete responses
            try:
                audio = self.recognizer.listen(
                    source, 
                    timeout=max_total_time,  # Wait for speech to start within max_total_time
                    phrase_time_limit=10  # Allow up to 10 seconds of continuous speech
                )
                result = self.recognizer.recognize_google(audio)
                logging.info(f"✅ Complete question heard: {result}")
                return result
            except sr.UnknownValueError:
                logging.info("🔇 Could not understand audio")
                return None
            except sr.WaitTimeoutError:
                logging.info(f"⏰ No speech detected within {max_total_time} seconds")
                return None
            except sr.RequestError as e:
                logging.error(f"Speech recognition error: {e}")
                return None
            except Exception as e:
                logging.error(f"Voice error: {e}")
                return None

    def detect_multiple_questions(self, text):
        """
        Detect if user asked multiple questions in one input.
        Returns list of individual questions if detected.
        """
        if not text:
            return [text]
        
        # Common question indicators
        question_indicators = [
            "?", "what", "how", "when", "where", "why", "who", "which",
            "can you", "could you", "would you", "do you", "are you",
            "is there", "are there", "tell me", "explain", "describe"
        ]
        
        # Split by common conjunctions that often separate questions
        conjunctions = [" and ", " also ", " plus ", " furthermore ", " additionally "]
        
        questions = []
        current_text = text
        
        for conj in conjunctions:
            if conj in current_text.lower():
                parts = current_text.split(conj)
                for part in parts:
                    part = part.strip()
                    if part and any(indicator in part.lower() for indicator in question_indicators):
                        questions.append(part)
                if questions:
                    return questions
        
        # If no conjunctions found, check if it's one long question
        if any(indicator in text.lower() for indicator in question_indicators):
            return [text]
        
        return [text]

    def listen_for_multiple_questions(self, max_total_time=8):
        """
        Listen for user input with better patience and speech handling.
        Returns (raw_text, [parsed_questions]) for compatibility.
        """
        with sr.Microphone() as source:
            logging.info("🎤 Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Increase timeout to be more patient with speech
            timeout = min(max_total_time, 10)  # Wait up to 10 seconds for speech to start
            phrase_time_limit = min(max_total_time, 15)  # Allow longer phrases for complete thoughts
            
            try:
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,  # Wait longer for speech to start
                    phrase_time_limit=phrase_time_limit  # Allow longer continuous speech
                )
                result = self.recognizer.recognize_google(audio)
                logging.info(f"✅ Heard: {result}")
                
                # Parse for multiple questions if detected
                questions = self.detect_multiple_questions(result)
                return result, questions
                
            except sr.UnknownValueError:
                logging.info("🔇 Could not understand audio")
                return None, []
            except sr.WaitTimeoutError:
                logging.info(f"⏰ No speech detected within {timeout} seconds")
                return None, []
            except sr.RequestError as e:
                logging.error(f"Speech recognition error: {e}")
                return None, []
            except Exception as e:
                logging.error(f"Voice error: {e}")
                return None, []

    def listen_with_retry(self, max_attempts=2, max_total_time=10):
        """
        Listen for user input with automatic retry for unclear speech.
        Returns (raw_text, [parsed_questions]) or (None, []) if all attempts fail.
        """
        for attempt in range(max_attempts):
            logging.info(f"🎤 Listening attempt {attempt + 1}/{max_attempts}...")
            
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                try:
                    audio = self.recognizer.listen(
                        source, 
                        timeout=8,  # Wait for speech to start
                        phrase_time_limit=12  # Allow longer phrases
                    )
                    result = self.recognizer.recognize_google(audio)
                    
                    if result and len(result.strip()) >= 3:
                        logging.info(f"✅ Clear speech heard: {result}")
                        questions = self.detect_multiple_questions(result)
                        return result, questions
                    else:
                        logging.info(f"⚠️ Speech too short/unclear: '{result}'")
                        # Don't continue to next attempt if we got some result, even if unclear
                        if not result:
                            if attempt < max_attempts - 1:
                                continue
                        else:
                            # We got some result, return it even if unclear
                            return result, []
                        
                except sr.UnknownValueError:
                    logging.info(f"🔇 Attempt {attempt + 1}: Could not understand audio")
                    if attempt < max_attempts - 1:
                        continue
                except sr.WaitTimeoutError:
                    logging.info(f"⏰ Attempt {attempt + 1}: No speech detected")
                    if attempt < max_attempts - 1:
                        continue
                except Exception as e:
                    logging.error(f"❌ Attempt {attempt + 1} error: {e}")
                    if attempt < max_attempts - 1:
                        continue
        
        logging.info("❌ All listening attempts failed")
        return None, []

    def detect_incomplete_speech(self, text):
        """
        Detect if speech was likely cut off or incomplete.
        Returns True if speech seems incomplete.
        """
        if not text:
            return True
            
        text = text.strip()
        
        # Check for very short responses
        if len(text) < 3:
            return True
            
        # Check for incomplete sentences (ending with common incomplete patterns)
        incomplete_patterns = [
            "and", "but", "or", "so", "because", "if", "when", "where", "how",
            "what", "who", "why", "which", "that", "the", "a", "an", "in", "on",
            "at", "to", "for", "of", "with", "by", "from", "up", "down"
        ]
        
        text_lower = text.lower()
        for pattern in incomplete_patterns:
            if text_lower.endswith(f" {pattern}"):
                return True
                
        # Check for trailing prepositions or articles
        if text_lower.endswith((" the", " a", " an", " in", " on", " at", " to", " for")):
            return True
            
        return False
