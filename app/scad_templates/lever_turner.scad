// Lever turner (Dreh- und Deckelhilfe) - parametric, all dimensions in mm.
// Ribbed cap that slides over a round jar lid, bottle cap, tap handle or knob and
// adds one or two long levers - turning needs far less grip and wrist force.
// Printed with the top plate on the bed, cavity facing up, no supports.

object_diameter = 70;   // diameter of the lid / knob / tap to grip
grip_depth      = 12;   // how far the cap slides over the object
wall            = 4;    // ring wall thickness
top_thickness   = 3;    // closed top plate (0 = open ring, e.g. for taps with a shaft)
lever_length    = 110;  // from the centre to the lever tip
lever_width     = 26;   // lever width
lever_height    = 15;   // lever thickness
levers          = 1;    // 1 = single lever, 2 = T-handle for two hands
rib_count       = 30;   // grip ribs inside the cap
rib_depth       = 1.0;  // how far the ribs protrude inwards
hang_hole       = 1;    // 1 = small hole at the lever tip to hang it up
tolerance       = 0.5;

$fn = 96;

Dc = object_diameter + 2 * tolerance;
Do = Dc + 2 * wall;
H  = top_thickness + grip_depth;
lh = max(lever_height, 4);
c  = 1.5;
LL = max(lever_length, Do / 2 + lever_width);

module lever2d(off = 0) hull() {
    circle(d = lever_width + 2 * off);
    translate([LL - lever_width / 2, 0]) circle(d = lever_width + 2 * off);
}

module lever() difference() {
    hull() {
        linear_extrude(height = lh) lever2d(-c);
        translate([0, 0, c]) linear_extrude(height = lh - 2 * c) lever2d(0);
    }
    if (hang_hole == 1) translate([LL - lever_width / 2, 0, -1]) cylinder(d = 8, h = lh + 2);
}

module ribs()
    for (i = [0 : rib_count - 1])
        rotate([0, 0, i * 360 / rib_count])
            translate([Dc / 2, 0, top_thickness + H / 2])
                rotate([0, 0, 45]) cube([rib_depth * sqrt(2), rib_depth * sqrt(2), H], center = true);

union() {
    difference() {
        union() {
            cylinder(d = Do, h = H);
            for (i = [0 : levers - 1]) rotate([0, 0, i * 180]) lever();
        }
        // cavity for the object
        translate([0, 0, top_thickness > 0 ? top_thickness : -1]) cylinder(d = Dc, h = H + lh + 2);
        // lead-in chamfer at the opening
        translate([0, 0, H - 1.5]) cylinder(d1 = Dc, d2 = Dc + 3, h = 1.51);
    }
    intersection() {
        ribs();
        translate([0, 0, top_thickness]) cylinder(d = Dc + 0.1, h = grip_depth - 1.5);
    }
}
