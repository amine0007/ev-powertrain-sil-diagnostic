import sys
import os

# Configuration pour compatibilité WSLg / Windows 11 (rendu fluide sans bug OpenGL)
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

import can
import cantools
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QLabel, QFrame, QGridLayout
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
import pyqtgraph as pg

# Désactiver OpenGL natif pour éviter les écrans blancs sous WSLg
pg.setConfigOptions(useOpenGL=False)

class MetricCard(QFrame):
    """Carte de métrique style Cockpit Automobile"""
    def __init__(self, title, unit, color="#00fff5"):
        super().__init__()
        self.unit = unit
        self.setMinimumHeight(100)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1b1b2f;
                border: 2px solid #1f4068;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout()
        
        self.title_label = QLabel(title.upper())
        self.title_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #a6a6a4; border: none;")
        
        self.value_label = QLabel(f"-- {unit}")
        self.value_label.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
        self.value_label.setStyleSheet(f"color: {color}; border: none;")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        self.setLayout(layout)

    def set_value(self, val):
        if isinstance(val, float):
            self.value_label.setText(f"{val:.1f} {self.unit}")
        else:
            self.value_label.setText(f"{val} {self.unit}")


class ECU_Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HIL TELEMETRY COCKPIT - DIAGNOSTIC VE")
        self.resize(1100, 650)
        self.setStyleSheet("background-color: #121212;")

        # Base de données CAN & Interface vcan0
        try:
            self.db = cantools.database.load_file('config/vehicule.dbc')
            self.msg_battery = self.db.get_message_by_name('Battery_State')
            self.msg_motor = self.db.get_message_by_name('Motor_State')
            self.bus = can.interface.Bus(channel='vcan0', interface='socketcan')
        except Exception as e:
            print(f"❌ Erreur d'initialisation CAN : {e}")
            sys.exit(1)

        self.time_data = []
        self.current_data = []
        self.time_counter = 0.0

        self.init_ui()

        # Timer de rafraîchissement IHM (25 Hz)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_can_data)
        self.timer.start(40)

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # --- 1. Banner Status ---
        self.status_banner = QLabel("SYSTEM STATUS: NOMINAL")
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_banner.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        self.status_banner.setStyleSheet("""
            background-color: #0f5257; 
            color: #00fff5; 
            padding: 12px; 
            border-radius: 6px;
            border: 1px solid #00fff5;
        """)
        main_layout.addWidget(self.status_banner)

        # --- 2. Cartes de Télémétrie Grid ---
        grid_layout = QGridLayout()
        
        self.card_v = MetricCard("Tension Batterie", "V", "#00fff5")
        self.card_i = MetricCard("Courant Batterie", "A", "#00fff5")
        self.card_temp = MetricCard("Température Pack", "°C", "#ff2e63")
        self.card_harm = MetricCard("Harmonique 3H (Defect)", "A", "#e23e57")

        grid_layout.addWidget(self.card_v, 0, 0)
        grid_layout.addWidget(self.card_i, 0, 1)
        grid_layout.addWidget(self.card_temp, 0, 2)
        grid_layout.addWidget(self.card_harm, 0, 3)

        main_layout.addLayout(grid_layout)

        # --- 3. Graphique Oscilloscope PyqtGraph ---
        self.plot_widget = pg.PlotWidget(title="<b>Courant de Phase Moteur (A) - Temps Réel</b>")
        self.plot_widget.setBackground('#1b1b2f')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(-50, 200)
        
        # Courbe Style Néon
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='#00fff5', width=2))
        main_layout.addWidget(self.plot_widget)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def update_can_data(self):
        while True:
            msg = self.bus.recv(timeout=0.001)
            if msg is None:
                break

            if msg.arbitration_id == 0x100:
                data = self.msg_battery.decode(msg.data)
                self.card_v.set_value(data['Battery_Voltage'])
                self.card_i.set_value(data['Battery_Current'])
                self.card_temp.set_value(data['Battery_Temp'])

            elif msg.arbitration_id == 0x200:
                data = self.msg_motor.decode(msg.data)
                harm_amp = data['Harmonic_Defect_Amp']
                i_rms = data['Phase_Current_RMS']

                self.card_harm.set_value(harm_amp)

                # Graphique glissant
                self.time_counter += 0.04
                self.time_data.append(self.time_counter)
                self.current_data.append(i_rms)

                if len(self.time_data) > 120:
                    self.time_data.pop(0)
                    self.current_data.pop(0)

                self.curve.setData(self.time_data, self.current_data)

                # Diagnostic d'alerte
                if harm_amp > 5.0:
                    self.status_banner.setText("🚨 CRITICAL ALERT: HARMONIC FAULT DETECTED (INVERTER DEFECT)")
                    self.status_banner.setStyleSheet("""
                        background-color: #6a097d; 
                        color: #ff2e63; 
                        padding: 12px; 
                        border-radius: 6px;
                        border: 2px solid #ff2e63;
                    """)
                else:
                    self.status_banner.setText("🟢 SYSTEM STATUS: NOMINAL")
                    self.status_banner.setStyleSheet("""
                        background-color: #0f5257; 
                        color: #00fff5; 
                        padding: 12px; 
                        border-radius: 6px;
                        border: 1px solid #00fff5;
                    """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ECU_Dashboard()
    window.show()
