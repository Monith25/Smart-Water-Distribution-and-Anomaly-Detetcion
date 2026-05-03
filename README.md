# Smart Water Distribution and Anomaly Detection

An intelligent multi-zone water management system for **real-time monitoring, anomaly detection, and dynamic redistribution** with explainable decision-making.

---

## Overview

This project focuses on building a **smart water pipeline system** that:

- Monitors multiple zones in real time  
- Detects anomalies using machine learning + system logic  
- Automatically controls valves  
- Redistributes water intelligently across zones  
- Provides clear justification for every decision  

Unlike traditional systems, this solution emphasizes **explainability and system-level awareness**, not just detection.

---

## System Architecture

The system is designed around a **multi-zone model (Zone A, B, C)**:

Each zone monitors:
- Flow rate  
- Pressure & temperature  
- Water quality (TDS, pH)  
- Vibration (pipeline/valve health)  

Zone A uses **real sensor data**, while Zones B & C simulate dynamic real-world conditions.

---

## Data Pipeline

- Serial data acquisition using **PySerial**  
- Backend processing using **Flask (Python)**  
- Data structured into **zone-wise dictionaries**  
- REST API endpoints for frontend consumption  

---

## Detection & Control

### Machine Learning
- **Random Forest Classifier**
- Trained on synthetic dataset
- Predicts valve actions:
  - `FULL` (close valve)
  - `HALF`
  - `QUAT`

### Rule + ML Hybrid Logic
- Flow–pressure inconsistency detection  
- Zero-flow with pressure → blockage detection  
- Vibration spikes → structural issues  
- pH/TDS deviation → contamination detection  

### Actuation
- Commands sent to Arduino
- State-based control (avoids redundant commands)

---

## Dynamic Redistribution (Core Feature)

When a zone fails:

- System evaluates the **remaining zones**
- Scores them based on:
  - Flow capacity  
  - Pressure stability  
  - Vibration  
  - Water quality  

- Selects the **best donor zone**
- Provides:
  - ✔ Action (what to do)
  - ✔ Justification (why this zone)
  - ✔ Comparison (why not the other zone)

## Frontend Dashboard

Built using **HTML, CSS, JavaScript**

Features:
- Live sensor data per zone  
- Time-based graphs (Live / 1 min / 5 min)  
- Multi-zone support (A, B, C)  
- Dedicated anomaly detection page  
- Real-time alerts with action + justification  

---

## Tech Stack

- **Python (Flask)**
- **PySerial**
- **Scikit-learn (Random Forest)**
- **Arduino (Sensor + Servo Control)**
- **HTML / CSS / JavaScript**
- **Chart.js**

---

## Example Scenario

> Zone A detects zero flow with pressure → blockage suspected  

System response:
- Evaluates Zone B & C  
- Selects best donor (e.g., Zone C)  
- Rejects weaker zone (e.g., Zone B due to vibration)  

Output:
