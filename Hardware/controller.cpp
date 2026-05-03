#include <Wire.h>
#include <Adafruit_BMP085.h>
#include <AS5600.h>
#include <MPU6050.h>
#include <Servo.h>
#include <math.h>


/************* TDS SENSOR MODULE*************/

#define TDS_PIN A0

// ---------- INIT FUNCTION ----------
void initTDS() {
  pinMode(TDS_PIN, INPUT);
}

// ---------- READ FUNCTION ----------
float readTDS() {

  int analogValue = analogRead(TDS_PIN);

  float voltage = analogValue * (5.0 / 1023.0);

  float tds = (133.42 * voltage * voltage * voltage
              - 255.86 * voltage * voltage
              + 857.39 * voltage) * 0.5;

  // remove tiny noise
  if (tds < 10) tds = 0;

  return tds;
}


/************* PH SENSOR MODULE *************/

#define PH_PIN A2
#define PH_SAMPLES 10

float phVoltage = 0;
float phValue = 0;

// ---------- INIT FUNCTION ----------
void initPH() {
  pinMode(PH_PIN, INPUT);
}

// ---------- READ FUNCTION ----------
float readPH() {

  int buffer[PH_SAMPLES];

  // take multiple readings
  for (int i = 0; i < PH_SAMPLES; i++) {
    buffer[i] = analogRead(PH_PIN);
    delay(10);  // small delay for stability
  }

  // sort values (for median filtering)
  for (int i = 0; i < PH_SAMPLES - 1; i++) {
    for (int j = i + 1; j < PH_SAMPLES; j++) {
      if (buffer[i] > buffer[j]) {
        int temp = buffer[i];
        buffer[i] = buffer[j];
        buffer[j] = temp;
      }
    }
  }

  // take median value
  int medianValue = buffer[PH_SAMPLES / 2];

  // convert to voltage
  phVoltage = medianValue * (5.0 / 1023.0);

  // convert to pH (approximate formula)
  phValue = 7 + ((2.5 - phVoltage) / 0.18);

  return phValue;
}

/************* BMP180 SENSOR MODULE *************/

#include <Wire.h>
#include <Adafruit_BMP085.h>

Adafruit_BMP085 bmp;

// ---------- INIT FUNCTION ----------
void initBMP() {
  if (!bmp.begin(0x77)) {
    Serial.println("BMP180 init failed!");
  }
}

// ---------- READ PRESSURE ----------
float readPressure() {
  return bmp.readPressure();   // returns in Pascals (Pa)
}

// ---------- READ TEMPERATURE ----------
float readBMPTemperature() {
  return bmp.readTemperature();  // returns in °C
}

// ---------- READ ALTITUDE (OPTIONAL) ----------
float readAltitude() {
  return bmp.readAltitude();   // meters
}

/************* STATUS LED MODULE *************/

#define LED_PIN 13

unsigned long ledPreviousMillis = 0;
const long ledInterval = 500;  // blink every 500ms
bool ledState = false;

// ---------- INIT FUNCTION ----------
void initLED() {
  pinMode(LED_PIN, OUTPUT);
}

// ---------- UPDATE FUNCTION ----------
void updateLED() {
  unsigned long currentMillis = millis();

  if (currentMillis - ledPreviousMillis >= ledInterval) {
    ledPreviousMillis = currentMillis;

    ledState = !ledState;
    digitalWrite(LED_PIN, ledState);
  }
}

/************* ANEMOMETER MODULE (AS5600) *************/

#include <Wire.h>
#include <AS5600.h>

AS5600 as5600;

// internal state
float anemoPrevAngle = 0;
unsigned long anemoPrevTime = 0;
float anemoRPMFiltered = 0;

// ---------- INIT FUNCTION ----------
void initAnemometer() {
  Wire.begin();
  anemoPrevTime = millis();
}

// ---------- READ FUNCTION ----------
float readFlowRate() {

  unsigned long currentTime = millis();

  float rawAngle = as5600.readAngle();
  float angle = rawAngle * 360.0 / 4096.0;

  float deltaAngle = angle - anemoPrevAngle;

  // wrap-around handling
  if (deltaAngle < -180) deltaAngle += 360;
  if (deltaAngle > 180) deltaAngle -= 360;

  unsigned long deltaTime = currentTime - anemoPrevTime;

  float rpm = 0;

  if (deltaTime > 50) {
    rpm = (deltaAngle / 360.0) * (60000.0 / deltaTime);

    rpm = abs(rpm);

    // noise filter
    if (rpm < 1) rpm = 0;

    // smoothing (exponential)
    anemoRPMFiltered = (anemoRPMFiltered * 0.7) + (rpm * 0.3);

    anemoPrevAngle = angle;
    anemoPrevTime = currentTime;
  }

  return anemoRPMFiltered;
}


/************* MPU6050 VIBRATION MODULE *************/

// object (keep this!)
MPU6050 mpu;

// internal state
float vibrationFiltered = 0;

// ---------- INIT FUNCTION ----------
void initMPU() {
  mpu.initialize();

  if (!mpu.testConnection()) {
    Serial.println("MPU6050 init failed!");
  }
}

// ---------- READ FUNCTION ----------
float readVibration() {

  int16_t ax, ay, az;
  mpu.getAcceleration(&ax, &ay, &az);

  float vibration = sqrt((float)ax * ax + (float)ay * ay + (float)az * az);

  vibration = vibration / 16384.0;  
  vibration = abs(vibration - 1.0);

  if (vibration < 0.02) vibration = 0;

  vibrationFiltered = (vibrationFiltered * 0.7) + (vibration * 0.3);

  return vibrationFiltered;
}


/************* SERVO VALVE MODULE *************/

// object (keep this!)
Servo valveServo;

#define SERVO_PIN 10

int servoNeutral = 90;

// tuning values
int quatDelay = 300;
int halfDelay = 600;
int fullDelay = 600;

// ---------- INIT FUNCTION ----------
void initServo() {
  valveServo.attach(SERVO_PIN);
  valveServo.write(servoNeutral);
}

// ---------- COMMAND FUNCTION ----------
void controlValve(String cmd) {

  cmd.trim();

  if (cmd == "FULL") {
    Serial.println("Valve: FULL CLOSED");

    valveServo.write(servoNeutral - 20);
    delay(fullDelay);
    valveServo.write(servoNeutral);
  }

  else if (cmd == "QUAT") {
    Serial.println("Valve: 25% OPEN");

    valveServo.write(servoNeutral + 10);
    delay(quatDelay);
    valveServo.write(servoNeutral);
  }

  else if (cmd == "HALF") {
    Serial.println("Valve: 50% OPEN");

    valveServo.write(servoNeutral + 25);
    delay(halfDelay);
    valveServo.write(servoNeutral);
  }
}

/************* SETUP *************/
void setup() {
  Serial.begin(9600);
  Wire.begin();

  initTDS();
  initPH();
  initBMP();
  initLED();
  initAnemometer();
  initMPU();
  initServo();

  Serial.println("SYSTEM INITIALIZED");
}

/************* LOOP *************/
void loop() {

  // 🔹 LED heartbeat
  updateLED();

  // 🔹 Read sensors
  float flow = readFlowRate();
  float pressure = readPressure();
  float temperature = readBMPTemperature();
  float tds = readTDS();
  float ph = readPH();
  float vibration = readVibration();

  // 🔹 SERIAL OUTPUT (HUMAN READABLE)
  Serial.print(flow); Serial.print(",");
  Serial.print(pressure); Serial.print(",");
  Serial.print(temperature); Serial.print(",");
  Serial.print(tds); Serial.print(",");
  Serial.print(ph); Serial.print(",");
  Serial.println(vibration);
  // 🔹 SERIAL COMMAND CONTROL (for Python later)
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    controlValve(cmd);
  }

  delay(100);
}
