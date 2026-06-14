# SensorTrix

Unified format for all physical sensor inputs.

Every sensor is **(location, amount)** — a 16-bit index and a 16-bit
ADC reading packed into one 32-bit bus word:

```
bits 31-16: amount    (0-65535, device-scaled)
bits 15-0:  location  (sensor index, axis, channel, contact ID)
```

A **sensor stack** is N readings on N consecutive bus addresses — one
word per element. Same format, same tiles, same bridge. Only the host
device differs.

## Covers without modification

| Sensor type | location | amount |
|---|---|---|
| Touch array | contact_id + axis | pressure |
| IMU (accel+gyro+mag) | axis 0-5 | reading |
| Microphone array | element_id | amplitude |
| Motor encoder array | joint_id | position/velocity |
| Sonar array | beam_id | echo amplitude |
| Tactile skin | taxel_id | contact force |
| Any N-channel ADC | channel_id | raw count |

## Tiles

| Tile | Cells | Depth | Purpose |
|---|---|---|---|
| SENSOR_UNPACK | 144c | d5 | Split word into location + amount |
| SENSOR_THRESHOLD | 518c | d14 | Fire when amount >= preloaded T |
| SENSOR_DELTA | 517c | d12 | Change since preloaded previous |
| SENSOR_STACK_MAX | 317c | d66 | Peak across two readings |
| SENSOR_STACK_SUM | 482c | d10 | Sum (mean filter step) |

All tiles fit the ~900c single-card budget.

## Sensor stack reduction

For an N-element stack, use a binary tree of SENSOR_STACK_MAX or
SENSOR_STACK_SUM tiles: N-1 instances, log2(N) depth levels.

Example: 16-element tactile array → peak contact point
- 8 × SENSOR_STACK_MAX at level 0 (pairs)
- 4 × at level 1, 2 × at level 2, 1 × at level 3
- Total: 15 tiles, depth = 4 × d66 = d264
