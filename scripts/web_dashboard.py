import streamlit as st
import can
import cantools
import pandas as pd
import time

st.set_page_config(page_title="Cockpit Diagnostic VE", layout="wide")
st.title("🚗 Cockpit Supervision & Diagnostic Véhicule Électrique")

# Chargement DBC & CAN
@st.cache_resource
def init_can():
    db = cantools.database.load_file('config/vehicule.dbc')
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    return db, bus

try:
    db, bus = init_can()
    msg_battery = db.get_message_by_name('Battery_State')
    msg_motor = db.get_message_by_name('Motor_State')
except Exception as e:
    st.error(f"Erreur de connexion CAN : {e}")
    st.stop()

# Placeholders pour la télémétrie
kpi_v, kpi_i, kpi_temp, kpi_harm = st.columns(4)
status_alert = st.empty()
chart_placeholder = st.empty()

history_time = []
history_current = []

t_start = time.time()

st.info("Écoute active du bus vcan0 en temps réel...")

while True:
    msg = bus.recv(timeout=0.05)
    if msg:
        if msg.arbitration_id == 0x100:
            data = msg_battery.decode(msg.data)
            kpi_v.metric("Tension Batterie", f"{data['Battery_Voltage']:.1f} V")
            kpi_i.metric("Courant Batterie", f"{data['Battery_Current']:.1f} A")
            kpi_temp.metric("Température", f"{data['Battery_Temp']} °C")

        elif msg.arbitration_id == 0x200:
            data = msg_motor.decode(msg.data)
            harm_amp = data['Harmonic_Defect_Amp']
            kpi_harm.metric("Défaut Harmonique (3H)", f"{harm_amp:.1f} A")

            # Status Alerte
            if harm_amp > 5.0:
                status_alert.error("🚨 ALERTE CRITIQUE : HARMONIQUE ANORMALE DÉTECTÉE SUR LE MOTEUR !")
            else:
                status_alert.success("🟢 SYSTEM STATUS: OK")

            # Graphique
            now = time.time() - t_start
            history_time.append(now)
            history_current.append(data['Phase_Current_RMS'])
            if len(history_time) > 50:
                history_time.pop(0)
                history_current.pop(0)

            df = pd.DataFrame({'Temps (s)': history_time, 'Courant RMS (A)': history_current})
            chart_placeholder.line_chart(df.set_index('Temps (s)'))

    time.sleep(0.05)
