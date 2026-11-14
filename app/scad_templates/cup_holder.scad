// Two-handled cup holder (Becherhalter) - parametric, all dimensions in mm.
// Sleeve that fits around an existing cup/glass and adds one or two large
// handles - for tremor (two-handed drinking), weak grip or when a thin glass
// cannot be held safely. Printed upright, no supports (pointed handle openings).

cup_bottom_diameter = 70;   // outer diameter of the cup at its base
cup_top_diameter    = 80;   // outer diameter of the cup at its rim
cup_height          = 95;   // full height of the cup (for the taper)
sleeve_height       = 65;   // height of the sleeve
wall                = 3;    // sleeve wall thickness
base_lip            = 4;    // inward lip at the bottom the cup rests on (0 = none)
handles             = 2;    // 1 or 2 handles
handle_opening_w    = 28;   // finger opening width (radial)
handle_bar          = 10;   // handle bar thickness
handle_thickness    = 14;   // handle thickness (tangential)
tolerance           = 0.8;

$fn = 120;

function d_at(z) = cup_bottom_diameter + (cup_top_diameter - cup_bottom_diameter) * z / cup_height;

lip_h = base_lip > 0 ? 2.5 : 0;
r1 = d_at(0) / 2 + tolerance;
r2 = d_at(sleeve_height) / 2 + tolerance;
xa = min(r1, r2) + wall - 3;               // handle root starts inside the wall
xo = max(r1, r2) + wall + 1;               // finger opening starts outside the sleeve
xe = xo + handle_opening_w + handle_bar;   // outer edge of the handle
oh = max(sleeve_height - 2 * handle_bar, handle_opening_w + 5);
hh = oh + 2 * handle_bar;

module opening2d(w, h) hull() {             // rounded bottom, 45 deg pointed top
    translate([w / 2, w / 2]) circle(d = w);
    translate([w / 2, h - w * 0.707]) circle(d = w);
    translate([w / 2 - 0.5, h - 0.1]) square([1, 0.1]);
}

module handle2d() difference() {
    translate([xa, 0]) offset(r = 4) offset(delta = -4) square([xe - xa, hh]);
    translate([xo, handle_bar]) opening2d(handle_opening_w, oh);
}

module handle() rotate([90, 0, 0]) linear_extrude(height = handle_thickness, center = true) handle2d();

difference() {
    union() {
        cylinder(r1 = r1 + wall, r2 = r2 + wall, h = sleeve_height);
        for (i = [0 : handles - 1]) rotate([0, 0, i * 180]) handle();
    }
    // cup cavity
    translate([0, 0, lip_h]) cylinder(r1 = d_at(lip_h) / 2 + tolerance, r2 = r2, h = sleeve_height - lip_h + 0.01);
    translate([0, 0, sleeve_height]) cylinder(r = xe + 5, h = hh);   // trim handle above sleeve
    // hole in the base lip
    translate([0, 0, -1]) cylinder(r = max(r1 - base_lip, 5), h = lip_h + 2);
}
