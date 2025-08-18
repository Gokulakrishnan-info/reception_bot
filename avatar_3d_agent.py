#!/usr/bin/env python3
"""
3D Avatar Agent Module
Uses PyQt6 OpenGL for realistic 3D avatar rendering
"""

import logging
import math
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLVersionProfile
from PyQt6.QtGui import QOpenGLContext, QSurfaceFormat
import OpenGL.GL as gl
import OpenGL.GLU as glu

class OpenGL3DAvatarWidget(QOpenGLWidget):
    """3D Avatar Widget using OpenGL"""
    
    def __init__(self):
        super().__init__()
        self.state = "idle"
        self.animation_time = 0
        self.rotation_x = 0
        self.rotation_y = 0
        self.eye_blink = 0
        self.mouth_open = 0
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(50)  # 20 FPS
        
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
            self.rotation_y = math.sin(self.animation_time * 0.5) * 5
            self.eye_blink = abs(math.sin(self.animation_time * 3)) > 0.8
        elif self.state == "speaking":
            self.rotation_y = math.sin(self.animation_time * 2) * 3
            self.mouth_open = abs(math.sin(self.animation_time * 10))
        elif self.state == "listening":
            self.rotation_x = math.sin(self.animation_time * 1.5) * 2
            self.eye_blink = False
        elif self.state == "thinking":
            self.rotation_y = math.sin(self.animation_time * 0.8) * 8
            self.rotation_x = math.cos(self.animation_time * 0.6) * 3
        elif self.state == "processing":
            self.rotation_y = self.animation_time * 30
        elif self.state == "happy":
            self.rotation_y = math.sin(self.animation_time * 2) * 4
            self.rotation_x = math.sin(self.animation_time * 1.5) * 2
        
        self.update()
    
    def initializeGL(self):
        """Initialize OpenGL context"""
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        
        # Set up lighting
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, [1.0, 1.0, 1.0, 0.0])
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
    
    def resizeGL(self, width, height):
        """Handle window resize"""
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluPerspective(45, width / height, 0.1, 100.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
    
    def paintGL(self):
        """Render the 3D avatar"""
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        
        # Position camera
        gl.glTranslatef(0.0, 0.0, -5.0)
        gl.glRotatef(self.rotation_x, 1.0, 0.0, 0.0)
        gl.glRotatef(self.rotation_y, 0.0, 1.0, 0.0)
        
        # Draw 3D robot head based on state
        self._draw_3d_robot_head()
    
    def _draw_3d_robot_head(self):
        """Draw 3D robot head with state-specific features"""
        # Set color based on state
        if self.state == "idle":
            gl.glColor3f(0.3, 0.5, 0.7)  # Blue
        elif self.state == "speaking":
            gl.glColor3f(0.2, 0.8, 0.2)  # Green
        elif self.state == "listening":
            gl.glColor3f(1.0, 0.6, 0.0)  # Orange
        elif self.state == "thinking":
            gl.glColor3f(0.5, 0.2, 0.8)  # Purple
        elif self.state == "processing":
            gl.glColor3f(1.0, 0.3, 0.0)  # Red
        elif self.state == "happy":
            gl.glColor3f(1.0, 0.8, 0.0)  # Gold
        
        # Draw main head sphere
        self._draw_sphere(0.8, 20, 20)
        
        # Draw eyes
        self._draw_3d_eyes()
        
        # Draw mouth
        self._draw_3d_mouth()
        
        # Draw state-specific features
        self._draw_state_features()
    
    def _draw_sphere(self, radius, slices, stacks):
        """Draw a sphere using OpenGL"""
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + float(i) / stacks)
            z0 = math.sin(lat0)
            zr0 = math.cos(lat0)
            
            lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
            z1 = math.sin(lat1)
            zr1 = math.cos(lat1)
            
            gl.glBegin(gl.GL_QUAD_STRIP)
            for j in range(slices + 1):
                lng = 2 * math.pi * float(j) / slices
                x = math.cos(lng)
                y = math.sin(lng)
                
                gl.glNormal3f(x * zr0, y * zr0, z0)
                gl.glVertex3f(x * zr0 * radius, y * zr0 * radius, z0 * radius)
                gl.glNormal3f(x * zr1, y * zr1, z1)
                gl.glVertex3f(x * zr1 * radius, y * zr1 * radius, z1 * radius)
            gl.glEnd()
    
    def _draw_3d_eyes(self):
        """Draw 3D eyes with blinking animation"""
        # Left eye
        gl.glPushMatrix()
        gl.glTranslatef(-0.3, 0.2, 0.6)
        
        if self.eye_blink:
            # Blinking - squashed sphere
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glScalef(1.0, 0.1, 1.0)
            self._draw_sphere(0.15, 10, 10)
        else:
            # Open eye
            gl.glColor3f(1.0, 1.0, 1.0)
            self._draw_sphere(0.15, 10, 10)
            
            # Pupil
            gl.glColor3f(0.0, 0.0, 0.0)
            gl.glTranslatef(0.0, 0.0, 0.05)
            self._draw_sphere(0.08, 8, 8)
        
        gl.glPopMatrix()
        
        # Right eye
        gl.glPushMatrix()
        gl.glTranslatef(0.3, 0.2, 0.6)
        
        if self.eye_blink:
            # Blinking - squashed sphere
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glScalef(1.0, 0.1, 1.0)
            self._draw_sphere(0.15, 10, 10)
        else:
            # Open eye
            gl.glColor3f(1.0, 1.0, 1.0)
            self._draw_sphere(0.15, 10, 10)
            
            # Pupil
            gl.glColor3f(0.0, 0.0, 0.0)
            gl.glTranslatef(0.0, 0.0, 0.05)
            self._draw_sphere(0.08, 8, 8)
        
        gl.glPopMatrix()
    
    def _draw_3d_mouth(self):
        """Draw 3D mouth with animation"""
        gl.glPushMatrix()
        gl.glTranslatef(0.0, -0.3, 0.6)
        
        if self.state == "speaking":
            # Animated speaking mouth
            mouth_height = 0.1 + self.mouth_open * 0.2
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glScalef(0.4, mouth_height, 0.1)
            self._draw_sphere(0.3, 8, 8)
        elif self.state == "listening":
            # Slightly open listening mouth
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glScalef(0.3, 0.15, 0.1)
            self._draw_sphere(0.3, 8, 8)
        elif self.state == "thinking":
            # Small thinking mouth
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glScalef(0.2, 0.1, 0.1)
            self._draw_sphere(0.3, 8, 8)
        elif self.state == "happy":
            # Big happy smile
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glScalef(0.5, 0.2, 0.1)
            self._draw_sphere(0.3, 8, 8)
        else:
            # Default mouth
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glScalef(0.3, 0.05, 0.1)
            self._draw_sphere(0.3, 8, 8)
        
        gl.glPopMatrix()
    
    def _draw_state_features(self):
        """Draw state-specific 3D features"""
        if self.state == "speaking":
            # Speech waves
            self._draw_speech_waves()
        elif self.state == "listening":
            # Listening ears
            self._draw_listening_ears()
        elif self.state == "thinking":
            # Thinking bubbles
            self._draw_thinking_bubbles()
        elif self.state == "processing":
            # Processing gears
            self._draw_processing_gears()
        elif self.state == "happy":
            # Happy sparkles
            self._draw_happy_sparkles()
    
    def _draw_speech_waves(self):
        """Draw 3D speech waves"""
        gl.glColor3f(1.0, 1.0, 1.0)
        for i in range(3):
            gl.glPushMatrix()
            gl.glTranslatef(1.0 + i * 0.3, 0.0, 0.0)
            wave_offset = math.sin(self.animation_time * 6 + i) * 0.1
            gl.glTranslatef(0.0, wave_offset, 0.0)
            gl.glScalef(0.1, 0.1, 0.1)
            self._draw_sphere(0.5, 8, 8)
            gl.glPopMatrix()
    
    def _draw_listening_ears(self):
        """Draw 3D listening ears"""
        gl.glColor3f(1.0, 1.0, 1.0)
        
        # Left ear
        gl.glPushMatrix()
        gl.glTranslatef(-0.8, 0.5, 0.0)
        gl.glScalef(0.2, 0.3, 0.1)
        self._draw_sphere(0.5, 8, 8)
        gl.glPopMatrix()
        
        # Right ear
        gl.glPushMatrix()
        gl.glTranslatef(0.8, 0.5, 0.0)
        gl.glScalef(0.2, 0.3, 0.1)
        self._draw_sphere(0.5, 8, 8)
        gl.glPopMatrix()
    
    def _draw_thinking_bubbles(self):
        """Draw 3D thinking bubbles"""
        gl.glColor3f(1.0, 1.0, 1.0)
        for i in range(3):
            gl.glPushMatrix()
            gl.glTranslatef(1.2 + i * 0.2, 0.0, 0.0)
            bubble_offset = math.sin(self.animation_time * 2 + i) * 0.1
            gl.glTranslatef(0.0, bubble_offset, 0.0)
            bubble_size = 0.05 + math.sin(self.animation_time * 3 + i) * 0.02
            gl.glScalef(bubble_size, bubble_size, bubble_size)
            self._draw_sphere(0.5, 8, 8)
            gl.glPopMatrix()
    
    def _draw_processing_gears(self):
        """Draw 3D processing gears"""
        gl.glColor3f(1.0, 1.0, 1.0)
        gl.glPushMatrix()
        gl.glRotatef(self.animation_time * 360, 0.0, 0.0, 1.0)
        
        # Draw gear teeth
        for i in range(8):
            gl.glPushMatrix()
            angle = i * 45
            gl.glRotatef(angle, 0.0, 0.0, 1.0)
            gl.glTranslatef(0.6, 0.0, 0.0)
            gl.glScalef(0.1, 0.3, 0.1)
            self._draw_sphere(0.5, 4, 4)
            gl.glPopMatrix()
        
        gl.glPopMatrix()
    
    def _draw_happy_sparkles(self):
        """Draw 3D happy sparkles"""
        gl.glColor3f(1.0, 1.0, 1.0)
        sparkle_angle = self.animation_time * 2
        for i in range(4):
            gl.glPushMatrix()
            angle = sparkle_angle + i * 90
            x = math.cos(math.radians(angle)) * 1.2
            y = math.sin(math.radians(angle)) * 1.2
            gl.glTranslatef(x, y, 0.0)
            gl.glScalef(0.05, 0.05, 0.05)
            self._draw_sphere(0.5, 6, 6)
            gl.glPopMatrix()


class Avatar3DAgent:
    """3D Avatar Agent with OpenGL rendering"""
    
    def __init__(self):
        self._init_pyqt6()
    
    def _init_pyqt6(self):
        """Initialize PyQt6-based 3D avatar interface"""
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication([])
        
        # Configure OpenGL
        format = QSurfaceFormat()
        format.setDepthBufferSize(24)
        format.setStencilBufferSize(8)
        format.setVersion(2, 0)
        format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        QSurfaceFormat.setDefaultFormat(format)
        
        self.window = QMainWindow()
        self.window.setWindowTitle("Jarvis AI Assistant - 3D Avatar")
        self.window.setGeometry(100, 100, 600, 600)
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
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 3D Avatar widget
        self.avatar_widget = OpenGL3DAvatarWidget()
        self.avatar_widget.setFixedSize(500, 500)
        
        # Add to layout
        layout.addWidget(self.avatar_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # State management
        self.current_state = "idle"
        self.closed = False
        
        # Show window
        self.window.show()
    
    def show_speaking(self):
        """Show speaking state with 3D animation"""
        if self.closed:
            return
        
        logging.info("🗣️ 3D Avatar: Switching to speaking state")
        self.current_state = "speaking"
        self.avatar_widget.set_state("speaking")
    
    def show_listening(self):
        """Show listening state with 3D animation"""
        if self.closed:
            return
        
        logging.info("👂 3D Avatar: Switching to listening state")
        self.current_state = "listening"
        self.avatar_widget.set_state("listening")
    
    def show_idle(self):
        """Show idle state with 3D animation"""
        if self.closed:
            return
        
        logging.info("🤖 3D Avatar: Switching to idle state")
        self.current_state = "idle"
        self.avatar_widget.set_state("idle")
    
    def show_thinking(self):
        """Show thinking state with 3D animation"""
        if self.closed:
            return
        
        logging.info("🤔 3D Avatar: Switching to thinking state")
        self.current_state = "thinking"
        self.avatar_widget.set_state("thinking")
    
    def show_processing(self):
        """Show processing state with 3D animation"""
        if self.closed:
            return
        
        logging.info("⚙️ 3D Avatar: Switching to processing state")
        self.current_state = "processing"
        self.avatar_widget.set_state("processing")
    
    def show_happy(self):
        """Show happy state with 3D animation"""
        if self.closed:
            return
        
        logging.info("😊 3D Avatar: Switching to happy state")
        self.current_state = "happy"
        self.avatar_widget.set_state("happy")
    
    def on_close(self):
        """Close the 3D avatar interface"""
        self.closed = True
        if hasattr(self, 'window'):
            self.window.close()
        try:
            if hasattr(self, 'app'):
                self.app.quit()
        except Exception:
            pass
