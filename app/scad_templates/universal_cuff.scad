// Universal cuff (Universalmanschette) - parametric, all dimensions in mm.
// C-shaped band around the palm with a pocket that holds a spoon, fork, pen or
// toothbrush - for people who cannot close their hand (e.g. tetraplegia C5/C6,
// severe arthritis, stroke). Print flat (band width = Z), PETG or TPU recommended.

palm_width      = 85;   // palm width across the knuckles (MCP joints)
hand_thickness  = 30;   // hand thickness palm-to-back at the knuckles
band_width      = 28;   // width of the band along the hand
wall            = 3;    // band wall thickness
opening         = 24;   // gap on the thumb side to slip the hand in
holder_diameter = 12;   // diameter of the utensil handle that goes into the pocket
holder_length   = 50;   // length of the utensil pocket
holder_wall     = 3;    // wall around the pocket
holder_offset   = 0;    // shift pocket along the palm width (+ = towards thumb side)
tolerance       = 0.4;

$fn = 96;

a  = palm_width / 2 + tolerance;
b  = hand_thickness / 2 + tolerance;
hd = holder_diameter + 2 * tolerance;
ho = hd + 2 * holder_wall;
H  = max(band_width, ho);

module ellipse(rx, ry) scale([rx, ry]) circle(r = 1);

module band2d()
    offset(r = 1) offset(delta = -1)
    difference() {
        ellipse(a + wall, b + wall);
        ellipse(a, b);
        translate([a - 2 * wall, -opening / 2]) square([5 * wall, opening]);
    }

y_face = -(b + wall);               // outermost palm-side point of the band

difference() {
    union() {
        linear_extrude(height = H) band2d();
        // pocket block on the palm side
        translate([holder_offset - holder_length / 2, y_face - ho, 0])
            cube([holder_length, ho - y_face, H]);
    }
    // keep the hand cavity clean
    translate([0, 0, -1]) linear_extrude(height = H + 2) ellipse(a, b);
    // utensil pocket (horizontal, along the palm width)
    translate([holder_offset - holder_length / 2 - 1, y_face - ho / 2, H / 2])
        rotate([0, 90, 0]) cylinder(d = hd, h = holder_length + 2);
}
