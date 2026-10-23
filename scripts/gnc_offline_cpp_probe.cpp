// Deterministic software-only probe for R2.3.
//
// This translation unit includes the production algorithm implementations
// directly.  It accepts the CSV trace emitted by gnc_offline_oracle.py and
// writes one result row per production PID/Kalman call.  It deliberately has
// no Arduino setup, sensor bus, servo, plant, or recovery path.

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../flight_computer/src/algorithms/pid.cpp"
#include "../flight_computer/src/algorithms/kalman.cpp"

static std::vector<std::string> split(const std::string &line) {
    std::vector<std::string> parts;
    std::stringstream input(line);
    std::string part;
    while (std::getline(input, part, ',')) parts.push_back(part);
    return parts;
}

static float number(const std::string &value) {
    return static_cast<float>(std::strtod(value.c_str(), nullptr));
}

int main() {
    PIDController pid(PIDController::FLIGHT);
    KalmanFilter kalman;
    std::cout << std::setprecision(9) << std::fixed;

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        const std::vector<std::string> fields = split(line);
        const std::string &kind = fields[0];
        if (kind == "PID_PROFILE") {
            if (fields.size() != 3) return 2;
            pid.setProfile(fields[2] == "testbench" ? PIDController::TESTBENCH
                                                     : PIDController::FLIGHT);
        } else if (kind == "PID_RESET") {
            pid.reset();
        } else if (kind == "PID") {
            if (fields.size() != 5) return 2;
            const float value = pid.compute(number(fields[3]), number(fields[4]));
            std::cout << "PID," << fields[1] << "," << fields[2] << "," << value << "\n";
        } else if (kind == "KALMAN_RESET") {
            kalman.init();
        } else if (kind == "KALMAN") {
            if (fields.size() != 6) return 2;
            const float value = kalman.update(number(fields[3]), number(fields[4]), number(fields[5]));
            std::cout << "KALMAN," << fields[1] << "," << fields[2] << "," << value << "\n";
        } else {
            return 2;
        }
    }
    return 0;
}
