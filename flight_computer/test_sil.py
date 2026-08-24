import time

class FlightState:
    STARTUP = 0
    IDLE_PAD = 1
    ARMED = 2
    POWERED_ASCENT = 3
    COASTING = 4
    APOGEE = 5
    DESCENT = 6
    MAIN_DEPLOY = 7
    LANDED = 8
    ERROR_STATE = 9

def state_to_string(state):
    return {
        0: "STARTUP",
        1: "IDLE_PAD",
        2: "ARMED",
        3: "POWERED_ASCENT",
        4: "COASTING",
        5: "APOGEE [!!! DROGUE DEPLOY !!!]",
        6: "DESCENT",
        7: "MAIN_DEPLOY [!!! MAIN CHUTE !!!]",
        8: "LANDED",
        9: "ERROR_STATE"
    }.get(state, "UNKNOWN")

class SensorData:
    def __init__(self):
        self.accel_z = 1.0
        self.altitude_agl = 0.0
        self.vertical_vel = 0.0
        self.is_armed = False

current_state = FlightState.STARTUP
current_data = SensorData()

def log_state_change(new_state):
    print(f"\n[STATE CHANGE] Transition to: {state_to_string(new_state)}")

def update_state_machine():
    global current_state, current_data
    if current_state == FlightState.STARTUP:
        print("Performing System Checks...")
        current_state = FlightState.IDLE_PAD
        log_state_change(current_state)
    elif current_state == FlightState.IDLE_PAD:
        if current_data.is_armed:
            current_state = FlightState.ARMED
            log_state_change(current_state)
    elif current_state == FlightState.ARMED:
        if current_data.accel_z > 2.5:
            current_state = FlightState.POWERED_ASCENT
            log_state_change(current_state)
    elif current_state == FlightState.POWERED_ASCENT:
        if current_data.accel_z <= 0.5:
            current_state = FlightState.COASTING
            log_state_change(current_state)
    elif current_state == FlightState.COASTING:
        if current_data.vertical_vel <= 0.0 and current_data.altitude_agl > 10.0:
            current_state = FlightState.APOGEE
            log_state_change(current_state)
            # 立即切入下降
            current_state = FlightState.DESCENT
            log_state_change(current_state)
    elif current_state == FlightState.DESCENT:
        if current_data.altitude_agl <= 150.0 and current_data.vertical_vel < -1.0:
            current_state = FlightState.MAIN_DEPLOY
            log_state_change(current_state)
    elif current_state == FlightState.MAIN_DEPLOY:
        if current_data.altitude_agl <= 1.0 and abs(current_data.vertical_vel) < 0.5:
            current_state = FlightState.LANDED
            log_state_change(current_state)

def run_simulation():
    global current_state, current_data
    print("--- Starting Python SIL Simulation ---")
    log_state_change(current_state)
    
    update_state_machine()
    
    print("\n[SIM] Ground Station sending ARM command...")
    current_data.is_armed = True
    update_state_machine()
    
    print("\n[SIM] Ignition! Motor burning...")
    current_data.accel_z = 5.0
    current_data.vertical_vel = 50.0
    current_data.altitude_agl = 20.0
    update_state_machine()
    
    print("\n[SIM] Motor burnout, coasting...")
    current_data.accel_z = -0.5
    current_data.vertical_vel = 30.0
    current_data.altitude_agl = 100.0
    update_state_machine()
    
    print("\n[SIM] Reaching Apogee...")
    current_data.vertical_vel = -0.1
    current_data.altitude_agl = 500.0
    update_state_machine()
    
    print("\n[SIM] Descending under drogue chute...")
    current_data.vertical_vel = -15.0
    current_data.altitude_agl = 140.0
    update_state_machine()
    
    print("\n[SIM] Touchdown...")
    current_data.vertical_vel = 0.0
    current_data.altitude_agl = 0.5
    update_state_machine()
    
    print("\n--- Simulation Complete ---")

if __name__ == "__main__":
    run_simulation()
