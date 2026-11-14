// Plate guard (Tellerranderhoehung) - parametric, all dimensions in mm.
// Clip-on raised rim for a round plate: food can be pushed against the wall with
// one hand and is turned back by the inward lip - for stroke / hemiplegia,
// one-handed eating, tremor or poor coordination. C-clip over the plate edge: the
// lower jaw reaches under the plate (stops the wall tipping outwards), a 45 deg
// hook holds the plate edge down and a small bump at the jaw tip clamps it.
// Printed as used (lower jaw flat on the bed, wall up), no supports: the only
// overhangs (hook over the plate edge, underside of the lip) are 45 deg.
// The arc is shortened automatically if it would not fit a 220 x 220 mm bed.

plate_diameter = 260;  // outer diameter of the plate
rim_thickness  = 5;    // thickness of the plate edge the clip goes over
rim_slope      = 10;   // angle the plate rim rises towards its edge (deg, 0 = flat)
clip_depth     = 14;   // how far the lower jaw reaches under the plate, from the edge
grip_bump      = 1;    // bump at the jaw tip that clamps the plate (0 = none)
arc_angle      = 100;  // part of the plate edge covered by the guard (deg)
wall_height    = 30;   // wall height above the plate surface
wall_thickness = 3;    // wall / clip thickness
lip            = 5;    // inward lip at the top that turns food back (0 = none)
tolerance      = 0.3;  // clearance at the plate edge

$fn = 96;

R    = plate_diameter / 2 + tolerance;   // inner face of the clip spine (plate edge)
w    = max(wall_thickness, 2);
s    = rim_thickness + 2 * tolerance;    // slot height at the plate edge
cd   = max(clip_depth, 6);
jaw  = max(w, 3);                        // lower jaw thickness at its tip
ta   = tan(max(0, rim_slope));
zf0  = jaw + cd * ta;                    // slot floor at the spine
zc   = zf0 + s;                          // plate top surface at the edge
k    = 3;                                // 45 deg hook over the plate edge
H    = max(wall_height, 12);
ztop = zc + H;
tl   = 2;                                // lip tip thickness
lp   = max(0, min(lip, (H - k - tl - 2) / 2));
f    = min(1.5 * lp, 8);                 // cove between wall and lip
b    = max(0, min(grip_bump, (cd - 3) / 2, s / 2));
rr   = min(0.8, w / 2 - 0.3);            // rounding of convex edges

r_t  = R - cd;                           // jaw tip
r_wi = R - k;                            // wall inner face
r_wo = r_wi + w;                         // wall outer face
r_so = R + w;                            // spine outer face

function zf(r) = zf0 - (R - r) * ta;     // slot floor follows the rim slope

z9  = ztop - tl - lp;                    // lip underside meets the wall face
fcx = r_wi - f;
fcz = z9 - f * (sqrt(2) - 1);

pts = concat(
    [[r_t + 1, 0],                       // jaw tip, bottom chamfer
     [r_so - 1.5, 0],
     [r_so, 1.5],
     [r_so, zc + w],                     // outer face of the spine
     [r_wo, zc + w + k],                 // 45 deg step in to the wall
     [r_wo, ztop]],
    lp > 0.4
        ? concat([[r_wi - lp, ztop], [r_wi - lp, ztop - tl]],
                 [for (i = [0 : 8]) let(a = 45 - i * 45 / 8) [fcx + f * cos(a), fcz + f * sin(a)]])
        : [[r_wi, ztop]],
    [[r_wi, zc + k],                     // foot of the wall face / top of the hook
     [R, zc],                            // hook corner: the plate edge sits here
     [R, zf0]],                          // back of the slot
    b > 0.05 ? [[r_t + 2 + 2 * b, zf(r_t + 2 + 2 * b)], [r_t + 2, zf(r_t + 2) + b]] : [],
    [[r_t, zf(r_t) + 0.3 * b],
     [r_t, 1]]
);

module profile2d() offset(r = rr, $fn = 24) offset(delta = -rr) polygon(pts);

// shorten the arc so its chord fits the bed
A  = min(max(arc_angle, 20), 2 * asin(min(1, 107 / (r_so + 0.5))));

// wall slopes down at both ends (no sharp corners, food slides off)
zl   = zc + k + w + 2;
phi  = 35;
lt   = (ztop - zl) / tan(phi) + 3;
rmin = min(r_t, r_wi - lp) - 3;

module end_cut() intersection() {
    translate([rmin, -5, zl]) cube([r_so + 3 - rmin, lt + 5, ztop - zl + 5]);
    translate([0, 0, zl]) rotate([phi, 0, 0]) translate([-500, -500, 0]) cube([1000, 1000, 500]);
}

rotate([0, 0, -A / 2])
difference() {
    rotate_extrude(angle = A) profile2d();
    end_cut();
    rotate([0, 0, A]) mirror([0, 1, 0]) end_cut();
}
