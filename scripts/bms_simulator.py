import time
import math
import can
import cantools

# 1. Charger le fichier DBC
db = cantools.database.load_file('config/vehicule.dbc')
msg_battery = db.get_message_by_name('Battery_State')
msg_motor = db.get_message_by_name('Motor_State')

# 2. Connexion au bus CAN vcan0
try:
    bus = can.interface.Bus(channel='vcan0', interface='socketcan')
    print("✅ Connecté au bus vcan0")
except Exception as e:
    print(f"❌ Erreur bus CAN : {e}")
    exit(1)

print("🚀 Simulation Véhicule & Moteur démarrée (Injection de défaut à t = 10s)...")

t = 0.0
dt = 0.05  # Échantillonnage à 20 Hz (toutes les 50 ms)

try:
    while True:
        # --- 1. Génération données Batterie ---
        i_bat = 40.0 * math.sin(0.5 * t)
        v_bat = 380.0 - (0.05 * i_bat)
        temp_bat = 25.0 + (t * 0.1)

        data_bat = msg_battery.encode({
            'Battery_Voltage': v_bat,
            'Battery_Current': i_bat,
            'Battery_Temp': int(temp_bat)
        })
        bus.send(can.Message(arbitration_id=msg_battery.frame_id, data=data_bat, is_extended_id=False))

        # --- 2. Génération données Moteur avec injection de défaut ---
        rpm = 3000 + int(500 * math.sin(0.2 * t))
        f_fondamentale = 50.0  # 50 Hz
        i_phase_rms = 100.0 + 10.0 * math.sin(0.1 * t)
        
        # Injection de défaut : Après 10 secondes, une harmonique à 150 Hz apparaît !
        harmonic_fault = 0.0
        if t > 10.0:
            harmonic_fault = 12.5  # Amplitute du défaut en Ampères (seuil d'alerte > 5.0A)

        data_motor = msg_motor.encode({
            'Phase_Current_RMS': i_phase_rms,
            'Harmonic_Defect_Amp': harmonic_fault,
            'Motor_RPM': rpm
        })
        bus.send(can.Message(arbitration_id=msg_motor.frame_id, data=data_motor, is_extended_id=False))

        fault_status = "🔴 INJECTION DÉFAUT HARMONIQUE" if t > 10.0 else "🟢 REGIME NORMAL"
        print(f"[{t:.1f}s] RPM: {rpm} | I_rms: {i_phase_rms:.1f}A | Defaut 3h: {harmonic_fault:.1f}A | {fault_status}", end='\r')

        time.sleep(dt)
        t += dt

except KeyboardInterrupt:
    print("\n🛑 Simulation arrêtée.")
