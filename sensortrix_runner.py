"""
sensortrix_runner.py — SensorTrix runner + SensorBridge

Every physical sensor is (location, amount):
  location  — which sensor in the array, which axis, which channel (16-bit)
  amount    — the ADC reading, scaled to [0, 65535] (16-bit)

Packed into one 32-bit bus word: bits 31-16 = amount, bits 15-0 = location.

A sensor STACK (array) is N words on N consecutive bus addresses — one word
per element. The location field carries the array index so the fabric can
route without separate address ranges. Robotics: a 12-DOF joint encoder
array is 12 readings, one stream, one format, one bridge.

Covers without modification:
  touch array      (location = contact_id + axis, amount = pressure)
  IMU              (location = axis 0-5, amount = accel/gyro reading)
  microphone array (location = element_id, amount = amplitude)
  magnetometer     (location = axis 0-2, amount = field strength)
  motor encoders   (location = joint_id, amount = position/velocity)
  sonar array      (location = beam_id,  amount = echo amplitude)
  tactile skin     (location = taxel_id, amount = contact force)
  any N-channel ADC (location = channel_id, amount = raw count)

SensorBridge:
  Thin extension of MouseBridge. Background thread reads from a data source
  (real device, simulation, or test fixture) and packs (location, amount)
  words into a queue. The DeviceManager polls each tick, places the latest
  word on the bus at the configured OUT_ADDR.

  Real device path: USB HID (touch, gamepad), I2C/SPI (IMU, mag) via
  host driver → bridge thread → bus word. The bridge only packs; decoding
  is the fabric's job.

Run: python3 sensortrix_runner.py
"""

import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cell_format import FormatRegistry, SensorTrix

fmt = SensorTrix()
reg = FormatRegistry.get_default()
reg.register_class(SensorTrix)


# ── Reference tile implementations (ground truth for validation) ───────────────

def ref_unpack(word: int):
    """Reference SENSOR_UNPACK: (location, amount) from 32-bit word."""
    return fmt.unpack(word)

def ref_threshold(amount: int, threshold: int) -> int:
    """Reference SENSOR_THRESHOLD: 1 if amount >= threshold, else 0."""
    return 1 if amount >= threshold else 0

def ref_delta(current: int, previous: int) -> int:
    """Reference SENSOR_DELTA: signed change = current - previous."""
    delta = current - previous
    # Keep in signed 16-bit range
    if delta > 32767:  delta -= 65536
    if delta < -32768: delta += 65536
    return delta

def ref_stack_max(a: int, b: int) -> int:
    """Reference SENSOR_STACK_MAX: max of two amounts."""
    return max(a, b)

def ref_stack_sum(a: int, b: int) -> int:
    """Reference SENSOR_STACK_SUM: sum of two amounts (32-bit, may overflow)."""
    return (a + b) & 0xFFFFFFFF


# ── Simulation runner ──────────────────────────────────────────────────────────

def run_sensor_demo():
    """
    Demonstrate SensorTrix over three example sensor stacks:
      1. Touch array  — 5-finger pressure, find peak and detect contact
      2. IMU          — 6-DOF (3-axis accel + 3-axis gyro), find max magnitude
      3. Motor arm    — 6-joint encoder array, compute velocity (delta)
    """
    random.seed(42)

    results = {}

    # ── 1. Touch array: 5 fingers, (contact_id, pressure) ────────────────────
    print("\n── Touch array (5-finger pressure) ──")
    contact_threshold = 1000   # min pressure to count as real contact

    # Simulate: fingers 2 and 4 are pressing
    touch_readings = [
        (0, 0),      # finger 0: no contact
        (1, 500),    # finger 1: light touch (below threshold)
        (2, 12800),  # finger 2: firm press
        (3, 0),      # finger 3: no contact
        (4, 31000),  # finger 4: strong press
    ]

    words   = fmt.pack_stack(touch_readings)
    unpacked = fmt.unpack_stack(words)

    print(f"  {'Finger':>6}  {'Amount':>6}  {'Contact?':>8}  {'Word':>10}")
    contacts = []
    amounts  = []
    for loc, amt in unpacked:
        fired = ref_threshold(amt, contact_threshold)
        contacts.append(fired)
        amounts.append(amt)
        print(f"  {loc:>6}  {amt:>6}  {'YES' if fired else 'no':>8}  "
              f"{fmt.pack(loc, amt):#010x}")

    peak = amounts[0]
    for a in amounts[1:]:
        peak = ref_stack_max(peak, a)
    total = 0
    for a in amounts:
        total = ref_stack_sum(total, a)

    print(f"  Peak pressure : {peak}  (finger 4)")
    print(f"  Total force   : {total}  (sum across all fingers)")
    print(f"  Contacts      : {sum(contacts)} of {len(contacts)} fingers active")

    results['touch'] = {
        'peak': peak, 'total': total, 'contacts': sum(contacts),
        'expected_peak': 31000, 'expected_contacts': 2
    }

    # ── 2. IMU: 6-DOF, find peak magnitude axis ───────────────────────────────
    print("\n── IMU (6-DOF: ax,ay,az,gx,gy,gz) ──")
    # Axis encoding: 0-2 = accel X/Y/Z, 3-5 = gyro X/Y/Z
    # amount: 0=centre, 32767=1g (accel) or 1rad/s (gyro), scaled

    imu_readings = [
        (0,  1640),   # ax: ~0.05g (near still)
        (1,  1800),   # ay: ~0.055g
        (2, 32200),   # az: ~0.98g (gravity dominant)
        (3,   320),   # gx: low rotation
        (4,   180),   # gy: low rotation
        (5,   410),   # gz: small yaw
    ]

    axis_names = ['ax','ay','az','gx','gy','gz']
    imu_words  = fmt.pack_stack(imu_readings)
    imu_unpacked = fmt.unpack_stack(imu_words)

    print(f"  {'Axis':>4}  {'Amount':>6}  {'Word':>10}")
    imu_amounts = []
    for (loc, amt), name in zip(imu_unpacked, axis_names):
        imu_amounts.append(amt)
        print(f"  {name:>4}  {amt:>6}  {fmt.pack(loc, amt):#010x}")

    imu_peak = imu_amounts[0]
    for a in imu_amounts[1:]:
        imu_peak = ref_stack_max(imu_peak, a)
    imu_sum = 0
    for a in imu_amounts:
        imu_sum = ref_stack_sum(imu_sum, a)

    print(f"  Peak magnitude axis: {imu_peak}  (az — gravity)")
    print(f"  Sum across all axes: {imu_sum}")

    results['imu'] = {
        'peak': imu_peak, 'sum': imu_sum,
        'expected_peak': 32200   # az dominates
    }

    # ── 3. Motor arm: 6-joint encoder, velocity via SENSOR_DELTA ─────────────
    print("\n── Motor arm (6-joint encoder, velocity) ──")

    # Two consecutive position readings, compute velocity (delta)
    prev_positions = [10000, 20000, 5000, 15000, 25000, 8000]
    curr_positions = [10050,  19980, 5120, 15000, 24800, 8200]

    print(f"  {'Joint':>5}  {'Prev':>6}  {'Curr':>6}  {'Delta':>7}  {'Direction':>10}")
    deltas = []
    for i, (prev, curr) in enumerate(zip(prev_positions, curr_positions)):
        delta = ref_delta(curr, prev)
        deltas.append(delta)
        direction = 'forward' if delta > 0 else ('backward' if delta < 0 else 'still')
        print(f"  {i:>5}  {prev:>6}  {curr:>6}  {delta:>+7}  {direction:>10}")

    # Pack current + delta as a combined reading for downstream
    # (location = joint_id, amount = |delta| for magnitude routing)
    combined = [(i, abs(d)) for i, d in enumerate(deltas)]
    peak_velocity = max(abs(d) for d in deltas)
    print(f"  Peak velocity: {peak_velocity} counts/tick (joint 2)")

    results['arm'] = {
        'deltas': deltas, 'peak_velocity': peak_velocity,
        'expected_peak': 200   # joints 5 and 4 both hit 200
    }

    return results


def run_validation():
    """Validate all tile reference implementations with known values."""
    print("\n── Tile reference validation ──")
    PASS, FAIL = 0, 0

    def check(label, got, expected):
        nonlocal PASS, FAIL
        if got == expected:
            PASS += 1
            print(f"  [PASS] {label}")
        else:
            FAIL += 1
            print(f"  [FAIL] {label}  got={got}  expected={expected}")

    # SENSOR_UNPACK
    check("unpack(0xFFFF0000) → (0, 65535)",
          ref_unpack(0xFFFF0000), (0, 65535))
    check("unpack(0x00010002) → (2, 1)",
          ref_unpack(0x00010002), (2, 1))
    check("unpack(0x80001234) → (0x1234, 0x8000)",
          ref_unpack(0x80001234), (0x1234, 0x8000))
    check("pack(3, 12800) round-trips",
          ref_unpack(fmt.pack(3, 12800)), (3, 12800))

    # SENSOR_THRESHOLD
    check("threshold(5000, 1000) → 1",   ref_threshold(5000, 1000), 1)
    check("threshold(500,  1000) → 0",   ref_threshold(500,  1000), 0)
    check("threshold(1000, 1000) → 1",   ref_threshold(1000, 1000), 1)  # boundary
    check("threshold(0,    0)    → 1",   ref_threshold(0,    0),    1)
    check("threshold(0,    1)    → 0",   ref_threshold(0,    1),    0)

    # SENSOR_DELTA
    check("delta(100, 80)   → +20",      ref_delta(100, 80),    20)
    check("delta(80,  100)  → -20",      ref_delta(80,  100),  -20)
    check("delta(100, 100)  → 0",        ref_delta(100, 100),   0)
    check("delta(0, 65535)  → +1 (wrap)", ref_delta(0, 65535),   1)  # unsigned wrap

    # SENSOR_STACK_MAX
    check("stack_max(100, 200)  → 200",  ref_stack_max(100, 200), 200)
    check("stack_max(200, 100)  → 200",  ref_stack_max(200, 100), 200)
    check("stack_max(0,   0)    → 0",    ref_stack_max(0, 0),     0)

    # SENSOR_STACK_SUM
    check("stack_sum(100, 200)  → 300",  ref_stack_sum(100, 200),   300)
    check("stack_sum(0,   0)    → 0",    ref_stack_sum(0, 0),         0)
    check("stack_sum(65535, 1) → 65536", ref_stack_sum(65535, 1), 65536)

    # pack/unpack round-trip for stack
    readings = [(i, i * 1000) for i in range(8)]
    rt = fmt.unpack_stack(fmt.pack_stack(readings))
    check("pack_stack/unpack_stack round-trip (8 elements)",
          rt, readings)

    # FormatDefinition registered
    check("SensorTrix registered in FormatRegistry",
          reg.get("SensorTrix") is not None, True)

    print(f"\n  Results: {PASS} passed, {FAIL} failed")
    return FAIL == 0


if __name__ == "__main__":
    print("⬡ SensorTrix — unified (location, amount) sensor format")
    print("=" * 58)

    ok = run_validation()
    results = run_sensor_demo()

    # Spot-check demo results
    assert results['touch']['peak']     == results['touch']['expected_peak'],     "touch peak wrong"
    assert results['touch']['contacts'] == results['touch']['expected_contacts'],  "touch contacts wrong"
    assert results['imu']['peak']       == results['imu']['expected_peak'],       "IMU peak wrong"
    assert results['arm']['peak_velocity'] == results['arm']['expected_peak'],    "arm velocity wrong"

    print(f"\n{'='*58}")
    if ok:
        print("All demos passed ✓")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
