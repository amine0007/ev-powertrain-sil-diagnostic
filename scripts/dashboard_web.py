import sys
import time
import asyncio
import can
import cantools
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# Stockage de la télémétrie en mémoire
telemetry = {
    "voltage": 0.0,
    "current": 0.0,
    "temp": 0.0,
    "rpm": 0,
    "harm_amp": 0.0,
    "status": "NOMINAL",
    "history_time": [],
    "history_current": []
}

# Chargement de la base DBC et du bus CAN
try:
    db = cantools.database.load_file('config/vehicule.dbc')
    msg_battery = db.get_message_by_name('Battery_State')
    msg_motor = db.get_message_by_name('Motor_State')
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
except Exception as e:
    print(f"❌ Erreur connexion CAN : {e}")
    sys.exit(1)

def read_can():
    t0 = time.time()
    while True:
        msg = bus.recv(timeout=0.01)
        if msg:
            if msg.arbitration_id == 0x100:
                data = msg_battery.decode(msg.data)
                telemetry["voltage"] = round(data['Battery_Voltage'], 1)
                telemetry["current"] = round(data['Battery_Current'], 1)
                telemetry["temp"] = int(data['Battery_Temp'])

            elif msg.arbitration_id == 0x200:
                data = msg_motor.decode(msg.data)
                telemetry["harm_amp"] = round(data['Harmonic_Defect_Amp'], 2)
                telemetry["rpm"] = int(data['Motor_RPM'])
                i_rms = round(data['Phase_Current_RMS'], 1)

                # Diagnostic Status
                if telemetry["harm_amp"] > 5.0:
                    telemetry["status"] = "CRITICAL_FAULT"
                else:
                    telemetry["status"] = "NOMINAL"

                # Historique pour le graphique
                t_curr = round(time.time() - t0, 1)
                telemetry["history_time"].append(t_curr)
                telemetry["history_current"].append(i_rms)

                if len(telemetry["history_time"]) > 50:
                    telemetry["history_time"].pop(0)
                    telemetry["history_current"].pop(0)

@app.on_event("startup")
def startup_event():
    import threading
    threading.Thread(target=read_can, daemon=True).start()

@app.get("/api/data")
def get_data():
    return telemetry

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>HIL Telemetry Cockpit - Diagnostic VE</title>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            body { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 20px; }
            h1 { text-align: center; color: #38bdf8; margin-bottom: 20px; font-size: 24px; }
            .banner { text-align: center; padding: 15px; font-weight: bold; border-radius: 8px; font-size: 18px; margin-bottom: 20px; transition: all 0.3s; }
            .nominal { background-color: #065f46; color: #34d399; border: 1px solid #10b981; }
            .critical { background-color: #881337; color: #fda4af; border: 2px solid #f43f5e; animation: pulse 1s infinite; }
            .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
            .card { background-color: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155; text-align: center; }
            .card .title { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
            .card .value { font-size: 28px; font-weight: bold; color: #38bdf8; margin-top: 10px; }
            #chart { background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; padding: 10px; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
        </style>
    </head>
    <body>
        <h1>🚗 HIL TELEMETRY COCKPIT - VÉHICULE ÉLECTRIQUE</h1>
        <div id="banner" class="banner nominal">SYSTEM STATUS: NOMINAL</div>
        
        <div class="grid">
            <div class="card"><div class="title">Tension Batterie</div><div class="value" id="v_val">-- V</div></div>
            <div class="card"><div class="title">Courant Batterie</div><div class="value" id="i_val">-- A</div></div>
            <div class="card"><div class="title">Température Pack</div><div class="value" id="temp_val">-- °C</div></div>
            <div class="card"><div class="title">Défaut Harmonique (3H)</div><div class="value" id="harm_val" style="color: #f43f5e;">-- A</div></div>
        </div>

        <div id="chart"></div>

        <script>
            let trace = { x: [], y: [], type: 'scatter', mode: 'lines', line: { color: '#38bdf8', width: 3 } };
            let layout = {
                title: { text: 'Courant de Phase Moteur (A) - Temps Réel', font: { color: '#f8fafc' } },
                paper_bgcolor: '#1e293b', plot_bgcolor: '#1e293b',
                xaxis: { title: 'Temps (s)', color: '#94a3b8', gridcolor: '#334155' },
                yaxis: { title: 'Courant RMS (A)', color: '#94a3b8', gridcolor: '#334155' },
                margin: { t: 40, b: 40, l: 40, r: 20 }
            };
            Plotly.newPlot('chart', [trace], layout);

            async function updateDashboard() {
                try {
                    let res = await fetch('/api/data');
                    let data = await res.json();

                    document.getElementById('v_val').innerText = data.voltage + ' V';
                    document.getElementById('i_val').innerText = data.current + ' A';
                    document.getElementById('temp_val').innerText = data.temp + ' °C';
                    document.getElementById('harm_val').innerText = data.harm_amp + ' A';

                    let banner = document.getElementById('banner');
                    if (data.status === 'CRITICAL_FAULT') {
                        banner.innerText = '🚨 ALERTE CRITIQUE : HARMONIQUE ANORMALE DÉTECTÉE (DÉFAUT INVERTEUR)';
                        banner.className = 'banner critical';
                    } else {
                        banner.innerText = '🟢 SYSTEM STATUS: NOMINAL';
                        banner.className = 'banner nominal';
                    }

                    Plotly.react('chart', [{ x: data.history_time, y: data.history_current, type: 'scatter', mode: 'lines', line: { color: '#38bdf8', width: 3 } }], layout);
                } catch(e) {}
            }

            setInterval(updateDashboard, 100);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
