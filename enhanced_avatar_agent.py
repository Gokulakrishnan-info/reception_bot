#!/usr/bin/env python3
"""
Enhanced Avatar Agent Module
Supports multiple animation types: images, CSS animations, custom drawings
"""

import logging
import threading
import os
import math
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter, QBrush, QRadialGradient, QPen, QPainterPath

class EnhancedAvatarAgent:
    """Enhanced Avatar Agent with multiple animation types"""
    
    def __init__(self):
        self._init_pyqt6()
    
    def _init_pyqt6(self):
        """Initialize PyQt6-based avatar interface"""
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])
        
        self.window = QMainWindow()
        self.window.setWindowTitle("Jarvis AI Assistant - Enhanced")
        self.window.setGeometry(100, 100, 500, 600)
        self.window.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Set modern styling
        self.window.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border-radius: 20px;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Avatar container with enhanced styling
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(250, 250)
        self.avatar_container.setStyleSheet("""
            QWidget {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8,
                    stop:0 #4facfe, stop:1 #00f2fe);
                border-radius: 125px;
                border: 4px solid #ffffff;
            }
        """)
        
        # Add enhanced drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 8)
        self.avatar_container.setGraphicsEffect(shadow)
        
        # Custom animated avatar widget
        self.avatar_widget = AnimatedAvatarWidget()
        self.avatar_widget.setFixedSize(200, 200)
        
        # Avatar container layout
        avatar_layout = QVBoxLayout(self.avatar_container)
        avatar_layout.addWidget(self.avatar_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add widgets to main layout
        layout.addWidget(self.avatar_container, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        
        # State management
        self.current_state = "idle"
        self.is_speaking = False
        self.closed = False
        
        # Animation timers
        self.state_timer = QTimer()
        self.state_timer.timeout.connect(self._update_state_animation)
        self.state_timer.start(50)  # Update every 50ms for smooth animation
        
        # Show window
        self.window.show()
        
        # Start idle animation
        self._update_state_animation()
    
    def _update_state_animation(self):
        """Update the current state animation"""
        if self.closed:
            return
        
        self.avatar_widget.set_state(self.current_state)
        self.avatar_widget.update()
    
    def show_speaking(self):
        """Show speaking state with animation"""
        if self.closed:
            return
        
        logging.info("🗣️ Avatar: Switching to speaking state")
        self.current_state = "speaking"
        self.is_speaking = True
    
    def show_listening(self):
        """Show listening state with animation"""
        if self.closed:
            return
        
        logging.info("👂 Avatar: Switching to listening state")
        self.current_state = "listening"
        self.is_speaking = False
    
    def show_idle(self):
        """Show idle state with animation"""
        if self.closed:
            return
        
        logging.info("🤖 Avatar: Switching to idle state")
        self.current_state = "idle"
        self.is_speaking = False
    
    def show_thinking(self):
        """Show thinking state with animation"""
        if self.closed:
            return
        
        logging.info("🤔 Avatar: Switching to thinking state")
        self.current_state = "thinking"
        self.is_speaking = False
    
    def show_processing(self):
        """Show processing state with animation"""
        if self.closed:
            return
        
        logging.info("⚙️ Avatar: Switching to processing state")
        self.current_state = "processing"
        self.is_speaking = False
    
    def show_happy(self):
        """Show happy state with animation"""
        if self.closed:
            return
        
        logging.info("😊 Avatar: Switching to happy state")
        self.current_state = "happy"
        self.is_speaking = False
    
    def on_close(self):
        """Close the avatar interface"""
        self.closed = True
        if hasattr(self, 'window'):
            self.window.close()
        try:
            if hasattr(self, 'app'):
                self.app.quit()
        except Exception:
            pass


class AnimatedAvatarWidget(QWidget):
    """Custom widget for drawing animated avatar states"""
    
    def __init__(self):
        super().__init__()
        self.state = "idle"
        self.animation_time = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(50)  # 20 FPS animation
        
    def set_state(self, state):
        """Set the current animation state"""
        self.state = state
    
    def _update_animation(self):
        """Update animation time"""
        self.animation_time += 0.05
        if self.animation_time > 2 * math.pi:
            self.animation_time = 0
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for drawing animated avatar"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 3
        
        # Draw based on state
        if self.state == "idle":
            self._draw_idle_state(painter, center_x, center_y, radius)
        elif self.state == "speaking":
            self._draw_speaking_state(painter, center_x, center_y, radius)
        elif self.state == "listening":
            self._draw_listening_state(painter, center_x, center_y, radius)
        elif self.state == "thinking":
            self._draw_thinking_state(painter, center_x, center_y, radius)
        elif self.state == "processing":
            self._draw_processing_state(painter, center_x, center_y, radius)
        elif self.state == "happy":
            self._draw_happy_state(painter, center_x, center_y, radius)
    
    def _draw_idle_state(self, painter, center_x, center_y, radius):
        """Draw idle robot state with breathing animation"""
        # Breathing effect
        breath_scale = 1.0 + 0.1 * math.sin(self.animation_time * 2)
        scaled_radius = radius * breath_scale
        
        # Draw robot head
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(QColor(70, 130, 180)))
        painter.drawEllipse(int(center_x - scaled_radius), int(center_y - scaled_radius), 
                           int(scaled_radius * 2), int(scaled_radius * 2))
        
        # Draw eyes with subtle blinking
        eye_y = center_y - scaled_radius * 0.3
        eye_spacing = scaled_radius * 0.4
        
        # Blinking animation
        blink = abs(math.sin(self.animation_time * 3)) > 0.8
        eye_height = 4 if blink else 16
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - eye_spacing - 8), int(eye_y - eye_height/2), 16, int(eye_height))
        painter.drawEllipse(int(center_x + eye_spacing - 8), int(eye_y - eye_height/2), 16, int(eye_height))
        
        # Draw pupils (only when not blinking)
        if not blink:
            painter.setBrush(QBrush(QColor(0, 0, 0)))
            painter.drawEllipse(int(center_x - eye_spacing - 4), int(eye_y - 4), 8, 8)
            painter.drawEllipse(int(center_x + eye_spacing - 4), int(eye_y - 4), 8, 8)
        
        # Draw mouth
        mouth_y = center_y + scaled_radius * 0.2
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawArc(int(center_x - 15), int(mouth_y - 10), 30, 20, 0, 180 * 16)
    
    def _draw_speaking_state(self, painter, center_x, center_y, radius):
        """Draw speaking robot state with pulsing animation and animated mouth"""
        # Pulsing effect
        pulse_scale = 1.0 + 0.15 * math.sin(self.animation_time * 8)
        scaled_radius = radius * pulse_scale
        
        # Draw robot head
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(QColor(50, 205, 50)))
        painter.drawEllipse(int(center_x - scaled_radius), int(center_y - scaled_radius), 
                           int(scaled_radius * 2), int(scaled_radius * 2))
        
        # Draw animated eyes (wider when speaking)
        eye_y = center_y - scaled_radius * 0.3
        eye_spacing = scaled_radius * 0.4
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - eye_spacing - 8), int(eye_y - 8), 16, 16)
        painter.drawEllipse(int(center_x + eye_spacing - 8), int(eye_y - 8), 16, 16)
        
        # Draw pupils with slight movement
        pupil_offset = math.sin(self.animation_time * 6) * 2
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(int(center_x - eye_spacing - 4 + pupil_offset), int(eye_y - 4), 8, 8)
        painter.drawEllipse(int(center_x + eye_spacing - 4 + pupil_offset), int(eye_y - 4), 8, 8)
        
        # Draw animated mouth (opens and closes)
        mouth_open = abs(math.sin(self.animation_time * 10))
        mouth_height = 5 + mouth_open * 15
        mouth_y = center_y + scaled_radius * 0.2
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - 12), int(mouth_y - mouth_height/2), 24, int(mouth_height))
        
        # Draw speech waves
        wave_x = center_x + scaled_radius + 20
        wave_y = center_y - scaled_radius * 0.5
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        
        for i in range(3):
            wave_offset = math.sin(self.animation_time * 6 + i) * 5
            painter.drawArc(int(wave_x + i * 15), int(wave_y + wave_offset), 20, 20, 0, 180 * 16)
    
    def _draw_listening_state(self, painter, center_x, center_y, radius):
        """Draw listening robot state with wave animation and attentive eyes"""
        # Wave effect
        wave_scale = 1.0 + 0.08 * math.sin(self.animation_time * 4)
        scaled_radius = radius * wave_scale
        
        # Draw robot head
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(QColor(255, 165, 0)))
        painter.drawEllipse(int(center_x - scaled_radius), int(center_y - scaled_radius), 
                           int(scaled_radius * 2), int(scaled_radius * 2))
        
        # Draw attentive eyes (slightly larger and focused)
        eye_y = center_y - scaled_radius * 0.3
        eye_spacing = scaled_radius * 0.4
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - eye_spacing - 10), int(eye_y - 10), 20, 20)
        painter.drawEllipse(int(center_x + eye_spacing - 10), int(eye_y - 10), 20, 20)
        
        # Draw focused pupils
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(int(center_x - eye_spacing - 5), int(eye_y - 5), 10, 10)
        painter.drawEllipse(int(center_x + eye_spacing - 5), int(eye_y - 5), 10, 10)
        
        # Draw listening mouth (slightly open)
        mouth_y = center_y + scaled_radius * 0.2
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - 8), int(mouth_y - 6), 16, 12)
        
        # Draw listening ears
        ear_y = center_y - scaled_radius * 0.8
        ear_spacing = scaled_radius * 0.6
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - ear_spacing - 12), int(ear_y - 12), 24, 24)
        painter.drawEllipse(int(center_x + ear_spacing - 12), int(ear_y - 12), 24, 24)
        
        # Draw sound waves
        wave_x = center_x - scaled_radius - 30
        wave_y = center_y
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        
        for i in range(3):
            wave_radius = 10 + i * 8 + math.sin(self.animation_time * 3 + i) * 3
            painter.drawEllipse(int(wave_x - wave_radius), int(wave_y - wave_radius), 
                               int(wave_radius * 2), int(wave_radius * 2))
    
    def _draw_thinking_state(self, painter, center_x, center_y, radius):
        """Draw thinking robot state with rotation animation and thoughtful expression"""
        # Rotation effect
        rotation = self.animation_time * 30
        
        # Draw robot head
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(QColor(138, 43, 226)))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius), 
                           int(radius * 2), int(radius * 2))
        
        # Draw thoughtful eyes (looking up and to the side)
        eye_y = center_y - radius * 0.3
        eye_spacing = radius * 0.4
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - eye_spacing - 8), int(eye_y - 8), 16, 16)
        painter.drawEllipse(int(center_x + eye_spacing - 8), int(eye_y - 8), 16, 16)
        
        # Draw pupils looking up and to the right (thinking pose)
        pupil_offset_x = math.sin(self.animation_time * 2) * 3
        pupil_offset_y = -2  # Looking up
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(int(center_x - eye_spacing - 4 + pupil_offset_x), int(eye_y - 4 + pupil_offset_y), 8, 8)
        painter.drawEllipse(int(center_x + eye_spacing - 4 + pupil_offset_x), int(eye_y - 4 + pupil_offset_y), 8, 8)
        
        # Draw thinking mouth (slightly open, thoughtful)
        mouth_y = center_y + radius * 0.2
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - 6), int(mouth_y - 4), 12, 8)
        
        # Draw thinking bubbles
        bubble_x = center_x + radius + 20
        bubble_y = center_y - radius * 0.5
        
        painter.setBrush(QBrush(QColor(255, 255, 255, 180)))
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        
        # Animated bubbles
        for i in range(3):
            bubble_offset = math.sin(self.animation_time * 2 + i) * 10
            bubble_size = 8 + math.sin(self.animation_time * 3 + i) * 4
            painter.drawEllipse(int(bubble_x + i * 15), int(bubble_y + bubble_offset), 
                               int(bubble_size), int(bubble_size))
        
        # Draw question mark
        painter.setPen(QPen(QColor(138, 43, 226), 2))
        painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        painter.drawText(int(center_x - 5), int(center_y + 5), "?")
    
    def _draw_processing_state(self, painter, center_x, center_y, radius):
        """Draw processing robot state with spinning animation and focused eyes"""
        # Spinning effect
        spin_angle = self.animation_time * 360
        
        # Draw robot head
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(QColor(255, 69, 0)))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius), 
                           int(radius * 2), int(radius * 2))
        
        # Draw focused eyes (intense processing)
        eye_y = center_y - radius * 0.3
        eye_spacing = radius * 0.4
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - eye_spacing - 8), int(eye_y - 8), 16, 16)
        painter.drawEllipse(int(center_x + eye_spacing - 8), int(eye_y - 8), 16, 16)
        
        # Draw intense pupils (processing focus)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(int(center_x - eye_spacing - 3), int(eye_y - 3), 6, 6)
        painter.drawEllipse(int(center_x + eye_spacing - 3), int(eye_y - 3), 6, 6)
        
        # Draw processing mouth (neutral, focused)
        mouth_y = center_y + radius * 0.2
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawArc(int(center_x - 10), int(mouth_y - 8), 20, 16, 0, 180 * 16)
        
        # Draw spinning gears
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(spin_angle)
        
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255, 100)))
        
        # Draw gear teeth
        for i in range(8):
            angle = i * 45
            x = math.cos(math.radians(angle)) * radius * 0.7
            y = math.sin(math.radians(angle)) * radius * 0.7
            painter.drawRect(int(x - 3), int(y - 8), 6, 16)
        
        painter.restore()
        
        # Draw processing dots
        dot_y = center_y + radius * 0.3
        for i in range(3):
            dot_x = center_x - 20 + i * 20
            dot_alpha = abs(math.sin(self.animation_time * 4 + i))
            painter.setBrush(QBrush(QColor(255, 255, 255, int(255 * dot_alpha))))
            painter.drawEllipse(int(dot_x - 4), int(dot_y - 4), 8, 8)
    
    def _draw_happy_state(self, painter, center_x, center_y, radius):
        """Draw happy robot state with bouncing animation and joyful expression"""
        # Bouncing effect
        bounce_offset = math.sin(self.animation_time * 4) * 5
        scaled_radius = radius * (1.0 + 0.05 * abs(math.sin(self.animation_time * 2)))
        
        # Draw robot head
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(QColor(255, 215, 0)))
        painter.drawEllipse(int(center_x - scaled_radius), int(center_y - scaled_radius + bounce_offset), 
                           int(scaled_radius * 2), int(scaled_radius * 2))
        
        # Draw happy eyes (squinted with joy)
        eye_y = center_y - scaled_radius * 0.3 + bounce_offset
        eye_spacing = scaled_radius * 0.4
        
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - eye_spacing - 8), int(eye_y - 8), 16, 16)
        painter.drawEllipse(int(center_x + eye_spacing - 8), int(eye_y - 8), 16, 16)
        
        # Draw happy pupils (slightly squinted)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawEllipse(int(center_x - eye_spacing - 3), int(eye_y - 3), 6, 6)
        painter.drawEllipse(int(center_x + eye_spacing - 3), int(eye_y - 3), 6, 6)
        
        # Draw happy mouth (big smile)
        mouth_y = center_y + scaled_radius * 0.2 + bounce_offset
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(int(center_x - 15), int(mouth_y - 8), 30, 16)
        
        # Draw sparkles
        sparkle_angle = self.animation_time * 2
        for i in range(4):
            angle = sparkle_angle + i * 90
            sparkle_x = center_x + math.cos(math.radians(angle)) * (scaled_radius + 20)
            sparkle_y = center_y + math.sin(math.radians(angle)) * (scaled_radius + 20)
            
            painter.setBrush(QBrush(QColor(255, 255, 255, 200)))
            painter.drawEllipse(int(sparkle_x - 3), int(sparkle_y - 3), 6, 6)
