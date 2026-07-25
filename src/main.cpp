#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include <cstring>
#include <unistd.h>
#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <eigen/Eigen/Dense>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// --- Module 1 : Estimation d'état (EKF SoC) ---
class EKF_SoC {
private:
    double soc, P, Q, R;
    const double Capacity = 50.0;
public:
    EKF_SoC() : soc(0.8), P(0.1), Q(0.0001), R(0.05) {}
    double update(double voltage, double current, double dt) {
        double soc_pred = soc - (current * (dt / 3600.0)) / Capacity;
        double P_pred = P + Q;
        double v_expected = 300.0 + 100.0 * soc_pred - 0.05 * current;
        double H = 100.0;
        double K = (P_pred * H) / (H * P_pred * H + R);
        soc = soc_pred + K * (voltage - v_expected);
        P = (1.0 - K * H) * P_pred;
        if (soc > 1.0) soc = 1.0;
        if (soc < 0.0) soc = 0.0;
        return soc * 100.0;
    }
};

// --- Module 2 : Traitement du Signal (Analyse Spectrale DSP) ---
class SignalAnalyzer {
public:
    static bool detectHarmonicDefect(double harmonic_amplitude, double threshold = 5.0) {
        return harmonic_amplitude > threshold;
    }
};

int main() {
    int s;
    struct sockaddr_can addr;
    struct ifreq ifr;
    struct can_frame frame;

    if ((s = socket(PF_CAN, SOCK_RAW, CAN_RAW)) < 0) {
        std::cerr << "❌ Erreur Socket CAN" << std::endl;
        return 1;
    }

    std::strcpy(ifr.ifr_name, "vcan0");
    ioctl(s, SIOCGIFINDEX, &ifr);

    memset(&addr, 0, sizeof(addr));
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        std::cerr << "❌ Erreur Bind vcan0" << std::endl;
        return 1;
    }

    std::cout << "==========================================================" << std::endl;
    std::cout << "  ECU DIAGNOSTIC AUTO - EKF (Batterie) & DSP (Moteur)    " << std::endl;
    std::cout << "==========================================================" << std::endl;

    EKF_SoC ekf;

    while (true) {
        int nbytes = read(s, &frame, sizeof(struct can_frame));
        if (nbytes < 0) break;

        // --- Trame 0x100 : Diagnostic Batterie & EKF ---
        if (frame.can_id == 0x100) {
            uint16_t raw_v = (frame.data[1] << 8) | frame.data[0];
            int16_t raw_i = (frame.data[3] << 8) | frame.data[2];
            int8_t raw_t = frame.data[4];

            double v = raw_v * 0.1;
            double i = raw_i * 0.1;
            double t = raw_t - 40;
            double soc = ekf.update(v, i, 0.05);

            std::cout << "[BMS EKF] V: " << v << "V | I: " << i << "A | SoC: " << soc << "%";
        }

        // --- Trame 0x200 : Diagnostic Moteur / Analyse Spectrale ---
        if (frame.can_id == 0x200) {
            uint16_t raw_i_rms = (frame.data[1] << 8) | frame.data[0];
            uint16_t raw_harm = (frame.data[3] << 8) | frame.data[2];
            uint16_t raw_rpm = (frame.data[5] << 8) | frame.data[4];

            double i_rms = raw_i_rms * 0.1;
            double harm_amp = raw_harm * 0.01;
            int rpm = raw_rpm;

            bool defect = SignalAnalyzer::detectHarmonicDefect(harm_amp);

            std::cout << " | [MOTEUR DSP] RPM: " << rpm << " | Amp_3H: " << harm_amp << "A";
            if (defect) {
                std::cout << " 🚨 [ALERTE DEFECT: HARMONIQUE ANORMALE DETECTEE!]";
            } else {
                std::cout << " 🟢 [OK]";
            }
            std::cout << std::endl;
        }
    } 

    close(s);
    return 0;
}
