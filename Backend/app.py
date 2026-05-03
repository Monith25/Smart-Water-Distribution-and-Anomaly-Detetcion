from flask import Flask, render_template, jsonify, request
import serial
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import random


df = pd.read_csv("synthetic_water_data.csv")
def label_action(row):
    if row["tds"] > 500 or row["vibration"] > 0.1:
        return "FULL"
    elif row["flow"] < 5:
        return "HALF"
    elif row["flow"] < 50:
        return "QUAT"
    else:
        return "QUAT"

df["action"] = df.apply(label_action, axis=1)

# features
X = df[["flow", "pressure", "tds", "vibration"]]

# labels (must exist in CSV)
y = df["action"]   # FULL / HALF / QUAT

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y)

print("✅ RandomForest Model Loaded")

current_state = "FULL"
app = Flask(__name__)

# 🔥 OPEN SERIAL ONLY ONCE
try:
    ser = serial.Serial('COM11', 9600, timeout=1)
    print("✅ Connected to COM11")
except Exception as e:
    print("❌ Serial connection failed:", e)
    ser = None

latest_data = {
    "flow": 0,
    "pressure": 0,
    "temp": 0,
    "tds": 0,
    "ph": 0,
    "vibration": 0
}

zone_data = {
    "A": latest_data,
    "B": {"flow": 20, "pressure": 91320, "temp": 30, "tds": 50, "ph": 7, "vibration": 0.02},
    "C": {"flow": 35, "pressure": 91310, "temp": 32, "tds": 60, "ph": 7.2, "vibration": 0.03}
}
def update_fake_zones():
    # Zone B
    zone_data["B"]["flow"] += random.uniform(-2, 2)
    zone_data["B"]["pressure"] += random.uniform(-5, 5)
    zone_data["B"]["tds"] += random.uniform(-2, 2)
    zone_data["B"]["vibration"] += random.uniform(-0.01, 0.01)

    # Zone C
    zone_data["C"]["flow"] += random.uniform(-3, 3)
    zone_data["C"]["pressure"] += random.uniform(-6, 6)
    zone_data["C"]["tds"] += random.uniform(-3, 3)
    zone_data["C"]["vibration"] += random.uniform(-0.01, 0.01)

    # clamp values (important)
    for z in ["B", "C"]:
        zone_data[z]["flow"] = max(0, zone_data[z]["flow"])
        zone_data[z]["pressure"] = max(91000, zone_data[z]["pressure"])
        zone_data[z]["tds"] = max(0, zone_data[z]["tds"])
        zone_data[z]["vibration"] = max(0, zone_data[z]["vibration"])
def run_model(data):
    sample = pd.DataFrame([[
        data["flow"],
        data["pressure"],
        data["tds"],
        data["vibration"]
    ]], columns=["flow", "pressure", "tds", "vibration"])

    prediction = model.predict(sample)[0]

    print("🤖 ML Decision:", prediction)

    return prediction  # FULL / HALF / QUAT

# READ SERIAL PROPERLY
def read_serial():
    global latest_data
    if ser is None:
        return
    try:
        line = ""

        # keep reading till we get latest line (DO NOT CHANGE THIS)
        while ser.in_waiting:
            line = ser.readline().decode(errors='ignore').strip()

        if not line:
            return

        print("FINAL RAW:", line)

        parts = line.split(",")

        if len(parts) >= 6:
            latest_data = {
                "flow": float(parts[0]),
                "pressure": float(parts[1]),
                "temp": float(parts[2]),
                "tds": float(parts[3]),
                "ph": float(parts[4]),
                "vibration": float(parts[5])
            }

            print("✅ UPDATED:", latest_data)
            global current_state
            cmd = run_model(latest_data)
            if cmd not in ["FULL", "HALF", "QUAT"]:
                print("⚠️ Invalid ML output:", cmd)
                return
            if cmd is not None and cmd != current_state:
                try:
                    ser.write((cmd + "\n").encode())
                    print("📡 SENT:", cmd)
                    current_state = cmd
                except:
                    print("❌ Failed to send command")
        else:
            print("❌ BAD DATA:", parts)

    except Exception as e:
        print("Error:", e)

# ===== ROUTES =====
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/zoneA")
def zoneA():
    return render_template("zoneA.html")

@app.route("/zoneB")
def zoneB():
    return render_template("zoneB.html")

@app.route("/zoneC")
def zoneC():
    return render_template("zoneC.html")


@app.route("/data")
def data():
    read_serial()
    update_fake_zones()   # 🔥 ADD THIS

    zone_data["A"] = latest_data

    return jsonify(zone_data)
@app.route("/anomaly")
def anomaly():
    read_serial()
    return render_template("anamoly.html")

@app.route("/anomaly_data")
def anomaly_data():
    read_serial()
    update_fake_zones()

    zone = request.args.get("zone", "A")
    anomalies = []

    d = zone_data[zone]    # we analyze Zone A

    # ===== SMART SCORING FUNCTION =====
    def score(z):
        return (
            z["flow"] * 3
            + (z["pressure"] - 91200) * 0.1
            - z["vibration"] * 300
            - z["tds"] * 0.2
        )

    # ===== PICK OTHER ZONES BASED ON SELECTED =====
    zones = ["A", "B", "C"]
    zones.remove(zone)  # remove selected zone

    z1, z2 = zones  # the two candidates

    data1 = zone_data[z1]
    data2 = zone_data[z2]

    score1 = score(data1)
    score2 = score(data2)

    if score1 > score2:
        donor = z1
        other = z2
        donor_data = data1
        other_data = data2
    else:
        donor = z2
        other = z1
        donor_data = data2
        other_data = data1

    print(f"Comparing {z1} vs {z2} → Selected:", donor)
    # ===== ANOMALIES =====

    # Low Pressure
    if d["pressure"] < 91300:
        anomalies.append({
            "type": "Low Pressure",
            "message": f"Pressure too low: {d['pressure']}",
            "level": "medium",
            "action": f"Increase supply from Zone {donor}",
            "justification": (
                f"Zone {donor} selected (flow={donor_data['flow']:.2f}, "
                f"vibration={donor_data['vibration']:.3f}). "
                f"Zone {other} avoided (flow={other_data['flow']:.2f}, "
                f"vibration={other_data['vibration']:.3f})."
            )
        })

    # High Pressure
    elif d["pressure"] > 91350:
        anomalies.append({
            "type": "High Pressure",
            "message": f"Pressure too high: {d['pressure']}",
            "level": "high",
            "action": f"Divert excess water to Zone {donor}",
            "justification": (
                f"Zone {donor} selected due to better stability. "
                f"Zone {other} avoided due to comparatively lower performance."
            )
        })

    # No Flow
    if d["flow"] <= 0.1:
        anomalies.append({
            "type": "No Water Flow",
            "message": f"Flow is zero or very low: {d['flow']}",
            "level": "high",
            "action": f"Supply water from Zone {donor} and open valve",
            "justification": (
                f"Zone {donor} selected (flow={donor_data['flow']:.2f}, "
                f"vibration={donor_data['vibration']:.3f}). "
                f"Zone {other} avoided (flow={other_data['flow']:.2f}, "
                f"vibration={other_data['vibration']:.3f})."
            )
        })

    # Blockage
    if d["flow"] <= 0.1 and d["pressure"] > 91250:
        anomalies.append({
            "type": "Possible Blockage",
            "message": "Pressure present but no flow",
            "level": "high",
            "action": f"Reroute from Zone {donor} and inspect pipeline",
            "justification": (
                f"Zone {donor} ensures continuity while inspection is performed. "
                f"Zone {other} avoided due to lower reliability."
            )
        })

    # Temperature
    if d["temp"] > 45:
        anomalies.append({
            "type": "High Temperature",
            "message": f"Temp spike: {d['temp']} °C",
            "level": "medium",
            "action": f"Increase circulation using Zone {donor}",
            "justification": (
                f"Zone {donor} provides better cooling potential. "
                f"Zone {other} avoided due to less favorable conditions."
            )
        })

    # pH
    if d["ph"] > 13 or d["ph"] < 6:
        anomalies.append({
            "type": "pH Imbalance",
            "message": f"pH abnormal: {d['ph']}",
            "level": "high",
            "action": f"Isolate Zone A and supply clean water from Zone {donor}",
            "justification": (
                f"Zone {donor} has safer conditions. "
                f"Zone {other} avoided due to poorer water quality indicators."
            )
        })

    # Vibration
    if d["vibration"] > 0.7:
        anomalies.append({
            "type": "Pipe Vibration",
            "message": f"High vibration: {d['vibration']}",
            "level": "high",
            "action": f"Shift load to Zone {donor}",
            "justification": (
                f"Zone {donor} is more stable. "
                f"Zone {other} avoided due to higher structural risk."
            )
        })

    return jsonify(anomalies)

# ===== RUN =====
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
