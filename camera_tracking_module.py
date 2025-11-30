import cv2
import time
import numpy as np
from datetime import datetime, timedelta
import logging
import threading
import json

# Import the other modules
from face_recognition_module import FaceRecognition
from data_storage_module import DataStorage

class CameraTrackingSystem:
    def __init__(self):
        self.logger = self.setup_logging()
        
        # Initialize modules
        self.face_recognition = FaceRecognition()
        self.data_storage = DataStorage()
        
        # Camera settings
        self.camera_index = 0
        self.frame_width = 640
        self.frame_height = 480
        self.fps = 20
        
        # System states
        self.system_active = False
        self.door_unlocked = False
        self.tracking_unknown = False
        self.suspicious_activity_detected = False
        
        # Tracking variables
        self.unknown_person_detected_time = None
        self.owner_detected_time = None
        self.last_alert_time = None
        
        # Servo control simulation (replace with actual GPIO)
        self.servo1_position = 0  # 0=locked, 90=unlocked
        self.servo2_position = 90  # 90=center
        
        # Motion detection
        self.previous_frame = None
        self.motion_threshold = 1000
        
        # Alert cooldown (prevent spam)
        self.alert_cooldown = 60  # seconds
        
        self.logger.info("Camera Tracking System initialized")
    
    def setup_logging(self):
        """Setup logging for camera tracking"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('camera_tracking.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def initialize_camera(self):
        """Initialize camera with error handling"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                self.logger.error(f"Cannot open camera {self.camera_index}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Test camera
            ret, test_frame = self.cap.read()
            if not ret:
                self.logger.error("Cannot read from camera")
                return False
            
            self.logger.info("Camera initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            return False
    
    def control_servo1(self, unlock=True):
        """Control door lock servo"""
        try:
            angle = 90 if unlock else 0
            self.servo1_position = angle
            
            # Simulate servo movement (replace with actual GPIO code)
            if unlock:
                self.logger.info("🚪 DOOR UNLOCKED - Servo 1 rotated 90°")
                self.data_storage.log_security_event(
                    "DOOR_UNLOCKED", 
                    "owner", 
                    100, 
                    "front_door",
                    "Door unlocked via face recognition"
                )
            else:
                self.logger.info("🚪 DOOR LOCKED - Servo 1 rotated 0°")
                self.data_storage.log_security_event(
                    "DOOR_LOCKED", 
                    "system", 
                    100, 
                    "front_door",
                    "Door locked by system"
                )
            
            self.door_unlocked = unlock
            return True
            
        except Exception as e:
            self.logger.error(f"Error controlling servo 1: {e}")
            return False
    
    def control_servo2(self, direction):
        """Control tracking servo based on movement direction"""
        try:
            angles = {
                "left": 45,
                "right": 135,
                "up": 70,
                "down": 110,
                "center": 90
            }
            
            angle = angles.get(direction, 90)
            self.servo2_position = angle
            
            self.logger.info(f"🎯 Tracking servo moved {direction} to {angle}°")
            
            # Log tracking activity
            self.data_storage.log_security_event(
                "TRACKING_MOVEMENT",
                "unknown",
                0,
                "front_door",
                f"Tracking servo moved {direction} to follow unknown person"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error controlling servo 2: {e}")
            return False
    
    def detect_suspicious_activity(self, frame):
        """Detect suspicious activities using motion analysis"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            if self.previous_frame is None:
                self.previous_frame = gray
                return False
            
            # Compute difference between frames
            frame_diff = cv2.absdiff(self.previous_frame, gray)
            _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
            
            # Dilate to fill holes
            thresh = cv2.dilate(thresh, None, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            suspicious_motion = False
            motion_areas = []
            
            for contour in contours:
                if cv2.contourArea(contour) > 1000:  # Significant movement
                    (x, y, w, h) = cv2.boundingRect(contour)
                    motion_areas.append((x, y, w, h))
                    suspicious_motion = True
            
            self.previous_frame = gray
            
            # Check if we should trigger alert
            if suspicious_motion and not self.door_unlocked:
                current_time = time.time()
                
                # Check alert cooldown
                if self.last_alert_time is None or (current_time - self.last_alert_time) > self.alert_cooldown:
                    self.trigger_security_alert("SUSPICIOUS_MOTION", motion_areas)
                    self.last_alert_time = current_time
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in suspicious activity detection: {e}")
            return False
    
    def trigger_security_alert(self, alert_type, details=None):
        """Trigger security alerts and notifications"""
        try:
            self.logger.warning(f"🚨 SECURITY ALERT: {alert_type}")
            
            # Determine severity and description
            if alert_type == "SUSPICIOUS_MOTION":
                severity = "HIGH"
                description = "Suspicious movement detected near entrance"
                action_taken = "GSM alerts sent, relay activated"
            elif alert_type == "INTRUDER_DETECTED":
                severity = "CRITICAL"
                description = "Unknown person attempting access"
                action_taken = "Tracking activated, alerts sent"
            else:
                severity = "MEDIUM"
                description = f"Security event: {alert_type}"
                action_taken = "System monitoring"
            
            # Log alert
            self.data_storage.log_alert(alert_type, severity, description, action_taken)
            
            # Simulate GSM alert (replace with actual GSM code)
            self.send_gsm_alert(alert_type, description)
            
            # Simulate relay activation (replace with actual GPIO code)
            self.activate_security_relay()
            
            self.suspicious_activity_detected = True
            
        except Exception as e:
            self.logger.error(f"Error triggering security alert: {e}")
    
    def send_gsm_alert(self, alert_type, description):
        """Simulate sending GSM alerts"""
        try:
            # Simulate sending SMS (replace with actual GSM module code)
            police_message = f"SECURITY ALERT: {alert_type} - {description} - Location: Your Address"
            owner_message = f"HOME SECURITY: {alert_type} - {description}"
            
            self.logger.info(f"📱 SMS to POLICE: {police_message}")
            self.logger.info(f"📱 SMS to OWNER: {owner_message}")
            
            # Log the alert
            self.data_storage.log_security_event(
                "GSM_ALERT_SENT",
                "system",
                100,
                "front_door",
                f"Alerts sent for: {alert_type}"
            )
            
        except Exception as e:
            self.logger.error(f"Error sending GSM alert: {e}")
    
    def activate_security_relay(self):
        """Activate security relay"""
        try:
            # Simulate relay activation (replace with actual GPIO code)
            self.logger.info("🔒 SECURITY RELAY ACTIVATED - Additional security measures enabled")
            
            self.data_storage.log_security_event(
                "RELAY_ACTIVATED",
                "system",
                100,
                "front_door",
                "Security relay activated for enhanced protection"
            )
            
        except Exception as e:
            self.logger.error(f"Error activating relay: {e}")
    
    def track_unknown_person(self, frame, face_bbox):
        """Track unknown person and adjust camera/servo"""
        try:
            x, y, w, h = face_bbox
            frame_h, frame_w = frame.shape[:2]
            
            # Calculate face center
            face_center_x = x + w/2
            face_center_y = y + h/2
            
            # Determine if person is moving out of frame
            if face_center_x < frame_w * 0.2:
                direction = "right"
            elif face_center_x > frame_w * 0.8:
                direction = "left"
            elif face_center_y < frame_h * 0.2:
                direction = "down"
            elif face_center_y > frame_h * 0.8:
                direction = "up"
            else:
                direction = "center"
            
            # Only move servo if person is near edge
            if direction != "center":
                self.control_servo2(direction)
            
            # Draw tracking info
            cv2.putText(frame, f"TRACKING: {direction.upper()}", 
                       (10, frame_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            return direction
            
        except Exception as e:
            self.logger.error(f"Error in person tracking: {e}")
            return "center"
    
    def run_security_system(self):
        """Main security system loop"""
        try:
            if not self.initialize_camera():
                return
            
            self.system_active = True
            self.logger.info("Security System STARTED - Press 'q' to quit, 't' to train, 'l' to lock door")
            
            while self.system_active:
                ret, frame = self.cap.read()
                if not ret:
                    self.logger.error("Can't receive frame from camera")
                    break
                
                # Flip frame horizontally for mirror effect
                frame = cv2.flip(frame, 1)
                
                # Face recognition
                processed_frame, owner_detected, face_results, confidence = self.face_recognition.recognize_face(frame)
                
                # Handle owner detection
                if owner_detected and not self.door_unlocked:
                    self.control_servo1(unlock=True)
                    self.owner_detected_time = time.time()
                    self.data_storage.save_evidence_image(frame, "owner_detected", "owner")
                
                # Handle unknown persons
                unknown_faces = [face for face in face_results if "UNKNOWN" in face['name']]
                if unknown_faces and not owner_detected:
                    if not self.tracking_unknown:
                        self.unknown_person_detected_time = time.time()
                        self.tracking_unknown = True
                        self.logger.warning("Unknown person detected - starting tracking")
                        
                        # Trigger intruder alert
                        self.trigger_security_alert("INTRUDER_DETECTED")
                    
                    # Track the first unknown face
                    self.track_unknown_person(processed_frame, unknown_faces[0]['bbox'])
                    
                    # Save evidence
                    self.data_storage.save_evidence_image(frame, "intruder_detected", "unknown")
                
                # Reset tracking if no unknown faces for a while
                elif self.tracking_unknown and not unknown_faces:
                    if time.time() - self.unknown_person_detected_time > 5:  # 5 seconds no detection
                        self.tracking_unknown = False
                        self.control_servo2("center")  # Reset tracking servo
                
                # Detect suspicious activity
                suspicious_detected = self.detect_suspicious_activity(frame)
                if suspicious_detected:
                    cv2.putText(processed_frame, "SUSPICIOUS ACTIVITY DETECTED!", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Auto-lock door after 10 seconds if no owner present
                if self.door_unlocked and not owner_detected:
                    if time.time() - self.owner_detected_time > 10:
                        self.control_servo1(unlock=False)
                
                # Display system status
                status_text = f"Door: {'UNLOCKED' if self.door_unlocked else 'LOCKED'} | " \
                            f"Tracking: {'ON' if self.tracking_unknown else 'OFF'} | " \
                            f"Alerts: {'ACTIVE' if self.suspicious_activity_detected else 'NORMAL'}"
                
                cv2.putText(processed_frame, status_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Display controls help
                help_text = "Controls: Q=Quit, T=Train, L=Lock, S=Status"
                cv2.putText(processed_frame, help_text, (10, processed_frame.shape[0] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # Show frame
                cv2.imshow('Security System - Camera Tracking', processed_frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('t'):
                    self.train_new_face()
                elif key == ord('l'):
                    self.control_servo1(unlock=False)
                elif key == ord('s'):
                    self.show_system_status()
            
            # Cleanup
            self.cleanup()
            
        except Exception as e:
            self.logger.error(f"Error in main security loop: {e}")
            self.cleanup()
    
    def train_new_face(self):
        """Train new face in a separate thread"""
        def train_thread():
            self.face_recognition.train_new_face("owner")
        
        thread = threading.Thread(target=train_thread)
        thread.daemon = True
        thread.start()
        self.logger.info("Face training started in background...")
    
    def show_system_status(self):
        """Display current system status"""
        status = {
            "System Active": self.system_active,
            "Door Locked": not self.door_unlocked,
            "Tracking Unknown": self.tracking_unknown,
            "Suspicious Activity": self.suspicious_activity_detected,
            "Known Faces": self.face_recognition.get_known_faces(),
            "Servo 1 Position": self.servo1_position,
            "Servo 2 Position": self.servo2_position
        }
        
        self.logger.info("=== SYSTEM STATUS ===")
        for key, value in status.items():
            self.logger.info(f"{key}: {value}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.system_active = False
            
            if hasattr(self, 'cap'):
                self.cap.release()
            
            cv2.destroyAllWindows()
            
            # Ensure door is locked on exit
            if self.door_unlocked:
                self.control_servo1(unlock=False)
            
            self.logger.info("Security System stopped and cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

# Main execution
if __name__ == "__main__":
    security_system = CameraTrackingSystem()
    security_system.run_security_system()