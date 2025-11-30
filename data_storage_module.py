import json
import csv
import os
import sqlite3
from datetime import datetime
import logging
import pickle
import cv2

class DataStorage:
    def __init__(self):
        self.logger = self.setup_logging()
        self.db_file = "security_system.db"
        self.events_file = "security_events.json"
        self.alerts_file = "alerts_log.csv"
        
        self.setup_database()
        self.setup_storage()
    
    def setup_logging(self):
        """Setup logging for data storage"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data_storage.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def setup_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    person_name TEXT,
                    confidence REAL,
                    camera_location TEXT,
                    additional_info TEXT
                )
            ''')
            
            # Create alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT,
                    description TEXT,
                    action_taken TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Create face logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS face_recognition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    recognized_name TEXT,
                    confidence REAL,
                    image_path TEXT,
                    camera_id INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("Database setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up database: {e}")
    
    def setup_storage(self):
        """Setup file-based storage"""
        try:
            # Create directories for storing evidence
            directories = ['evidence/images', 'evidence/videos', 'logs']
            for directory in directories:
                if not os.path.exists(directory):
                    os.makedirs(directory)
            
            # Initialize CSV file with headers if it doesn't exist
            if not os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(['Timestamp', 'Alert Type', 'Severity', 'Description', 'Location', 'Action Taken'])
            
            self.logger.info("File storage setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up file storage: {e}")
    
    def log_security_event(self, event_type, person_name=None, confidence=0, location="front_door", info=""):
        """Log security events to database and JSON"""
        try:
            timestamp = datetime.now().isoformat()
            
            # Database logging
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_events (timestamp, event_type, person_name, confidence, camera_location, additional_info)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (timestamp, event_type, person_name, confidence, location, info))
            
            conn.commit()
            conn.close()
            
            # JSON logging
            event_data = {
                'timestamp': timestamp,
                'event_type': event_type,
                'person_name': person_name,
                'confidence': confidence,
                'location': location,
                'additional_info': info
            }
            
            # Append to JSON file
            events = []
            if os.path.exists(self.events_file):
                with open(self.events_file, 'r') as f:
                    try:
                        events = json.load(f)
                    except json.JSONDecodeError:
                        events = []
            
            events.append(event_data)
            
            with open(self.events_file, 'w') as f:
                json.dump(events, f, indent=2)
            
            self.logger.info(f"Security event logged: {event_type} - {person_name}")
            
        except Exception as e:
            self.logger.error(f"Error logging security event: {e}")
    
    def log_alert(self, alert_type, severity, description, action_taken=""):
        """Log alerts to database and CSV"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Database logging
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts (timestamp, alert_type, severity, description, action_taken)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp, alert_type, severity, description, action_taken))
            
            conn.commit()
            conn.close()
            
            # CSV logging
            with open(self.alerts_file, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, alert_type, severity, description, "front_door", action_taken])
            
            self.logger.warning(f"Alert logged: {alert_type} - {severity} - {description}")
            
        except Exception as e:
            self.logger.error(f"Error logging alert: {e}")
    
    def save_evidence_image(self, frame, event_type, person_name="unknown"):
        """Save evidence images with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evidence/images/{event_type}_{person_name}_{timestamp}.jpg"
            
            # Create thumbnail
            thumbnail = cv2.resize(frame, (320, 240))
            
            cv2.imwrite(filename, frame)
            cv2.imwrite(filename.replace(".jpg", "_thumb.jpg"), thumbnail)
            
            # Log in database
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO face_recognition_logs (timestamp, recognized_name, confidence, image_path, camera_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), person_name, 0, filename, 1))
            
            conn.commit()
            conn.close()
            
            return filename
            
        except Exception as e:
            self.logger.error(f"Error saving evidence image: {e}")
            return None
    
    def get_recent_events(self, limit=10):
        """Retrieve recent security events"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM security_events 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            events = cursor.fetchall()
            conn.close()
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error retrieving events: {e}")
            return []
    
    def get_alerts_by_severity(self, severity):
        """Get alerts by severity level"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM alerts 
                WHERE severity = ? AND resolved = FALSE
                ORDER BY timestamp DESC
            ''', (severity,))
            
            alerts = cursor.fetchall()
            conn.close()
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error retrieving alerts: {e}")
            return []
    
    def export_data(self, start_date, end_date, export_format='json'):
        """Export data for specified date range"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM security_events 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            ''', (start_date, end_date))
            
            events = cursor.fetchall()
            conn.close()
            
            if export_format == 'json':
                export_file = f"export_events_{start_date}_{end_date}.json"
                with open(export_file, 'w') as f:
                    json.dump(events, f, indent=2)
            elif export_format == 'csv':
                export_file = f"export_events_{start_date}_{end_date}.csv"
                with open(export_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['ID', 'Timestamp', 'Event Type', 'Person', 'Confidence', 'Location', 'Info'])
                    writer.writerows(events)
            
            self.logger.info(f"Data exported to {export_file}")
            return export_file
            
        except Exception as e:
            self.logger.error(f"Error exporting data: {e}")
            return None