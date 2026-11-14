// Key turner (Schluesseldreher) - parametric, all dimensions in mm.
// Large lever handle that holds a key, so turning it needs much less pinch force
// and wrist rotation (arthritis, weak pinch grip, tremor). Key is fixed with an
// M3 bolt + nut through the key's hole, or glued. Print flat, no supports.

key_bow_width     = 24;   // width of the key head (bow)
key_bow_length    = 22;   // length of the key head that goes into the handle
key_bow_thickness = 2.5;  // thickness of the key head
lever_length      = 85;   // total length of the turner
lever_width       = 50;   // width of the wide grip end
thickness         = 14;   // thickness of the handle
finger_hole       = 1;    // 1 = finger hole in the grip end
finger_hole_d     = 24;   // finger hole diameter
bolt_hole         = 1;    // 1 = M3 bolt hole + nut trap to fix the key
bolt_offset       = 11;   // distance of the bolt hole from the slot opening
chamfer           = 2;    // edge chamfer
tolerance         = 0.3;

$fn = 72;

kw     = key_bow_width + 2 * tolerance;
kt     = key_bow_thickness + 2 * tolerance;
neck_w = kw + 8;
neck_l = key_bow_length + 6;
L      = max(lever_length, neck_l + lever_width / 2 + 5);
c      = min(chamfer, thickness / 4);

module outline(off = 0) hull() {
    translate([0, L - lever_width / 2]) circle(d = lever_width + 2 * off);
    translate([-(neck_w / 2 + off), 0]) square([neck_w + 2 * off, neck_l]);
}

module body() hull() {
    linear_extrude(height = thickness) outline(-c);
    translate([0, 0, c]) linear_extrude(height = thickness - 2 * c) outline(0);
}

difference() {
    body();
    // key slot
    translate([-kw / 2, -1, (thickness - kt) / 2]) cube([kw, key_bow_length + 1, kt]);
    // finger hole
    if (finger_hole == 1)
        translate([0, L - lever_width / 2, -1])
            cylinder(d = min(finger_hole_d, lever_width - 12), h = thickness + 2);
    // M3 bolt + nut trap
    if (bolt_hole == 1) {
        translate([0, bolt_offset, -1]) cylinder(d = 3.4, h = thickness + 2);
        translate([0, bolt_offset, -1]) cylinder(d = 6.6, h = 3.6, $fn = 6);
        translate([0, bolt_offset, thickness - 2.6]) cylinder(d = 6.2, h = 3);
    }
}
