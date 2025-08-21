#!/usr/bin/env python3
"""
Enhanced Avatar Agent using PNG images
Displays different avatar states using stored PNG files
"""

import sys
import time
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPixmap

class EnhancedAvatarAgent:
    """Enhanced Avatar Agent using PNG images for different states"""
    
    def __init__(self):
        self.app = None
        self.window = None
        self.current_state = "idle"
        self.closed = False
        
        # Initialize PyQt6 first
        self._init_pyqt6()
        
        # Load avatar images after QApplication is created
        self.avatar_images = {
            "idle": QPixmap(r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\avatar\avatar-idle.png"),
            "speaking": QPixmap(r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\avatar\avatar-speaking.png"),
            "listening": QPixmap(r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\avatar\avatar-listening.png"),
            "happy": QPixmap(r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\avatar\avatar-happy.png"),
            "processing": QPixmap(r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\avatar\avatar-processing.png"),
            "thinking": QPixmap(r"C:\Users\Gokulakrishnan\Documents\Python_Learnings\CAM_AI_ASSISTANT\Modular_AI_Bot\avatar\avatar-thinking.png"),
        }
        
        # Start with idle state
        self.show_idle()
        
    def _init_pyqt6(self):
        """Initialize PyQt6 application and window"""
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
            
        # Create main window
        self.window = QMainWindow()
        self.window.setWindowTitle("Jarvis AI Assistant - Enhanced")
        self.window.setGeometry(100, 100, 400, 400)
        self.window.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create avatar label
        self.avatar_label = QLabel()
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setMinimumSize(300, 300)
        layout.addWidget(self.avatar_label)
        
        # Show window
        self.window.show()
        self.app.processEvents()
        
    def _display_state(self, state_name):
        """Display the specified avatar state"""
        if state_name in self.avatar_images:
            self.current_state = state_name
            pixmap = self.avatar_images[state_name]
            
            # Scale pixmap to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.avatar_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.avatar_label.setPixmap(scaled_pixmap)
            self.app.processEvents()
            logging.info(f"🤖 Avatar: Switching to {state_name} state")
        else:
            logging.warning(f"Avatar state '{state_name}' not found")
    
    def show_idle(self):
        """Show idle state"""
        self._display_state("idle")
    
    def show_speaking(self):
        """Show speaking state"""
        self._display_state("speaking")
    
    def show_listening(self):
        """Show listening state"""
        self._display_state("listening")
    
    def show_thinking(self):
        """Show thinking state"""
        self._display_state("thinking")
    
    def show_processing(self):
        """Show processing state"""
        self._display_state("processing")
    
    def show_happy(self):
        """Show happy state"""
        self._display_state("happy")
    
    def on_close(self):
        """Clean up resources"""
        if self.window and not self.closed:
            self.window.close()
            self.closed = True
        if self.app:
            self.app.quit()
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.on_close()
