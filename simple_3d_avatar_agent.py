#!/usr/bin/env python3
"""
Simple 3D Avatar Agent Module
Uses PyQt6's built-in 3D capabilities for realistic avatar rendering
"""

import logging
import math
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGraphicsDropShadowEffect, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter, QBrush, QRadialGradient, QPen, QPainterPath, QTransform

class Simple3DAvatarWidget(QWidget):
    """Simple 3D Avatar Widget using PyQt6's built-in 3D effects"""
    
    def __init__(self):
        super().__init__()
        self.state = "idle"
        self.animation_time = 0
        self.rotation_angle = 0
        self.scale_factor = 1.0
        self.eye_blink = False
        self.mouth_open = 0
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(50)  # 20 FPS
        
        # Set widget properties for 3D effect
        self.setMinimumSize(300, 300)
        self.setStyleSheet("""
            QWidget {
                background: qradialgradient(cx:0.5, cy:0.5, radius:1.0,
                    stop:0 #4facfe, stop:0.5 #00f2fe, stop:1.0 #1a1a2e);
                border-radius: 150px;
                border: 3px solid #ffffff;
            }
        """)
        
    def set_state(self, state):
        """Set the current animation state"""
        self.state = state
    
    def _update_animation(self):
        """Update animation parameters"""
        self.animation_time += 0.05
        if self.animation_time > 2 * math.pi:
            self.animation_time = 0
        
        # Update state-specific animations
        if self.state == "idle":
            self.rotation_angle = math.sin(self.animation_time * 0.5) * 5
            self.scale_factor = 1.0 + 0.05 * math.sin(self.animation_time * 2)
            self.eye_blink = abs(math.sin(self.animation_time * 3)) > 0.8
        elif self.state == "speaking":
            self.rotation_angle = math.sin(self.animation_time * 2) * 3
            self.scale_factor = 1.0 + 0.1 * math.sin(self.animation_time * 8)
            self.mouth_open = abs(math.sin(self.animation_time * 10))
        elif self.state == "listening":
            self.rotation_angle = math.sin(self.animation_time * 1.5) * 2
            self.scale_factor = 1.0 + 0.03 * math.sin(self.animation_time * 4)
            self.eye_blink = False
        elif self.state == "thinking":
            self.rotation_angle = math.sin(self.animation_time * 0.8) * 8
            self.scale_factor = 1.0 + 0.02 * math.sin(self.animation_time * 1.5)
        elif self.state == "processing":
            self.rotation_angle = self.animation_time * 30
            self.scale_factor = 1.0 + 0.05 * math.sin(self.animation_time * 6)
        elif self.state == "happy":
            self.rotation_angle = math.sin(self.animation_time * 2) * 4
            self.scale_factor = 1.0 + 0.08 * math.sin(self.animation_time * 3)
        
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for 3D avatar rendering"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        radius = min(width, height) / 3 * self.scale_factor
        
        # Apply 3D rotation transform
        transform = QTransform()
        transform.translate(center_x, center_y)
        transform.rotate(self.rotation_angle)
        transform.translate(-center_x, -center_y)
        painter.setTransform(transform)
        
        # Draw 3D robot head with depth effect
        self._draw_3d_robot_head(painter, center_x, center_y, radius)
    
    def _draw_3d_robot_head(self, painter, center_x, center_y, radius):
        """Draw 3D robot head with depth and lighting effects"""
        # Set color based on state
        if self.state == "idle":
            base_color = QColor(70, 130, 180)
        elif self.state == "speaking":
            base_color = QColor(50, 205, 50)
        elif self.state == "listening":
            base_color = QColor(255, 165, 0)
        elif self.state == "thinking":
            base_color = QColor(75, 0, 130)  # Deep purple for thinking
        elif self.state == "processing":
            base_color = QColor(0, 100, 0)   # Dark green for processing
        elif self.state == "happy":
            base_color = QColor(255, 215, 0)
        
        # Create 3D gradient for depth effect
        gradient = QRadialGradient(center_x, center_y, radius)
        gradient.setColorAt(0, base_color.lighter(150))
        gradient.setColorAt(0.7, base_color)
        gradient.setColorAt(1, base_color.darker(150))
        
        # Draw main head with 3D effect
        painter.setPen(QPen(QColor(255, 255, 255), 3))
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(int(center_x - radius), int(center_y - radius), 
                           int(radius * 2), int(radius * 2))
        
        # Draw 3D eyes with depth
        self._draw_3d_eyes(painter, center_x, center_y, radius)
        
        # Draw 3D mouth with depth
        self._draw_3d_mouth(painter, center_x, center_y, radius)
        
        # Draw state-specific 3D features
        self._draw_state_features(painter, center_x, center_y, radius)
    
    def _draw_3d_eyes(self, painter, center_x, center_y, radius):
        """Draw 3D eyes with depth and blinking animation"""
        if self.state == "thinking":
            # Special thinking eyes - more thoughtful appearance
            self._draw_thinking_eyes(painter, center_x, center_y, radius)
        elif self.state == "processing":
            # Special processing eyes - more focused appearance
            self._draw_processing_eyes(painter, center_x, center_y, radius)
        else:
            # Normal eyes for other states
            eye_y = center_y - radius * 0.3
            eye_spacing = radius * 0.4
            
            # Left eye
            left_eye_x = center_x - eye_spacing
            self._draw_3d_eye(painter, left_eye_x, eye_y, radius * 0.15, self.eye_blink)
            
            # Right eye
            right_eye_x = center_x + eye_spacing
            self._draw_3d_eye(painter, right_eye_x, eye_y, radius * 0.15, self.eye_blink)
    
    def _draw_3d_eye(self, painter, x, y, size, blinking):
        """Draw a single 3D eye with depth effect"""
        if blinking:
            # Blinking - squashed ellipse
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(int(x - size), int(y - size * 0.1), int(size * 2), int(size * 0.2))
        else:
            # Open eye with 3D depth
            # Eye socket shadow
            shadow_gradient = QRadialGradient(x, y, size * 1.2)
            shadow_gradient.setColorAt(0, QColor(0, 0, 0, 50))
            shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(shadow_gradient))
            painter.drawEllipse(int(x - size * 1.2), int(y - size * 1.2), int(size * 2.4), int(size * 2.4))
            
            # Eye white with 3D gradient
            eye_gradient = QRadialGradient(x, y, size)
            eye_gradient.setColorAt(0, QColor(255, 255, 255))
            eye_gradient.setColorAt(0.7, QColor(240, 240, 240))
            eye_gradient.setColorAt(1, QColor(220, 220, 220))
            painter.setBrush(QBrush(eye_gradient))
            painter.drawEllipse(int(x - size), int(y - size), int(size * 2), int(size * 2))
            
            # Pupil with 3D depth
            pupil_gradient = QRadialGradient(x, y, size * 0.4)
            pupil_gradient.setColorAt(0, QColor(0, 0, 0))
            pupil_gradient.setColorAt(1, QColor(50, 50, 50))
            painter.setBrush(QBrush(pupil_gradient))
            painter.drawEllipse(int(x - size * 0.4), int(y - size * 0.4), int(size * 0.8), int(size * 0.8))
            
                        # Eye highlight for 3D effect
            highlight_gradient = QRadialGradient(x - size * 0.3, y - size * 0.3, size * 0.2)
            highlight_gradient.setColorAt(0, QColor(255, 255, 255, 200))
            highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(highlight_gradient))
            painter.drawEllipse(int(x - size * 0.5), int(y - size * 0.5), int(size * 0.4), int(size * 0.4))
    
    def _draw_thinking_eyes(self, painter, center_x, center_y, radius):
        """Draw special thinking eyes - more thoughtful and contemplative"""
        eye_y = center_y - radius * 0.25
        eye_spacing = radius * 0.35
        
        # Draw larger, more thoughtful eyes
        for i, eye_x in enumerate([center_x - eye_spacing, center_x + eye_spacing]):
            # Eye socket with deeper shadow
            shadow_gradient = QRadialGradient(eye_x, eye_y, radius * 0.2)
            shadow_gradient.setColorAt(0, QColor(0, 0, 0, 80))
            shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(shadow_gradient))
            painter.drawEllipse(int(eye_x - radius * 0.2), int(eye_y - radius * 0.2), 
                               int(radius * 0.4), int(radius * 0.4))
            
            # Larger eye with thoughtful expression
            eye_gradient = QRadialGradient(eye_x, eye_y, radius * 0.18)
            eye_gradient.setColorAt(0, QColor(255, 255, 255))
            eye_gradient.setColorAt(0.6, QColor(240, 240, 240))
            eye_gradient.setColorAt(1, QColor(220, 220, 220))
            painter.setBrush(QBrush(eye_gradient))
            painter.drawEllipse(int(eye_x - radius * 0.18), int(eye_y - radius * 0.18), 
                               int(radius * 0.36), int(radius * 0.36))
            
            # Thoughtful pupil - looking up and to the side
            pupil_offset_x = math.sin(self.animation_time * 0.5 + i) * radius * 0.05
            pupil_offset_y = -radius * 0.08  # Looking up
            pupil_gradient = QRadialGradient(eye_x + pupil_offset_x, eye_y + pupil_offset_y, radius * 0.08)
            pupil_gradient.setColorAt(0, QColor(75, 0, 130))  # Purple pupil
            pupil_gradient.setColorAt(1, QColor(50, 0, 100))
            painter.setBrush(QBrush(pupil_gradient))
            painter.drawEllipse(int(eye_x + pupil_offset_x - radius * 0.08), 
                               int(eye_y + pupil_offset_y - radius * 0.08), 
                               int(radius * 0.16), int(radius * 0.16))
            
            # Eye highlight
            highlight_gradient = QRadialGradient(eye_x - radius * 0.08, eye_y - radius * 0.08, radius * 0.06)
            highlight_gradient.setColorAt(0, QColor(255, 255, 255, 200))
            highlight_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(highlight_gradient))
            painter.drawEllipse(int(eye_x - radius * 0.14), int(eye_y - radius * 0.14), 
                               int(radius * 0.12), int(radius * 0.12))
    
    def _draw_processing_eyes(self, painter, center_x, center_y, radius):
        """Draw special processing eyes - more focused and intense"""
        eye_y = center_y - radius * 0.3
        eye_spacing = radius * 0.4
        
        # Draw focused, intense eyes
        for i, eye_x in enumerate([center_x - eye_spacing, center_x + eye_spacing]):
            # Eye socket with intense shadow
            shadow_gradient = QRadialGradient(eye_x, eye_y, radius * 0.18)
            shadow_gradient.setColorAt(0, QColor(0, 0, 0, 100))
            shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(shadow_gradient))
            painter.drawEllipse(int(eye_x - radius * 0.18), int(eye_y - radius * 0.18), 
                               int(radius * 0.36), int(radius * 0.36))
            
            # Intense eye with processing glow
            eye_gradient = QRadialGradient(eye_x, eye_y, radius * 0.16)
            eye_gradient.setColorAt(0, QColor(255, 255, 255))
            eye_gradient.setColorAt(0.5, QColor(200, 255, 200))  # Slight green tint
            eye_gradient.setColorAt(1, QColor(180, 255, 180))
            painter.setBrush(QBrush(eye_gradient))
            painter.drawEllipse(int(eye_x - radius * 0.16), int(eye_y - radius * 0.16), 
                               int(radius * 0.32), int(radius * 0.32))
            
            # Small, focused pupil
            pupil_gradient = QRadialGradient(eye_x, eye_y, radius * 0.06)
            pupil_gradient.setColorAt(0, QColor(0, 100, 0))  # Green pupil
            pupil_gradient.setColorAt(1, QColor(0, 50, 0))
            painter.setBrush(QBrush(pupil_gradient))
            painter.drawEllipse(int(eye_x - radius * 0.06), int(eye_y - radius * 0.06), 
                               int(radius * 0.12), int(radius * 0.12))
            
            # Processing glow effect
            glow_gradient = QRadialGradient(eye_x, eye_y, radius * 0.25)
            glow_gradient.setColorAt(0, QColor(0, 255, 0, 30))
            glow_gradient.setColorAt(1, QColor(0, 255, 0, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.drawEllipse(int(eye_x - radius * 0.25), int(eye_y - radius * 0.25), 
                               int(radius * 0.5), int(radius * 0.5))
    
    def _draw_3d_mouth(self, painter, center_x, center_y, radius):
        """Draw 3D mouth with depth and animation"""
        mouth_y = center_y + radius * 0.2
        
        if self.state == "speaking":
            # Animated speaking mouth with 3D effect
            mouth_height = radius * 0.1 + self.mouth_open * radius * 0.2
            mouth_width = radius * 0.4
            
            # Mouth shadow
            shadow_gradient = QRadialGradient(center_x, mouth_y, mouth_width)
            shadow_gradient.setColorAt(0, QColor(0, 0, 0, 30))
            shadow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(shadow_gradient))
            painter.drawEllipse(int(center_x - mouth_width), int(mouth_y - mouth_height), 
                               int(mouth_width * 2), int(mouth_height * 2))
            
            # Mouth with 3D gradient
            mouth_gradient = QRadialGradient(center_x, mouth_y, mouth_width)
            mouth_gradient.setColorAt(0, QColor(255, 255, 255))
            mouth_gradient.setColorAt(0.7, QColor(240, 240, 240))
            mouth_gradient.setColorAt(1, QColor(220, 220, 220))
            painter.setBrush(QBrush(mouth_gradient))
            painter.drawEllipse(int(center_x - mouth_width), int(mouth_y - mouth_height), 
                               int(mouth_width * 2), int(mouth_height * 2))
            
        elif self.state == "listening":
            # Slightly open listening mouth
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(int(center_x - radius * 0.2), int(mouth_y - radius * 0.15), 
                               int(radius * 0.4), int(radius * 0.3))
        elif self.state == "thinking":
            # Thoughtful mouth - slightly open and contemplative
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(int(center_x - radius * 0.12), int(mouth_y - radius * 0.08), 
                               int(radius * 0.24), int(radius * 0.16))
        elif self.state == "processing":
            # Focused processing mouth - neutral and concentrated
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawLine(int(center_x - radius * 0.2), int(mouth_y), 
                           int(center_x + radius * 0.2), int(mouth_y))
        elif self.state == "happy":
            # Big happy smile with 3D effect
            smile_gradient = QRadialGradient(center_x, mouth_y, radius * 0.3)
            smile_gradient.setColorAt(0, QColor(255, 255, 255))
            smile_gradient.setColorAt(1, QColor(240, 240, 240))
            painter.setBrush(QBrush(smile_gradient))
            painter.drawEllipse(int(center_x - radius * 0.3), int(mouth_y - radius * 0.2), 
                               int(radius * 0.6), int(radius * 0.4))
        else:
            # Default mouth
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawArc(int(center_x - radius * 0.3), int(mouth_y - radius * 0.2), 
                           int(radius * 0.6), int(radius * 0.4), 0, 180 * 16)
    
    def _draw_state_features(self, painter, center_x, center_y, radius):
        """Draw state-specific 3D features"""
        if self.state == "speaking":
            self._draw_3d_speech_waves(painter, center_x, center_y, radius)
        elif self.state == "listening":
            self._draw_3d_listening_ears(painter, center_x, center_y, radius)
        elif self.state == "thinking":
            self._draw_3d_thinking_bubbles(painter, center_x, center_y, radius)
        elif self.state == "processing":
            self._draw_3d_processing_gears(painter, center_x, center_y, radius)
        elif self.state == "happy":
            self._draw_3d_happy_sparkles(painter, center_x, center_y, radius)
    
    def _draw_3d_speech_waves(self, painter, center_x, center_y, radius):
        """Draw 3D speech waves"""
        wave_x = center_x + radius + 20
        wave_y = center_y - radius * 0.5
        
        for i in range(3):
            wave_offset = math.sin(self.animation_time * 6 + i) * 5
            wave_gradient = QRadialGradient(wave_x + i * 15, wave_y + wave_offset, 10)
            wave_gradient.setColorAt(0, QColor(255, 255, 255, 200))
            wave_gradient.setColorAt(1, QColor(255, 255, 255, 50))
            painter.setBrush(QBrush(wave_gradient))
            painter.drawEllipse(int(wave_x + i * 15 - 10), int(wave_y + wave_offset - 10), 20, 20)
    
    def _draw_3d_listening_ears(self, painter, center_x, center_y, radius):
        """Draw 3D listening ears"""
        ear_y = center_y - radius * 0.8
        ear_spacing = radius * 0.6
        
        # Left ear
        left_ear_gradient = QRadialGradient(center_x - ear_spacing, ear_y, radius * 0.2)
        left_ear_gradient.setColorAt(0, QColor(255, 255, 255))
        left_ear_gradient.setColorAt(1, QColor(240, 240, 240))
        painter.setBrush(QBrush(left_ear_gradient))
        painter.drawEllipse(int(center_x - ear_spacing - radius * 0.2), int(ear_y - radius * 0.2), 
                           int(radius * 0.4), int(radius * 0.4))
        
        # Right ear
        right_ear_gradient = QRadialGradient(center_x + ear_spacing, ear_y, radius * 0.2)
        right_ear_gradient.setColorAt(0, QColor(255, 255, 255))
        right_ear_gradient.setColorAt(1, QColor(240, 240, 240))
        painter.setBrush(QBrush(right_ear_gradient))
        painter.drawEllipse(int(center_x + ear_spacing - radius * 0.2), int(ear_y - radius * 0.2), 
                           int(radius * 0.4), int(radius * 0.4))
    
    def _draw_3d_thinking_bubbles(self, painter, center_x, center_y, radius):
        """Draw 3D thinking bubbles - more elegant and thoughtful"""
        bubble_x = center_x + radius + 25
        bubble_y = center_y - radius * 0.6
        
        # Draw elegant thinking bubbles with question marks
        for i in range(3):
            bubble_offset = math.sin(self.animation_time * 1.5 + i) * 8
            bubble_size = radius * 0.08 + math.sin(self.animation_time * 2 + i) * radius * 0.03
            
            # Bubble with purple tint for thinking
            bubble_gradient = QRadialGradient(bubble_x + i * 20, bubble_y + bubble_offset, bubble_size)
            bubble_gradient.setColorAt(0, QColor(255, 255, 255, 200))
            bubble_gradient.setColorAt(0.7, QColor(200, 150, 255, 150))
            bubble_gradient.setColorAt(1, QColor(150, 100, 200, 80))
            painter.setBrush(QBrush(bubble_gradient))
            painter.drawEllipse(int(bubble_x + i * 20 - bubble_size), int(bubble_y + bubble_offset - bubble_size), 
                               int(bubble_size * 2), int(bubble_size * 2))
            
            # Add question mark inside bubble
            painter.setPen(QPen(QColor(75, 0, 130), 2))
            painter.setFont(QFont("Arial", int(bubble_size * 0.8)))
            painter.drawText(int(bubble_x + i * 20 - bubble_size * 0.3), 
                           int(bubble_y + bubble_offset - bubble_size * 0.3), 
                           int(bubble_size * 0.6), int(bubble_size * 0.6), 
                           Qt.AlignmentFlag.AlignCenter, "?")
    
    def _draw_3d_processing_gears(self, painter, center_x, center_y, radius):
        """Draw 3D processing gears - more modern and appealing"""
        gear_center_x = center_x
        gear_center_y = center_y
        
        # Rotate the entire gear system
        transform = painter.transform()
        transform.translate(gear_center_x, gear_center_y)
        transform.rotate(self.animation_time * 360)
        transform.translate(-gear_center_x, -gear_center_y)
        painter.setTransform(transform)
        
        # Draw modern gear teeth with green processing theme
        for i in range(6):  # Fewer teeth for cleaner look
            angle = i * 60
            x = gear_center_x + math.cos(math.radians(angle)) * radius * 0.6
            y = gear_center_y + math.sin(math.radians(angle)) * radius * 0.6
            
            # Modern gear tooth with green processing theme
            tooth_gradient = QRadialGradient(x, y, radius * 0.12)
            tooth_gradient.setColorAt(0, QColor(0, 255, 0, 120))
            tooth_gradient.setColorAt(0.7, QColor(0, 200, 0, 80))
            tooth_gradient.setColorAt(1, QColor(0, 150, 0, 40))
            painter.setBrush(QBrush(tooth_gradient))
            painter.drawEllipse(int(x - radius * 0.12), int(y - radius * 0.25), 
                               int(radius * 0.24), int(radius * 0.5))
        
        # Draw central processing hub
        hub_gradient = QRadialGradient(gear_center_x, gear_center_y, radius * 0.15)
        hub_gradient.setColorAt(0, QColor(0, 255, 0, 150))
        hub_gradient.setColorAt(1, QColor(0, 100, 0, 100))
        painter.setBrush(QBrush(hub_gradient))
        painter.drawEllipse(int(gear_center_x - radius * 0.15), int(gear_center_y - radius * 0.15), 
                           int(radius * 0.3), int(radius * 0.3))
        
        # Reset transform
        painter.setTransform(QTransform())
    
    def _draw_3d_happy_sparkles(self, painter, center_x, center_y, radius):
        """Draw 3D happy sparkles"""
        sparkle_angle = self.animation_time * 2
        
        for i in range(4):
            angle = sparkle_angle + i * 90
            sparkle_x = center_x + math.cos(math.radians(angle)) * (radius + 20)
            sparkle_y = center_y + math.sin(math.radians(angle)) * (radius + 20)
            
            sparkle_gradient = QRadialGradient(sparkle_x, sparkle_y, radius * 0.05)
            sparkle_gradient.setColorAt(0, QColor(255, 255, 255, 200))
            sparkle_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(sparkle_gradient))
            painter.drawEllipse(int(sparkle_x - radius * 0.05), int(sparkle_y - radius * 0.05), 
                               int(radius * 0.1), int(radius * 0.1))


class SimpleAvatar3DAgent:
    """Simple 3D Avatar Agent with built-in 3D effects"""
    
    def __init__(self):
        self._init_pyqt6()
    
    def _init_pyqt6(self):
        """Initialize PyQt6-based simple 3D avatar interface"""
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])
        
        # Process events to ensure proper initialization
        self.app.processEvents()
        
        self.window = QMainWindow()
        self.window.setWindowTitle("Jarvis AI Assistant - Simple 3D Avatar")
        self.window.setGeometry(100, 100, 500, 500)
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
        
        # Simple 3D Avatar widget
        self.avatar_widget = Simple3DAvatarWidget()
        self.avatar_widget.setFixedSize(300, 300)
        
        # Ensure the widget is properly initialized
        self.avatar_widget.show()
        self.avatar_widget.update()
        
        # Add drop shadow for 3D effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 8)
        self.avatar_widget.setGraphicsEffect(shadow)
        
        # Add to layout
        layout.addWidget(self.avatar_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        
        # State management
        self.current_state = "idle"
        self.closed = False
        
        # Show window
        self.window.show()
        
        # Force update and process events
        self.window.update()
        self.app.processEvents()
    
    def show_speaking(self):
        """Show speaking state with 3D animation"""
        if self.closed:
            return
        
        logging.info("🗣️ Simple 3D Avatar: Switching to speaking state")
        self.current_state = "speaking"
        self.avatar_widget.set_state("speaking")
        self.app.processEvents()
    
    def show_listening(self):
        """Show listening state with 3D animation"""
        if self.closed:
            return
        
        logging.info("👂 Simple 3D Avatar: Switching to listening state")
        self.current_state = "listening"
        self.avatar_widget.set_state("listening")
        self.app.processEvents()
    
    def show_idle(self):
        """Show idle state with 3D animation"""
        if self.closed:
            return
        
        logging.info("🤖 Simple 3D Avatar: Switching to idle state")
        self.current_state = "idle"
        self.avatar_widget.set_state("idle")
        self.app.processEvents()
    
    def show_thinking(self):
        """Show thinking state with 3D animation"""
        if self.closed:
            return
        
        logging.info("🤔 Simple 3D Avatar: Switching to thinking state")
        self.current_state = "thinking"
        self.avatar_widget.set_state("thinking")
        self.app.processEvents()
    
    def show_processing(self):
        """Show processing state with 3D animation"""
        if self.closed:
            return
        
        logging.info("⚙️ Simple 3D Avatar: Switching to processing state")
        self.current_state = "processing"
        self.avatar_widget.set_state("processing")
        self.app.processEvents()
    
    def show_happy(self):
        """Show happy state with 3D animation"""
        if self.closed:
            return
        
        logging.info("😊 Simple 3D Avatar: Switching to happy state")
        self.current_state = "happy"
        self.avatar_widget.set_state("happy")
        self.app.processEvents()
    
    def on_close(self):
        """Close the simple 3D avatar interface"""
        self.closed = True
        if hasattr(self, 'window'):
            self.window.close()
        try:
            if hasattr(self, 'app'):
                self.app.quit()
        except Exception:
            pass
