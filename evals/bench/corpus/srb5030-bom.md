# SRB-5030 Bill of Materials

Orbeck Power Systems, assembly OPS-9001. Revision B, 06/01/2026. Quantities are per board. Part
numbers are Orbeck internal numbers; the approved manufacturer list for each is held in the ERP
system and is not reproduced here.

## 1. Bill of Materials, Revision B

| Ref | Qty | Part | Description |
| --- | --- | --- | --- |
| U1 | 1 | OPS-1147 | Synchronous buck controller, 40 V, 500 kHz, integrated FETs |
| L1 | 1 | OPS-2210 | Inductor, 10 uH, 4.5 A saturation, 28 mohm DCR, shielded composite, 6.0 x 6.0 x 3.0 mm |
| C1, C2 | 2 | OPS-3105 | Capacitor, 10 uF, 50 V, X7R, 1210, input |
| C3, C4 | 2 | OPS-3222 | Capacitor, 22 uF, 25 V, X7R, 1210, output |
| C5 | 1 | OPS-3010 | Capacitor, 100 nF, 50 V, X7R, 0603, bootstrap |
| C6, C7 | 2 | OPS-3010 | Capacitor, 100 nF, 50 V, X7R, 0603, decoupling |
| C8 | 1 | OPS-3009 | Capacitor, 10 nF, 50 V, X7R, 0603, soft start |
| R1 | 1 | OPS-4105 | Resistor, 105 kohm, 0.1%, 0603, feedback upper |
| R2 | 1 | OPS-4200 | Resistor, 20.0 kohm, 0.1%, 0603, feedback lower |
| R3 | 1 | OPS-4100 | Resistor, 100 kohm, 1%, 0603, enable pull-up |
| J1, J2 | 2 | OPS-5002 | Terminal block, 2 position, 5.08 mm pitch |
| TP1-TP4 | 4 | OPS-6001 | Test point, 1.0 mm loop |
| PCB | 1 | OPS-9001-B | Printed circuit board, 4 layer, 2 oz outer, 38 x 25 mm |

## 2. Output Voltage Setting

The output voltage is set by R1 and R2 against the OPS-1147's 0.800 V reference:

    VOUT = 0.800 * (1 + R1 / R2) = 0.800 * (1 + 105000 / 20000) = 0.800 * 6.25 = 5.000 V

Both values are E96 and the ratio is exact, so the nominal output is 5.000 V with no trim. Divider
current is 0.800 V / 20.0 kohm = 40 uA.

The reference is specified to +/-0.5 percent and the divider resistors to 0.1 percent, which sets
the unit-to-unit spread of the output voltage. That spread, plus the 7 mV of droop at the 1.0 A
test point, is what the +/-1 percent production window in `srb5030-test-spec.md` section 4 is
drawn around.

R1 and R2 are 0.1 percent parts and are not interchangeable with 1 percent parts of the same
value. A 1 percent divider widens the output spread by roughly a factor of three and takes the
production window with it.

## 3. Output Capacitors

C3 and C4 set the ripple. They are 22 uF 25 V X7R parts that derate to about 12 uF each at 5 V DC
bias, for about 24 uF of effective output capacitance. The ripple arithmetic in
`srb5030-datasheet.md` section 6 uses that 24 uF and nothing else.

A 22 uF part in a lower voltage rating or a lower-grade dielectric has the same marking, the same
footprint and the same nominal value, and derates much harder under bias. A 16 V X5R part in this
position measures about 3.3 uF at 5 V bias, which is roughly a quarter of what the design assumes
and roughly doubles the output ripple. OPS-3222 is not substitutable on value alone: the voltage
rating and the dielectric are both part of the specification.

## 4. Revision C Change

Revision C changes C1 and C2 from OPS-3105 (10 uF, 50 V, X7R, 1210) to OPS-3106 (10 uF, 63 V, X7R,
1210), per `ecn-2608-04.md`. The footprint is unchanged. Nothing else on this bill of materials
changes.
