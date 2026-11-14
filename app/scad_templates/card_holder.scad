// Playing card holder (Spielkartenhalter) - parametric, all dimensions in mm.
// Holds a hand of cards upright and slightly tilted so cards can be played with
// one hand, with weak grip or tremor. Print flat, no supports.

holder_length = 180;   // total length
holder_depth  = 55;    // front-to-back depth
holder_height = 28;    // height of the block
slots         = 2;     // 1 or 2 slot rows
slot_width    = 2.2;   // slot gap (more for thicker card stacks)
slot_depth    = 20;    // how deep the cards sit
slot_angle    = 12;    // backward tilt of the cards in degrees
end_margin    = 10;    // closed ends of the slots
corner_radius = 8;
chamfer       = 2;

$fn = 64;

c = min(chamfer, holder_height / 4);

module outline(off = 0)
    translate([-holder_length / 2, -holder_depth / 2])
        offset(r = corner_radius + off) offset(delta = -corner_radius)
            square([holder_length, holder_depth]);

module body() hull() {
    linear_extrude(height = holder_height) outline(-c);
    translate([0, 0, 0]) linear_extrude(height = holder_height - c) outline(0);
}

function row_y(i) = slots == 1 ? 0 : -holder_depth * 0.2 + i * holder_depth * 0.4;

difference() {
    body();
    for (i = [0 : slots - 1]) {
        sl = holder_length - 2 * end_margin;
        translate([-sl / 2, row_y(i), holder_height])
            rotate([-slot_angle, 0, 0]) {
                translate([0, -slot_width / 2, -slot_depth]) cube([sl, slot_width, slot_depth + 10]);
                // lead-in V at the top of the slot
                translate([0, 0, 0]) rotate([45, 0, 0]) translate([0, -2, -2]) cube([sl, 4, 4]);
            }
    }
}
