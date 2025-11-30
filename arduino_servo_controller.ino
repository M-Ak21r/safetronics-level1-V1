/*
 * arduino_servo_controller.ino
 * 
 * Arduino sketch for receiving servo angle commands from a PC via Serial
 * and controlling a pan servo for the safetronics security system.
 * 
 * Hardware connections:
 * - Servo signal wire -> Pin 9
 * - Servo power -> 5V (or external power for larger servos)
 * - Servo ground -> GND
 * 
 * Serial protocol:
 * - Receives integer values 0-180 as ASCII string followed by newline
 * - Example: "90\n" sets servo to 90 degrees (center position)
 */

#include <Servo.h>

// Pin definitions
const int SERVO_PIN = 9;

// Servo object
Servo panServo;

// Buffer for incoming serial data
const int BUFFER_SIZE = 8;
char inputBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// Current servo position
int currentAngle = 90;

// Timing for non-blocking operations
unsigned long lastUpdateTime = 0;
const unsigned long UPDATE_INTERVAL = 20; // milliseconds

void setup() {
    // Initialize serial communication at 9600 baud
    Serial.begin(9600);
    
    // Attach servo to pin
    panServo.attach(SERVO_PIN);
    
    // Set initial position to center
    panServo.write(currentAngle);
    
    // Clear input buffer
    memset(inputBuffer, 0, BUFFER_SIZE);
    
    // Send ready signal
    Serial.println("SERVO_READY");
}

void loop() {
    // Non-blocking serial read
    readSerial();
    
    // Non-blocking servo update (if needed for smooth movement)
    updateServo();
}

void readSerial() {
    // Check if data is available on serial port
    while (Serial.available() > 0) {
        char inChar = Serial.read();
        
        // Check for newline (end of command)
        if (inChar == '\n' || inChar == '\r') {
            if (bufferIndex > 0) {
                // Null-terminate the string
                inputBuffer[bufferIndex] = '\0';
                
                // Parse and process the command
                processCommand(inputBuffer);
                
                // Reset buffer
                bufferIndex = 0;
                memset(inputBuffer, 0, BUFFER_SIZE);
            }
        } else {
            // Add character to buffer if space available
            if (bufferIndex < BUFFER_SIZE - 1) {
                inputBuffer[bufferIndex] = inChar;
                bufferIndex++;
            }
        }
    }
}

void processCommand(const char* command) {
    // Parse integer value from command
    int angle = atoi(command);
    
    // Validate angle range (0-180 degrees)
    if (angle >= 0 && angle <= 180) {
        currentAngle = angle;
        
        // Immediately update servo position
        panServo.write(currentAngle);
        
        // Send acknowledgment
        Serial.print("ACK:");
        Serial.println(currentAngle);
    } else {
        // Invalid angle, send error
        Serial.println("ERR:INVALID_ANGLE");
    }
}

void updateServo() {
    // This function can be extended for smooth movement
    // Currently servo is updated immediately in processCommand
    
    unsigned long currentTime = millis();
    
    if (currentTime - lastUpdateTime >= UPDATE_INTERVAL) {
        lastUpdateTime = currentTime;
        
        // Additional servo processing can be added here
        // For example: smooth interpolation between angles
    }
}
