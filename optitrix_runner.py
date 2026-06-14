"""
optitrix_runner.py — OptiTrix PID controller runner

A PID controller is three operations on two numbers:
  error  = setpoint - measurement
  output = Kp*error + Ki*integral(error) + Kd*d(error)/dt
  clamp  = clip(output, min, max)

Each term maps to one tile. All six tiles fit the ~900c single-card budget.
The full controller is a pipeline of ponds connected by PTT bridges.

FIXED-POINT ENCODING: Q16.16 (bits 31-16 integer, bits 15-0 fractional).
Gains as arithmetic right-shifts (power-of-2 approximation, zero fabric cost).

THREE DEMOS:
  1. Motor velocity PID    — classic servo loop, Re=100 step response
  2. Temperature PID       — slow plant, integrator wind-up demonstration
  3. Cascade PID           — outer position loop → inner velocity loop
                             (two OPT pipelines in series, SensorTrix bridging)

Run: python3 optitrix_runner.py
"""

import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cell_format import FormatRegistry, OptiTrix, SensorTrix

fmt = OptiTrix()
sfmt = SensorTrix()
reg = FormatRegistry.get_default()
reg.register_class(OptiTrix)
reg.register_class(SensorTrix)

FRAC = fmt.FRAC_BITS   # 16
SCALE = fmt.SCALE       # 65536


# ── Reference tile implementations ────────────────────────────────────────────

def ref_error(setpoint: int, measurement: int) -> int:
    """OPT_ERROR: error = setpoint - measurement (Q16.16)."""
    return (setpoint - measurement) & 0xFFFFFFFF

def ref_p_term(error: int, kp_shift: int) -> int:
    """OPT_P_TERM: P = error >> kp_shift (arithmetic, signed)."""
    signed = error if error < 0x80000000 else error - 0x100000000
    return (signed >> kp_shift) & 0xFFFFFFFF

def ref_i_acc(prev_i: int, error: int) -> int:
    """OPT_I_ACC: I = prev_I + error (Q16.16, wraps on overflow)."""
    return (prev_i + error) & 0xFFFFFFFF

def ref_d_term(error: int, prev_error: int) -> int:
    """OPT_D_TERM: D = error - prev_error (Q16.16)."""
    return (error - prev_error) & 0xFFFFFFFF

def ref_sum_pi(p: int, i: int) -> int:
    """OPT_SUM_PI: PI = P + I."""
    return (p + i) & 0xFFFFFFFF

def ref_sum_pid(pi: int, d: int) -> int:
    """OPT_SUM_PID: PID = PI + D."""
    return (pi + d) & 0xFFFFFFFF

def to_q(v: float) -> int:
    """Float to Q16.16."""
    return fmt.to_fixed(v)

def from_q(w: int) -> float:
    """Q16.16 to float."""
    return fmt.from_fixed(w)


# ── PID controller (reference implementation) ─────────────────────────────────

class PIDController:
    """
    Reference PID using the six OptiTrix tile functions.
    State: prev_I (integral accumulator), prev_error (for derivative).
    Gains: kp_shift (P), ki_shift (I), kd_shift (D) as right-shift counts.
    Anti-windup: integral clamped to [-i_max, i_max] before next tick.
    """

    def __init__(self, kp_shift=1, ki_shift=4, kd_shift=2,
                 out_min=-32768.0, out_max=32768.0, i_max=16384.0):
        self.kp_shift = kp_shift
        self.ki_shift = ki_shift
        self.kd_shift = kd_shift
        self.out_min  = to_q(out_min)
        self.out_max  = to_q(out_max)
        self.i_max    = to_q(i_max)
        self._prev_i     = to_q(0.0)
        self._prev_error = to_q(0.0)

    def step(self, setpoint: float, measurement: float):
        """One PID tick. Returns (output_float, terms_dict)."""
        sp  = to_q(setpoint)
        meas = to_q(measurement)

        # Six tile pipeline
        err   = ref_error(sp, meas)
        p     = ref_p_term(err, self.kp_shift)
        i_raw = ref_i_acc(self._prev_i, ref_p_term(err, self.ki_shift))
        d_raw = ref_d_term(err, self._prev_error)
        d     = ref_p_term(d_raw, self.kd_shift)
        pi    = ref_sum_pi(p, i_raw)
        pid   = ref_sum_pid(pi, d)

        # Anti-windup clamp on integral (host-side, zero fabric cost)
        i_clamped = max(-self.i_max,
                        min(self.i_max, i_raw if i_raw < 0x80000000
                            else i_raw - 0x100000000)) & 0xFFFFFFFF

        # Output clamp
        pid_s = pid if pid < 0x80000000 else pid - 0x100000000
        pid_clamped = max(
            (self.out_min if self.out_min < 0x80000000
             else self.out_min - 0x100000000),
            min(
                (self.out_max if self.out_max < 0x80000000
                 else self.out_max - 0x100000000),
                pid_s
            )
        ) & 0xFFFFFFFF

        # Update preloaded state for next tick
        self._prev_i     = i_clamped
        self._prev_error = err

        return from_q(pid_clamped), {
            'error': from_q(err),
            'p':     from_q(p),
            'i':     from_q(i_raw),
            'd':     from_q(d),
            'output': from_q(pid_clamped),
        }

    def reset(self):
        self._prev_i     = to_q(0.0)
        self._prev_error = to_q(0.0)


# ── Demo 1: Motor velocity PID ────────────────────────────────────────────────

def demo_motor_velocity():
    """
    Motor velocity servo loop.
    Plant: discrete first-order  v(t+1) = 0.7*v(t) + 0.3*u(t)
    Steady state: v_ss = u_ss (plant gain = 1 at DC).
    Setpoint: step from 0 to 100 RPM at tick 0.
    Gain encoding: Kp=0.5 (shift=1), Ki=0.125 (shift=3), Kd=0.25 (shift=2).
    Expected: within 5% by tick ~25, within 2% by tick ~35.
    """
    print("\n── Demo 1: Motor velocity PID (step response) ──")
    pid = PIDController(kp_shift=1, ki_shift=3, kd_shift=2,
                        out_min=-500.0, out_max=500.0, i_max=200.0)

    setpoint = 100.0
    velocity = 0.0
    alpha    = 0.7    # plant pole
    beta     = 0.3    # plant gain (= 1-alpha, so DC gain = beta/(1-alpha) = 1.0)

    print(f"  {'Tick':>4}  {'Setpoint':>9}  {'Velocity':>9}  "
          f"{'Error':>8}  {'Output':>8}")

    max_overshoot = 0.0
    settled_tick  = None

    for tick in range(50):
        output, terms = pid.step(setpoint, velocity)
        velocity = alpha * velocity + beta * output

        if tick < 6 or tick % 8 == 0:
            print(f"  {tick:>4}  {setpoint:>9.1f}  {velocity:>9.2f}  "
                  f"{terms['error']:>8.2f}  {output:>8.2f}")

        overshoot = velocity - setpoint
        if overshoot > max_overshoot:
            max_overshoot = overshoot

        if settled_tick is None and abs(velocity - setpoint) < 2.0 and tick > 2:
            settled_tick = tick

    print(f"  Max overshoot: {max_overshoot:.2f} RPM  ({100*max_overshoot/setpoint:.1f}%)")
    print(f"  Settled (±2%): tick {settled_tick}")
    return {'max_overshoot_pct': 100*max_overshoot/setpoint,
            'settled_tick': settled_tick,
            'final_velocity': velocity}

# ── Demo 2: Temperature PID (slow plant, integrator) ─────────────────────────

def demo_temperature():
    """
    Temperature control. Plant: slow integrating system (heater/room).
    Setpoint: 22°C. Start: 18°C. Integrator needed to eliminate steady-state error.
    """
    print("\n── Demo 2: Temperature PID (slow integrating plant) ──")
    pid = PIDController(kp_shift=2, ki_shift=6, kd_shift=3,
                        out_min=0.0, out_max=50.0, i_max=30.0)

    setpoint  = 22.0    # °C
    temp      = 18.0    # °C starting point
    heat_gain = 0.05    # °C per unit heater output per tick
    cool_rate = 0.02    # °C natural cooling per tick

    print(f"  {'Tick':>4}  {'Setpoint':>9}  {'Temp':>7}  "
          f"{'Error':>7}  {'I_term':>7}  {'Output':>8}")

    settled_tick = None
    for tick in range(80):
        output, terms = pid.step(setpoint, temp)
        temp += heat_gain * output - cool_rate * (temp - 15.0)

        if tick % 10 == 0 or tick < 5:
            print(f"  {tick:>4}  {setpoint:>9.1f}  {temp:>7.2f}  "
                  f"{terms['error']:>7.3f}  {terms['i']:>7.3f}  {output:>8.3f}")

        if settled_tick is None and abs(temp - setpoint) < 0.1 and tick > 10:
            settled_tick = tick

    print(f"  Settled (±0.1°C): tick {settled_tick}")
    return {'final_temp': temp, 'settled_tick': settled_tick,
            'setpoint': setpoint}


# ── Demo 3: Cascade PID (position → velocity) ─────────────────────────────────

def demo_cascade():
    """
    Cascade control: outer position loop → inner velocity loop.
    Two OptiTrix pipelines connected by SensorTrix bridge.
    Outer PID output becomes velocity setpoint for inner PID.
    Common in robotics: joint position via velocity-controlled motor.
    """
    print("\n── Demo 3: Cascade PID (position outer, velocity inner) ──")

    outer = PIDController(kp_shift=1, ki_shift=5, kd_shift=2,
                          out_min=-50.0, out_max=50.0, i_max=25.0)
    inner = PIDController(kp_shift=1, ki_shift=4, kd_shift=2,
                          out_min=-100.0, out_max=100.0, i_max=50.0)

    pos_setpoint = 1000.0   # encoder counts target
    position     = 0.0
    velocity     = 0.0
    tau_v        = 3.0      # velocity plant time constant
    motor_gain   = 0.6

    print(f"  {'Tick':>4}  {'Pos_SP':>7}  {'Position':>9}  "
          f"{'Vel_SP':>7}  {'Velocity':>9}")

    settled_tick = None
    for tick in range(60):
        # Outer loop: position error → velocity setpoint
        vel_setpoint, outer_terms = outer.step(pos_setpoint, position)

        # SensorTrix bridge: pack outer output as sensor word
        # location=0 (single actuator), amount=|vel_setpoint| scaled
        sensor_word = sfmt.pack(0, int(abs(vel_setpoint) * 10) & 0xFFFF)

        # Inner loop: velocity error → motor command
        motor_cmd, inner_terms = inner.step(vel_setpoint, velocity)

        # Plant: velocity + position integration
        velocity += (motor_gain * motor_cmd - velocity) / tau_v
        position += velocity

        if tick % 6 == 0 or tick < 4:
            print(f"  {tick:>4}  {pos_setpoint:>7.0f}  {position:>9.1f}  "
                  f"{vel_setpoint:>7.1f}  {velocity:>9.2f}")

        if settled_tick is None and abs(position - pos_setpoint) < 10.0 and tick > 5:
            settled_tick = tick

    print(f"  Settled (±10 counts): tick {settled_tick}")
    return {'final_position': position, 'settled_tick': settled_tick}


# ── Validation ─────────────────────────────────────────────────────────────────

def run_validation():
    print("\n── Tile reference validation ──")
    PASS, FAIL = 0, 0

    def check(label, got, expected, tol=0):
        nonlocal PASS, FAIL
        ok = abs(got - expected) <= tol if tol else got == expected
        if ok:
            PASS += 1
            print(f"  [PASS] {label}")
        else:
            FAIL += 1
            print(f"  [FAIL] {label}  got={got}  expected={expected}")

    # OPT_ERROR
    e = ref_error(to_q(100.0), to_q(80.0))
    check("error(100, 80) ≈ 20.0",    from_q(e), 20.0, tol=0.001)
    e2 = ref_error(to_q(50.0), to_q(60.0))
    check("error(50, 60) ≈ -10.0",   from_q(e2), -10.0, tol=0.001)
    check("error(x, x) == 0",        from_q(ref_error(to_q(42.0), to_q(42.0))), 0.0)

    # OPT_P_TERM
    p = ref_p_term(to_q(20.0), 1)
    check("p_term(20.0, shift=1) ≈ 10.0", from_q(p), 10.0, tol=0.001)
    p2 = ref_p_term(to_q(-8.0), 2)
    check("p_term(-8.0, shift=2) ≈ -2.0", from_q(p2), -2.0, tol=0.001)

    # OPT_I_ACC
    i = ref_i_acc(to_q(5.0), to_q(2.0))
    check("i_acc(5.0, 2.0) ≈ 7.0",   from_q(i), 7.0, tol=0.001)

    # OPT_D_TERM
    d = ref_d_term(to_q(20.0), to_q(15.0))
    check("d_term(20, 15) ≈ 5.0",    from_q(d), 5.0, tol=0.001)
    d2 = ref_d_term(to_q(10.0), to_q(12.0))
    check("d_term(10, 12) ≈ -2.0",   from_q(d2), -2.0, tol=0.001)

    # OPT_SUM_PI / OPT_SUM_PID
    pi  = ref_sum_pi(to_q(3.0), to_q(1.5))
    check("sum_pi(3, 1.5) ≈ 4.5",    from_q(pi), 4.5, tol=0.001)
    pid = ref_sum_pid(pi, to_q(0.5))
    check("sum_pid(4.5, 0.5) ≈ 5.0", from_q(pid), 5.0, tol=0.001)

    # OptiTrix FormatDefinition
    from fp_tiles import TileLibrary
    lib = TileLibrary()
    BUDGET = 900
    for name, exp_c, exp_d in [
        ('OPT_ERROR',   517, 12),
        ('OPT_P_TERM',   32,  1),
        ('OPT_I_ACC',   482, 10),
        ('OPT_D_TERM',  517, 12),
        ('OPT_SUM_PI',  482, 10),
        ('OPT_SUM_PID', 482, 10),
    ]:
        t = lib.get(name)
        m = t.metadata
        check(f"{name}: cells={exp_c}", m.cell_count, exp_c)
        check(f"{name}: depth={exp_d}", m.pipeline_depth, exp_d)
        check(f"{name}: fits {BUDGET}c",
              1 if m.cell_count <= BUDGET else 0, 1)

    check("OptiTrix registered", 1 if reg.get("OptiTrix") else 0, 1)
    check("OptiTrix has 6 valid tiles", len(fmt.valid_tiles), 6)

    # Q16.16 round-trip
    for v in [0.0, 1.0, -1.0, 0.5, 100.0, -50.25]:
        rt = from_q(to_q(v))
        check(f"Q16.16 round-trip {v}", rt, v, tol=0.0001)

    print(f"\n  Results: {PASS} passed, {FAIL} failed")
    return FAIL == 0


if __name__ == "__main__":
    print("⬡ OptiTrix — PID controller pipeline")
    print("=" * 55)

    ok = run_validation()
    r1 = demo_motor_velocity()
    r2 = demo_temperature()
    r3 = demo_cascade()

    print(f"\n{'='*55}")
    assert r1['max_overshoot_pct'] < 15.0,  f"Motor overshoot too high: {r1['max_overshoot_pct']:.1f}%"
    assert r1['settled_tick'] is not None,   "Motor velocity did not settle"
    assert r1['settled_tick'] < 45,          f"Motor settled too slowly: tick {r1['settled_tick']}"
    assert r2['settled_tick'] is not None or abs(r2['final_temp'] - r2['setpoint']) < 1.5, "Temperature did not converge"
    assert r3['settled_tick'] is not None,   "Cascade position did not settle"

    if ok:
        print("All demos passed ✓")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
