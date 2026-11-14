// Built-up handle (Griffverdickung) - parametric, all dimensions in mm.
// Slides over cutlery, pens, toothbrushes, ... so they can be held with weak grip,
// limited finger flexion or tremor. Printed upright, bore opening up, no supports.

grip_length    = 110;  // total length of the handle
grip_diameter  = 32;   // outer diameter
bore_shape     = 0;    // 0 = round bore, 1 = flat/rectangular bore (flat cutlery)
bore_diameter  = 9;    // round bore: diameter of the utensil/pen shaft
bore_width     = 12;   // flat bore: width of the utensil handle
bore_thickness = 3.5;  // flat bore: thickness of the utensil handle
bore_depth     = 80;   // depth of the bore measured from the top end
finger_grooves = 4;    // number of finger grooves (0 = smooth)
groove_depth   = 2.0;  // depth of the finger grooves
end_radius     = 4;    // rounding of both ends
flat_side      = 1;    // 1 = small flat side so it does not roll off the table
tolerance      = 0.3;  // clearance added around the bore

$fn = 72;

R  = grip_diameter / 2;
L  = grip_length;
e  = min(end_radius, R - 1);
z0 = L * 0.18;
z1 = L * 0.82;

function groove(z) =
    (finger_grooves > 0 && z > z0 && z < z1)
        ? groove_depth * (0.5 - 0.5 * cos(360 * finger_grooves * (z - z0) / (z1 - z0)))
        : 0;

function end_round(z) =
    z < e     ? e - sqrt(max(0, e * e - pow(e - z, 2)))
  : z > L - e ? e - sqrt(max(0, e * e - pow(z - (L - e), 2)))
  : 0;

function r_at(z) = R - groove(z) - end_round(z);

steps   = 120;
profile = concat(
    [[0, 0]],
    [for (i = [0 : steps]) let(z = i * L / steps) [r_at(z), z]],
    [[0, L]]
);

module bore() {
    d = min(bore_depth, L + 2);
    if (bore_shape == 0) {
        translate([0, 0, L - d]) cylinder(d = bore_diameter + 2 * tolerance, h = d + 1);
        // lead-in chamfer
        translate([0, 0, L - 1.5]) cylinder(d1 = bore_diameter + 2 * tolerance, d2 = bore_diameter + 2 * tolerance + 3, h = 1.51);
    } else {
        w = bore_width + 2 * tolerance;
        t = bore_thickness + 2 * tolerance;
        translate([-w / 2, -t / 2, L - d]) cube([w, t, d + 1]);
    }
}

difference() {
    rotate_extrude() polygon(profile);
    bore();
    if (flat_side == 1) translate([R - 1.2, -R - 1, -1]) cube([R, 2 * R + 2, L + 2]);
}
