# 🚗 Real-Time EV Powertrain BMS Diagnostic & DSP Signal Monitoring (SIL / SocketCAN)

![System Status](https://img.shields.io/badge/System_Status-Operational-brightgreen)
![Language](https://img.shields.io/badge/C++-17-blue)
![Python](https://img.shields.io/badge/Python-3.10+-yellow)
![Protocol](https://img.shields.io/badge/CAN_Bus-SocketCAN_vcan0-orange)

## 📌 Overview

An end-to-end **Software-in-the-Loop (SIL)** diagnostic and telemetry platform for Electric Vehicle (EV) powertrains and Battery Management Systems (BMS).

The platform simulates multi-node CAN bus telemetry, performs real-time state estimation using an **Extended Kalman Filter (EKF)** for battery SoC/SoH, executes **DSP spectral analysis** (FFT / harmonic tracking) for inverter fault detection, and displays live telemetry on an industrial dark-mode cockpit dashboard.

## 🖥️ Dashboard Preview

Interface web en temps réel affichant les métriques de la batterie, l’état de charge (**SoC**) et la détection de défauts d’onduleur via l’analyse harmonique.

![HIL Telemetry Cockpit Dashboard](./assets/dashboard_preview.png)

## 🏗️ System Architecture

```text
+-------------------------------------------------------+
|              EV Powertrain Simulator                  |
|   (Python + SciPy + cantools + SocketCAN vcan0)       |
+---------------------------+---------------------------+
                            |
                            | CAN Frames (0x100 Battery / 0x200 Motor)
                            v
+---------------------------+---------------------------+
|               C++17 ECU Diagnostic Engine             |
|  - Extended Kalman Filter (EKF) SoC Estimation        |
|  - Signal Processing (Harmonic Fault Detector)        |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
|            HIL Telemetry Cockpit Dashboard            |
|        (FastAPI + Plotly + Live Web Telemetry)        |
+-------------------------------------------------------+
```

## 🚀 Quickstart Guide

### Prerequisites

- Linux (Ubuntu or WSL2).
- GCC / CMake.
- Python 3.10+.
- `can-utils`.

### Setup and Run

#### 1) Initialize the Virtual CAN interface

```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

#### 2) Compile the C++ ECU diagnostic core

```bash
mkdir build
cd build
cmake ..
make
./ecu_diag
```

#### 3) Launch the telemetry cockpit dashboard

```bash
python3 scripts/dashboard_web.py
```

Open the dashboard in your browser:

```text
http://localhost:8000
```

#### 4) Start the EV physical simulator

```bash
python3 scripts/bms_simulator.py
```

## 🛠️ Key Technical Features

- **CAN Bus Communications**: Standard DBC-defined database (`vehicule.dbc`), with multi-frame encoding/decoding via the Linux SocketCAN interface (`vcan0`).
- **Battery SoC Estimation (EKF)**: Non-linear state-space model using the Eigen C++ library for accurate state-of-charge tracking under noisy drive cycles.
- **DSP Inverter Diagnostic**: Real-time monitoring of phase current harmonics to detect 3rd-harmonic parasitic currents associated with IGBT or inter-turn short-circuit defects.
- **Live Telemetry Cockpit**: Low-latency web dashboard displaying real-time metrics, dynamic signal charts, and automatic critical fault banners.

## 📁 Project Structure

```text
.
├── assets/
│   └── dashboard_preview.png
├── build/
├── scripts/
│   ├── bms_simulator.py
│   └── dashboard_web.py
├── src/
│   ├── ecu_diag.cpp
│   └── ...
├── CMakeLists.txt
└── README.md
```

## 📚 Notes

- This project is designed for SIL / HIL-style validation and telemetry experimentation.
- The virtual CAN setup makes it possible to test the full pipeline without physical CAN hardware.
- The architecture is suitable for future extensions such as fault classification, predictive maintenance, and embedded deployment. is designed for SIL / HIL-style validation and telemetry experimentation.
- The virtual CAN setup makes it possible to test the full pipeline without physical CAN hardware.
- The architecture is suitable for future extensions such as fault classification, predictive maintenance, and embedded deployment.
