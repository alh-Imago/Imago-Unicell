# Reaction-game demo v1 (1 Nov 2026): the Tang alone, with the HW-262 shield

Status: simulated and built, NOT run on a board. Alan's idea (18:47): "led, display 1 2 or 3, you press the button, get time difference", and a counter to give the time dimension. Reading taken: a reaction game; a different reading would change the table and states, not the structure.

## What it does
1. All buttons up. Wait a random 1.0 to 3.0 s (display blank).
2. A target appears: LED 1, 2 or 3 on the Tang lights and the display shows 0001, 0002 or 0003. A 1 ms counter starts (a plain counter on the 27 MHz clock, not a special onboard counter).
3. Press the matching shield button (A1, A2 or A3). The counter stops; the display shows the time in milliseconds as four decimal digits. A wrong button shows E and the first three digits. No press in 9.999 s counts as wrong. Presses before the target are ignored.
4. The reaction time is turned into a layer-1 bin (floor of log2 of the milliseconds, 0..11), together with right or wrong button, and the scorer (the one from `SCORER_v1.md`, table loaded from a ROM at power-up) judges it. A GOOD HIT (right button, under 256 ms with the starting table) lights LED 4 and beeps for 0.2 s.
5. Press any button for the next round.

Starting table (`tools/hexn_demo_rom_v1.py`): reaction bin b gives class 1 the weight -10 x max(0, b-7) and class 0 the weight -10 x max(0, 8-b); a wrong button gives class 1 -100. Change that function to change the judging; no RTL edit.
LEDs: 0 heartbeat, 1/2/3 target, 4 good hit, 5 table loaded. Tang S1 restarts the unit (reloads the table).

## Wiring (Tang pin numbers from Alan's pinout picture)
| Shield | Tang pin | Header |
|---|---|---|
| A1 button | 72 | right, near the bottom |
| A2 button | 71 | right, near the bottom |
| A3 button | **86** | right (13th from the top) - NEW, a proposal; 86 is a plain free pin |
| display latch (shield pin 4) | 25 | left |
| display clock (shield pin 7) | 26 | left |
| display data (shield pin 8) | 27 | left |
| buzzer (shield pin 3) | 28 | left |
| shield 5V pin | Tang 3V3 | right header (16th), next to GND (15th) |
| shield GND | Tang GND | |
Same as the earlier shield build in the main repo (`docs/unit_bringup_guide.md`, shield section) apart from A3. Check with a meter that the shield's 5V pin is its supply rail before connecting, as that guide says. The ESP32 is not needed; unplug its wires from pins 73 to 77 or leave them, nothing drives them.
Pin 79 is the on-board RGB LED data line and 53/52 are the HDMI EDID lines; avoid those for buttons.

## Checked
- Simulation with a fast clock (`tests/hexn_demo/`, `tests/vm/test_hexn_demo_v1.py`): six random-target rounds with reaction times 40 to 225 ms (every third a wrong button) and a slow press at 400 ms: target display and LED right, measured time within 1 to 2 ms of the wait, wrong button shows E and is never a good hit, a right press under 256 ms is a good hit, a right press at 400 ms is not.
- Build: `fpga/build/hexn_react_demo_v1/unit_top.fs`, 712 of 20,736 LUT4 (3%), 200 MHz capable at 27, 15 pins.
- The display and buzzer driver is the earlier `hw262_shield_v1.v`, copied unchanged; its own header still says "not tried on a real shield", while the main repo's status map says proven on the board on 9 Oct. If the idle buzzer sounds, set BUZZ_ACTIVE_LOW to 0.

## To run
`openFPGALoader -b tangnano20k fpga/build/hexn_react_demo_v1/unit_top.fs`, wire as above, wait for LED 5.
