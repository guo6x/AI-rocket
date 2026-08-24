import math

# --- Rocket Baseline Parameters ---
m_dry = 0.340 # kg
m_prop_d12 = 0.0242 # kg
A = math.pi * 0.0375**2 # Frontal area (m^2)
Cd = 0.5 # Estimated drag coefficient
rho = 1.225 # Air density (kg/m^3)
g = 9.81
rail_length = 1.0 # m

def estimate_apogee(I_total, t_burn, m_prop, name, out_file):
    m_avg = m_dry + m_prop/2
    F_avg = I_total / t_burn
    
    out_file.write(f"\n{'='*40}\n")
    out_file.write(f"  Estimating Performance: {name}\n")
    out_file.write(f"{'='*40}\n")
    out_file.write(f"Average Thrust:      {F_avg:.2f} N\n")
    out_file.write(f"Weight (Avg):        {m_avg * g:.2f} N\n")
    out_file.write(f"Thrust/Weight Ratio: {F_avg / (m_avg * g):.2f}\n")
    
    if F_avg <= m_avg * g:
        out_file.write(f"❌ Rocket cannot lift off. Thrust < Weight.\n")
        return
        
    # 1. Burn phase (coarse constant acceleration, ignore drag for initial phase)
    a_avg = (F_avg - m_avg * g) / m_avg
    v_burnout = a_avg * t_burn
    h_burnout = 0.5 * a_avg * t_burn**2
    
    # Check rail departure velocity (v^2 = 2ax)
    v_rail = math.sqrt(2 * a_avg * rail_length)
    
    # 2. Coast phase (with gravity and aerodynamic drag)
    # v(t) = sqrt(mg/k) * tan( atan(v0*sqrt(k/mg)) - sqrt(kg)*t/m )
    # h_coast = (m / (2*k)) * ln( (m*g + k*v0^2) / (m*g) )
    k = 0.5 * rho * Cd * A
    
    if v_burnout > 0:
        h_coast = (m_dry / (2*k)) * math.log((m_dry*g + k*v_burnout**2) / (m_dry*g))
    else:
        h_coast = 0
        
    h_apogee = h_burnout + h_coast
    
    out_file.write(f"Rail Velocity (1m):  {v_rail:.2f} m/s (Target >= 15 m/s)\n")
    out_file.write(f"Burnout Velocity:    {v_burnout:.2f} m/s\n")
    out_file.write(f"Burnout Altitude:    {h_burnout:.2f} m\n")
    out_file.write(f"Coast Altitude:      {h_coast:.2f} m\n")
    out_file.write(f"Total Apogee:        {h_apogee:.2f} m\n")
    
    # 判定
    if h_apogee >= 100 and v_rail >= 15:
        out_file.write(f"Verdict: ✅ SUCCESS (Apogee>=100m, V_rail>=15m/s)\n")
    elif h_apogee >= 100:
        out_file.write(f"Verdict: ⚠️ MARGINAL (Apogee OK, V_rail SLOW -> Risk of weathercocking)\n")
    else:
        out_file.write(f"Verdict: ❌ FAIL (Apogee < 100m)\n")

with open('estimate_results.txt', 'w', encoding='utf-8') as f:
    # Run estimates
    estimate_apogee(I_total=8.8, t_burn=1.9, m_prop=0.010, name="Estes C6-5", out_file=f)
    estimate_apogee(I_total=20.0, t_burn=1.65, m_prop=0.0242, name="Estes D12-5", out_file=f)
    estimate_apogee(I_total=28.8, t_burn=2.44, m_prop=0.0369, name="Estes E12-6", out_file=f)

    # Reverse calculate minimum thrust for 100m and 15m/s
    f.write(f"\n{'='*40}\n")
    f.write("  Reverse Calculating Minimum Specs\n")
    f.write(f"{'='*40}\n")
    # To get v_rail >= 15 m/s on a 1.0m rail: a >= v^2 / 2x = 15^2 / 2 = 112.5 m/s^2
    a_req = 112.5
    # F - mg = ma  -> F = m(g+a)
    F_req = m_dry * (g + a_req) 
    f.write(f"Minimum Average Thrust for safe rail departure (>15m/s): {F_req:.2f} N\n")

    # To get ~100m apogee, require combined impulse
    # Assuming t_burn = 1.5s
    t_b = 1.5
    v_b = a_req * t_b
    h_b = 0.5 * a_req * t_b**2
    k = 0.5 * rho * Cd * A
    h_c = (m_dry / (2*k)) * math.log((m_dry*g + k*v_b**2) / (m_dry*g))
    f.write(f"With Thrust={F_req:.1f}N and burn time={t_b}s (Impulse={F_req*t_b:.1f}Ns):\n")
    f.write(f" -> Apogee would be around {h_b + h_c:.1f} m\n")

print("Done! Check estimate_results.txt")
