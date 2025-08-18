#!/usr/bin/env python3
"""
Avatar Agent Module
Handles the visual avatar interface
"""

import logging
import threading
import tkinter as tk

# Try to import PyQt6, fallback to Tkinter if not available
try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
    from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter, QBrush, QRadialGradient
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("PyQt6 not available, falling back to Tkinter")

class AvatarAgent:
    def __init__(self):
        if PYQT6_AVAILABLE:
            self._init_pyqt6()
        else:
            self._init_tkinter()
    
    def _init_pyqt6(self):
        """Initialize PyQt6-based avatar interface"""
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])
        
        self.window = QMainWindow()
        self.window.setWindowTitle("Jarvis AI Assistant")
        self.window.setGeometry(100, 100, 400, 500)
        self.window.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Set modern styling
        self.window.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
                border-radius: 15px;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Avatar container with shadow
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(200, 200)
        self.avatar_container.setStyleSheet("""
            QWidget {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 100px;
                border: 3px solid #ecf0f1;
            }
        """)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.avatar_container.setGraphicsEffect(shadow)
        
        # Avatar emoji label with enhanced robot emojis
        self.avatar_label = QLabel("🤖")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFont(QFont("Arial", 80))
        self.avatar_label.setStyleSheet("color: white;")
        
        # Enhanced emoji states for different robot expressions
        self.emoji_states = {
            "idle": ["🤖", "🤖", "🤖", "🤖", "🤖"],  # Subtle variations for idle
            "speaking": ["🗣️", "💬", "📢", "🗣️", "💬"],  # Speaking variations
            "listening": ["👂", "👂", "👂", "👂", "👂"],  # Listening variations
            "thinking": ["🤔", "🧠", "💭", "🤔", "🧠"],  # Thinking variations
            "happy": ["😊", "😄", "🤖", "😊", "😄"],  # Happy variations
            "processing": ["⚙️", "🔧", "⚡", "⚙️", "🔧"]  # Processing variations
        }
        self.current_emoji_index = 0
        
        # Avatar container layout
        avatar_layout = QVBoxLayout(self.avatar_container)
        avatar_layout.addWidget(self.avatar_label)
        
        # Add widgets to main layout
        layout.addWidget(self.avatar_container, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        
        # State management
        self.current_state = "idle"
        self.is_speaking = False
        self.closed = False
        
        # Animation timers
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self._animate_idle)
        self.idle_timer.start(3000)  # Animate every 3 seconds
        
        # Show window
        self.window.show()
        
        # Start idle animation
        self._animate_idle()
    
    def _init_tkinter(self):
        """Fallback to Tkinter if PyQt6 is not available"""
        # Enhanced emoji states for Tkinter fallback
        self.emoji_states = {
            "idle": ["🤖", "🤖", "🤖", "🤖", "🤖"],
            "speaking": ["🗣️", "💬", "📢", "🗣️", "💬"],
            "listening": ["👂", "👂", "👂", "👂", "👂"],
            "thinking": ["🤔", "🧠", "💭", "🤔", "🧠"],
            "happy": ["😊", "😄", "🤖", "😊", "😄"],
            "processing": ["⚙️", "🔧", "⚡", "⚙️", "🔧"]
        }
        self.current_emoji_index = 0
        
        # Check if we're in the main thread
        if threading.current_thread() is threading.main_thread():
            self.root = tk.Tk()
            self.root.title("Jarvis Avatar")
            self.root.geometry("300x400")
            self.root.protocol("WM_DELETE_WINDOW", self.on_close)
            
            # Avatar section
            self.avatar_label = tk.Label(self.root, text="🤖", font=("Arial", 120))
            self.avatar_label.pack(expand=True)
            
            self.is_speaking = False
            self.closed = False
            
            # Start the Tkinter mainloop in a separate thread
            self.thread = threading.Thread(target=self.root.mainloop, daemon=True)
            self.thread.start()
        else:
            # If not in main thread, create a simple non-GUI version
            self.root = None
            self.avatar_label = None
            self.is_speaking = False
            self.closed = False
            logging.warning("Tkinter GUI not available in non-main thread - using console mode")
    
    def _animate_idle(self):
        """Animate avatar in idle state with emoji cycling"""
        if not PYQT6_AVAILABLE or self.closed or self.current_state != "idle":
            return
        
        # Cycle through idle emojis
        self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["idle"])
        self.avatar_label.setText(self.emoji_states["idle"][self.current_emoji_index])
        
        # Subtle breathing animation
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(2000)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        current_geometry = self.avatar_container.geometry()
        expanded_geometry = current_geometry.adjusted(-2, -2, 2, 2)
        
        animation.setStartValue(current_geometry)
        animation.setEndValue(expanded_geometry)
        animation.finished.connect(lambda: self._reverse_idle_animation(current_geometry))
        animation.start()
    
    def _reverse_idle_animation(self, original_geometry):
        """Reverse the idle animation"""
        if self.closed or self.current_state != "idle":
            return
        
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(2000)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.setStartValue(self.avatar_container.geometry())
        animation.setEndValue(original_geometry)
        animation.start()
    
    def _post_ui(self, fn):
        """Safely post UI updates to the main thread"""
        if PYQT6_AVAILABLE:
            try:
                # Use QTimer.singleShot to ensure the function runs on the main thread
                QTimer.singleShot(0, fn)
            except Exception as e:
                # If timer/event loop isn't ready, try calling directly
                try:
                    fn()
                except Exception as e2:
                    logging.warning(f"UI update failed: {e2}")
                    # Last resort: try to update in the next event loop iteration
                    try:
                        QTimer.singleShot(100, fn)
                    except Exception:
                        pass
        else:
            # Tkinter fallback
            try:
                if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                    self.root.after(0, fn)
            except Exception as e:
                logging.warning(f"Tkinter UI update failed: {e}")
                # Console fallback
                print(f"🤖 Avatar State: {fn.__name__ if hasattr(fn, '__name__') else 'update'}")

    def _update_speaking_ui_pyqt(self):
        if self.closed:
            return
        # Stop idle animation
        self.idle_timer.stop()
        # Change avatar to speaking expression with cycling emojis
        self.current_emoji_index = 0
        self.avatar_label.setText(self.emoji_states["speaking"][self.current_emoji_index])
        # Animate speaking with pulsing effect
        self._animate_speaking()

    def show_speaking(self):
        """Show speaking state with animation"""
        if self.closed:
            return
        
        logging.info("🎤 Avatar: Switching to speaking state")
        self.current_state = "speaking"
        self.is_speaking = True
        
        if PYQT6_AVAILABLE:
            # Ensure UI update happens on main thread
            self._post_ui(self._update_speaking_ui_pyqt)
        else:
            if hasattr(self, 'root') and self.root:
                try:
                    self.root.after(0, lambda: self._update_speaking_ui())
                except Exception as e:
                    logging.warning(f"Tkinter speaking update failed: {e}")
                    print("🗣️ Avatar: Speaking")
            else:
                print("🗣️ Avatar: Speaking")
    
    def _animate_speaking(self):
        """Animate speaking state with pulsing effect and emoji cycling"""
        if self.closed or self.current_state != "speaking":
            return
        
        # Cycle through speaking emojis
        self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["speaking"])
        self.avatar_label.setText(self.emoji_states["speaking"][self.current_emoji_index])
        
        # Create pulsing animation
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(800)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        current_geometry = self.avatar_container.geometry()
        pulse_geometry = current_geometry.adjusted(-5, -5, 5, 5)
        
        animation.setStartValue(current_geometry)
        animation.setEndValue(pulse_geometry)
        animation.finished.connect(lambda: self._reverse_speaking_animation(current_geometry))
        animation.start()
    
    def _reverse_speaking_animation(self, original_geometry):
        """Reverse speaking animation"""
        if self.closed or self.current_state != "speaking":
            return
        
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(800)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.setStartValue(self.avatar_container.geometry())
        animation.setEndValue(original_geometry)
        animation.finished.connect(lambda: self._continue_speaking_animation() if self.current_state == "speaking" else None)
        animation.start()
    
    def _continue_speaking_animation(self):
        """Continue speaking animation if still speaking"""
        if self.current_state == "speaking" and not self.closed:
            QTimer.singleShot(500, self._animate_speaking)
    
    def _update_listening_ui_pyqt(self):
        if self.closed:
            return
        self.idle_timer.stop()
        # Change avatar to listening expression with cycling emojis
        self.current_emoji_index = 0
        self.avatar_label.setText(self.emoji_states["listening"][self.current_emoji_index])
        self._animate_listening()

    def show_listening(self):
        """Show listening state with animation"""
        if self.closed:
            return
        
        logging.info("👂 Avatar: Switching to listening state")
        self.current_state = "listening"
        self.is_speaking = False
        
        if PYQT6_AVAILABLE:
            # Ensure UI update happens on main thread
            self._post_ui(self._update_listening_ui_pyqt)
        else:
            if hasattr(self, 'root') and self.root:
                try:
                    self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["listening"])
                    self.avatar_label.config(text=self.emoji_states["listening"][self.current_emoji_index])
                except Exception as e:
                    logging.warning(f"Tkinter listening update failed: {e}")
                    print("👂 Avatar: Listening")
            else:
                print("👂 Avatar: Listening")
    
    def _animate_listening(self):
        """Animate listening state with wave effect and emoji cycling"""
        if self.closed or self.current_state != "listening":
            return
        
        # Cycle through listening emojis
        self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["listening"])
        self.avatar_label.setText(self.emoji_states["listening"][self.current_emoji_index])
        
        # Create wave animation
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(600)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        current_geometry = self.avatar_container.geometry()
        wave_geometry = current_geometry.adjusted(-3, -3, 3, 3)
        
        animation.setStartValue(current_geometry)
        animation.setEndValue(wave_geometry)
        animation.finished.connect(lambda: self._reverse_listening_animation(current_geometry))
        animation.start()
    
    def _reverse_listening_animation(self, original_geometry):
        """Reverse listening animation"""
        if self.closed or self.current_state != "listening":
            return
        
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(600)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.setStartValue(self.avatar_container.geometry())
        animation.setEndValue(original_geometry)
        animation.finished.connect(lambda: self._continue_listening_animation() if self.current_state == "listening" else None)
        animation.start()
    
    def _continue_listening_animation(self):
        """Continue listening animation if still listening"""
        if self.current_state == "listening" and not self.closed:
            QTimer.singleShot(400, self._animate_listening)
    
    def _update_idle_ui_pyqt(self):
        if self.closed:
            return
        # Reset to idle emoji and start cycling
        self.current_emoji_index = 0
        self.avatar_label.setText(self.emoji_states["idle"][self.current_emoji_index])
        self.idle_timer.start(3000)

    def _update_thinking_ui_pyqt(self):
        if self.closed:
            return
        self.idle_timer.stop()
        self.current_emoji_index = 0
        self.avatar_label.setText(self.emoji_states["thinking"][self.current_emoji_index])
        self._animate_thinking()

    def _update_processing_ui_pyqt(self):
        if self.closed:
            return
        self.idle_timer.stop()
        self.current_emoji_index = 0
        self.avatar_label.setText(self.emoji_states["processing"][self.current_emoji_index])
        self._animate_processing()

    def _update_happy_ui_pyqt(self):
        if self.closed:
            return
        self.idle_timer.stop()
        self.current_emoji_index = 0
        self.avatar_label.setText(self.emoji_states["happy"][self.current_emoji_index])
        self._animate_happy()

    def show_idle(self):
        """Show idle state with animation"""
        if self.closed:
            return
        
        logging.info("🤖 Avatar: Switching to idle state")
        self.current_state = "idle"
        self.is_speaking = False
        
        if PYQT6_AVAILABLE:
            # Ensure UI update happens on main thread
            self._post_ui(self._update_idle_ui_pyqt)
        else:
            if hasattr(self, 'root') and self.root:
                try:
                    self.root.after(0, lambda: self._update_idle_ui())
                except Exception as e:
                    logging.warning(f"Tkinter idle update failed: {e}")
                    print("🤖 Avatar: Idle")
            else:
                print("🤖 Avatar: Idle")

    def show_thinking(self):
        """Show thinking state with animation"""
        if self.closed:
            return
        
        logging.info("🤔 Avatar: Switching to thinking state")
        self.current_state = "thinking"
        self.is_speaking = False
        
        if PYQT6_AVAILABLE:
            self._post_ui(self._update_thinking_ui_pyqt)
        else:
            if hasattr(self, 'root') and self.root:
                try:
                    self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["thinking"])
                    self.avatar_label.config(text=self.emoji_states["thinking"][self.current_emoji_index])
                except Exception as e:
                    logging.warning(f"Tkinter thinking update failed: {e}")
                    print("🤔 Avatar: Thinking")
            else:
                print("🤔 Avatar: Thinking")

    def show_processing(self):
        """Show processing state with animation"""
        if self.closed:
            return
        
        logging.info("⚙️ Avatar: Switching to processing state")
        self.current_state = "processing"
        self.is_speaking = False
        
        if PYQT6_AVAILABLE:
            self._post_ui(self._update_processing_ui_pyqt)
        else:
            if hasattr(self, 'root') and self.root:
                try:
                    self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["processing"])
                    self.avatar_label.config(text=self.emoji_states["processing"][self.current_emoji_index])
                except Exception as e:
                    logging.warning(f"Tkinter processing update failed: {e}")
                    print("⚙️ Avatar: Processing")
            else:
                print("⚙️ Avatar: Processing")

    def show_happy(self):
        """Show happy state with animation"""
        if self.closed:
            return
        
        logging.info("😊 Avatar: Switching to happy state")
        self.current_state = "happy"
        self.is_speaking = False
        
        if PYQT6_AVAILABLE:
            self._post_ui(self._update_happy_ui_pyqt)
        else:
            if hasattr(self, 'root') and self.root:
                try:
                    self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["happy"])
                    self.avatar_label.config(text=self.emoji_states["happy"][self.current_emoji_index])
                except Exception as e:
                    logging.warning(f"Tkinter happy update failed: {e}")
                    print("😊 Avatar: Happy")
            else:
                print("😊 Avatar: Happy")

    def _update_speaking_ui(self):
        """Update UI for speaking state - called in main thread (Tkinter fallback)"""
        if not self.closed:
            self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["speaking"])
            self.avatar_label.config(text=self.emoji_states["speaking"][self.current_emoji_index])
            self.is_speaking = True

    def _update_idle_ui(self):
        """Update UI for idle state - called in main thread (Tkinter fallback)"""
        if not self.closed:
            self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["idle"])
            self.avatar_label.config(text=self.emoji_states["idle"][self.current_emoji_index])
            self.is_speaking = False

    def _animate_thinking(self):
        """Animate thinking state with rotation effect"""
        if self.closed or self.current_state != "thinking":
            return
        
        # Cycle through thinking emojis
        self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["thinking"])
        self.avatar_label.setText(self.emoji_states["thinking"][self.current_emoji_index])
        
        # Create thinking animation (gentle rotation)
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(1500)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        current_geometry = self.avatar_container.geometry()
        rotated_geometry = current_geometry.adjusted(-1, -1, 1, 1)
        
        animation.setStartValue(current_geometry)
        animation.setEndValue(rotated_geometry)
        animation.finished.connect(lambda: self._reverse_thinking_animation(current_geometry))
        animation.start()

    def _reverse_thinking_animation(self, original_geometry):
        """Reverse thinking animation"""
        if self.closed or self.current_state != "thinking":
            return
        
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(1500)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.setStartValue(self.avatar_container.geometry())
        animation.setEndValue(original_geometry)
        animation.finished.connect(lambda: self._continue_thinking_animation() if self.current_state == "thinking" else None)
        animation.start()

    def _continue_thinking_animation(self):
        """Continue thinking animation if still thinking"""
        if self.current_state == "thinking" and not self.closed:
            QTimer.singleShot(800, self._animate_thinking)

    def _animate_processing(self):
        """Animate processing state with spinning effect"""
        if self.closed or self.current_state != "processing":
            return
        
        # Cycle through processing emojis
        self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["processing"])
        self.avatar_label.setText(self.emoji_states["processing"][self.current_emoji_index])
        
        # Create processing animation (spinning effect)
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(500)
        animation.setEasingCurve(QEasingCurve.Type.Linear)
        
        current_geometry = self.avatar_container.geometry()
        spin_geometry = current_geometry.adjusted(-2, -2, 2, 2)
        
        animation.setStartValue(current_geometry)
        animation.setEndValue(spin_geometry)
        animation.finished.connect(lambda: self._reverse_processing_animation(current_geometry))
        animation.start()

    def _reverse_processing_animation(self, original_geometry):
        """Reverse processing animation"""
        if self.closed or self.current_state != "processing":
            return
        
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(500)
        animation.setEasingCurve(QEasingCurve.Type.Linear)
        animation.setStartValue(self.avatar_container.geometry())
        animation.setEndValue(original_geometry)
        animation.finished.connect(lambda: self._continue_processing_animation() if self.current_state == "processing" else None)
        animation.start()

    def _continue_processing_animation(self):
        """Continue processing animation if still processing"""
        if self.current_state == "processing" and not self.closed:
            QTimer.singleShot(300, self._animate_processing)

    def _animate_happy(self):
        """Animate happy state with bouncing effect"""
        if self.closed or self.current_state != "happy":
            return
        
        # Cycle through happy emojis
        self.current_emoji_index = (self.current_emoji_index + 1) % len(self.emoji_states["happy"])
        self.avatar_label.setText(self.emoji_states["happy"][self.current_emoji_index])
        
        # Create happy animation (bouncing effect)
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(1000)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        
        current_geometry = self.avatar_container.geometry()
        bounce_geometry = current_geometry.adjusted(-4, -4, 4, 4)
        
        animation.setStartValue(current_geometry)
        animation.setEndValue(bounce_geometry)
        animation.finished.connect(lambda: self._reverse_happy_animation(current_geometry))
        animation.start()

    def _reverse_happy_animation(self, original_geometry):
        """Reverse happy animation"""
        if self.closed or self.current_state != "happy":
            return
        
        animation = QPropertyAnimation(self.avatar_container, b"geometry")
        animation.setDuration(1000)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        animation.setStartValue(self.avatar_container.geometry())
        animation.setEndValue(original_geometry)
        animation.finished.connect(lambda: self._continue_happy_animation() if self.current_state == "happy" else None)
        animation.start()

    def _continue_happy_animation(self):
        """Continue happy animation if still happy"""
        if self.current_state == "happy" and not self.closed:
            QTimer.singleShot(600, self._animate_happy)

    def on_close(self):
        """Close the avatar interface"""
        self.closed = True
        if PYQT6_AVAILABLE:
            if hasattr(self, 'window'):
                self.window.close()
            # Gracefully stop the Qt event loop
            try:
                if hasattr(self, 'app'):
                    self.app.quit()
            except Exception:
                pass
        else:
            if hasattr(self, 'root'):
                self.root.destroy()
