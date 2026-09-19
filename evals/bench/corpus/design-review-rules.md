# Design Review Rules, Low-Voltage DC Power Boards

Orbeck Power Systems, document DR-0100. Revision 7, 08/11/2026. Revision 7 restated DR-14 after
the revision C review found an existing board that did not meet it. These rules apply to every
Orbeck DC-DC board rated 60 V or less. Each rule is written so that a reviewer can check it
against a bill of materials, a schematic and a layout without asking the designer a question.

## 1. How a Review Is Run

Every rule is checked and the result recorded as met, not met, or not applicable, with the numbers
that support it. A rule that is not met is either fixed or waived in writing, by name, with the
reason. There is no third outcome. A reviewer who cannot tell from the documents whether a rule is
met records that, which counts as not met until the documents say otherwise.

Findings cite the rule number and the evidence. A finding that does not name a rule is a comment,
not a finding, and does not hold a release.

## 2. DR-10: Inductor Saturation Margin

The inductor's saturation current shall be at least 1.3 times the peak inductor current at maximum
rated load, computed as the DC output current plus half the peak-to-peak ripple current.

Evidence required: the ripple current calculation from the input voltage, output voltage,
inductance and switching frequency, and the saturation rating from the inductor specification.

## 3. DR-12: Semiconductor Voltage Derating

A MOSFET or a diode on a DC rail shall be rated at least 1.5 times the maximum steady-state rail
voltage, before any allowance for switching overshoot. Overshoot is measured, not assumed, and is
additional margin, not a substitute for this rule.

## 4. DR-14: Ceramic Capacitor Voltage Derating

A ceramic capacitor on a DC rail shall be rated at least 1.5 times the maximum steady-state rail
voltage stated in the product's own datasheet.

This rule exists for two reasons. A class 2 dielectric loses capacitance under DC bias, so a part
run near its rating delivers far less than its marked value. And a cracked ceramic fails short: on
an input rail, with no fuse between the capacitor and the source, that is the failure mode with
the worst consequence on the board.

The maximum steady-state rail voltage in this rule is the number the datasheet sells, not the
number the design was simulated at. If the datasheet permits 36 V, the rule is checked at 36 V.

## 5. DR-16: Resistor and Capacitor Power Derating

A resistor shall dissipate no more than 60 percent of its rated power at maximum load and maximum
ambient. A capacitor's ripple current shall be no more than 70 percent of its rating at the same
conditions.

## 6. DR-20: Decoupling and Loop Area

Every supply pin shall have a 100 nF ceramic within 3 mm of the pin, on the same layer, with a via
to the plane no more than 1 mm from the pad. Bulk capacitance shall be within 10 mm.

The high-current switching loop, from the input capacitor through the high-side switch, the
low-side switch and back, shall be closed on one layer with a return plane directly beneath it.
The loop area shall be recorded in the review.

## 7. DR-24: Thermal

Junction temperature at maximum rated load and maximum rated ambient shall be at or below
125 degC, computed from the measured or specified thermal resistance and the calculated
dissipation. The calculation shall show the dissipation term by term, not as a single number.

Thermal shutdown is a protection. A design whose junction temperature reaches the shutdown
threshold in any rated operating condition does not meet this rule, whatever the protection does.

## 8. DR-30: Test Access and Markings

Every board shall carry test points for the input, the output and the return, sized for a fixture
probe, and a test point or a probe-accessible pad for the switch node. The board shall carry a
silkscreen revision character and an assembly number that ends in that character, so a board on a
bench can be identified without a label.

A test point that carries a switching node shall be marked for scope use and shall not be usable
as a fixture contact.
