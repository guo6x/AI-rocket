// Deterministic dual-period probe for the production PID implementation.
//
// This is an offline software boundary: it includes the production
// PIDController translation unit, accepts a fixed CSV protocol on stdin, and
// emits the PID value returned by compute plus the exact integer command used
// by main.cpp (90 + (int)PID output, constrained to [0,180]).  It has no
// Arduino setup, sensor bus, actuator, plant, or recovery path.

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../flight_computer/src/algorithms/pid.cpp"

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
    std::cout << std::setprecision(9) << std::fixed;

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        const std::vector<std::string> fields = split(line);
        const std::string &kind = fields[0];
        if (kind == "RESET") {
            pid.reset();
        } else if (kind == "PID_RESET") {
            if (fields.size() != 2) return 2;
            pid.reset();
        } else if (kind == "PID") {
            if (fields.size() != 6) return 2;
            const int period_ms = std::atoi(fields[1].c_str());
            const int step = std::atoi(fields[2].c_str());
            const int time_ms = std::atoi(fields[3].c_str());
            const float current = number(fields[4]);
            const float dt = number(fields[5]);
            const float output = pid.compute(current, dt);
            const int command = constrain(90 + static_cast<int>(output), 0, 180);
            std::cout << "PID," << period_ms << "," << step << "," << time_ms << ","
                      << current << "," << dt << "," << output << "," << command << "\n";
        } else {
            return 2;
        }
    }
    return 0;
}
