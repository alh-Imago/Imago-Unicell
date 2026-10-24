# ESP32 sensor logger: wiring and use (24 Oct 2026)

Status: **written, self-tested on fake data only. Not run on hardware.** Pins are copied from the UniCell wiring reference
(`docs/WIRING_REFERENCE_v1.md` in imago-unicell, sections 4 and 5). That reference says the pot and light sensor were wired and read on
10 Oct 2026; thermistor, PIR, tilt and ultrasonic were NOT recorded as run, and the thermistor circuit is an assumption.

## Why a new sketch, not the old /api/live
`/api/live` returns the 20 ms averaged reading (which hides the noise we want) and only answers with the Tang unit attached and a login.
The logger sketch has no WiFi, no averaging and no Tang: it streams every raw sample over USB.

## Wires (ESP32 side only; nothing goes to the Kintex or Tang yet)
| Sensor | Wire | ESP32 pin |
|---|---|---|
| Potentiometer | wiper | GPIO 35 (ADC1); ends to 3V3 and GND |
| Light sensor | A0 / signal | GPIO 36 (ADC1); VCC to 3V3 (never 5 V), GND |
| Thermistor (10k NTC + 10k divider) | midpoint | GPIO 39 (ADC1) |
| PIR | signal | GPIO 16 |
| Tilt switch | signal | GPIO 17 (internal pull-up, LOW when active) |

Leave out anything you do not have; an unconnected analog pin just records noise (useful as a floor reading, label it). Only ADC1 pins are used.
Do not use the ultrasonic one for this: it is timing-based, not a steady sample.

## Steps
1. Arduino IDE: open `tools/esp32/hexn_logger/hexn_logger.ino`, board ESP32, upload over USB.
2. `pip install pyserial`
3. `python3 tools/hexn_esp_log_v1.py --port /dev/ttyUSB0 --rate 1000 --seconds 60 --label <what you did> run1.csv`
   It prints samples, dropped samples and the real spacing. If drops are many, lower `--rate`.
4. Send the CSV back. Useful runs, each with a label: (a) all sensors untouched, lamp on; (b) lamp off / daylight only;
   (c) pot turned slowly; (d) one analog pin with nothing wired; (e) same as (a) at rate 2000 and 200.
   The rate matters: 1000/s lets us see 50 and 100 Hz mains and flicker and test whether looks 10 ms or 5 ms apart cancel.
