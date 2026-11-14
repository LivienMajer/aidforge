// Button hook + zipper pull (Knoepfhilfe + Reissverschlusshilfe) - parametric, mm.
// One-handed dressing aid: push the loop through the buttonhole, catch the button
// in the loop and pull it back through. The small hook on the other end catches
// the hole / ring of a zipper pull. Thick built-up handle with finger grooves and
// a flat underside (does not roll away) - for weak grip, arthritis, tremor,
// stroke / hemiplegia (one hand only), limited finger dexterity.
// Printed lying on its flat side, no supports: the handle is cut flat before its
// surface gets steeper than 45 deg, loop and hooks lie flat on the bed (45 deg
// chamfers). Overall length is limited to 214 mm (handle is shortened if needed).

handle_length  = 100;  // length of the handle
grip_diameter  = 30;   // handle diameter
finger_grooves = 3;    // number of finger grooves (0 = smooth)
groove_depth   = 1.5;  // depth of the finger grooves
shaft_length   = 30;   // from the handle end to the button loop
loop_width     = 16;   // outer width of the button loop (must pass the buttonhole)
loop_length    = 34;   // outer length of the button loop
loop_bar       = 3;    // width of the loop wire
hook_thickness = 3.5;  // thickness of shaft, loop and zipper hook
zipper_hook    = 1;    // 1 = zipper-pull hook at the other end
zipper_gap     = 4;    // opening of the zipper hook (gap between shank and tip)

$fn = 64;

R    = grip_diameter / 2;
gd   = finger_grooves > 0 ? min(groove_depth, R / 4) : 0;
rmin = R - gd;
h    = 0.69 * rmin;                // axis height: flat cut before the surface gets steeper than 45 deg
t    = max(hook_thickness, 3);
c    = min(0.8, t / 4);            // edge chamfer of the flat parts
W    = max(loop_width, 12);
bar  = max(3, min(loop_bar, (W - 5) / 2));
LL   = max(loop_length, W + 4);
bw   = max(bar + 3, 6);            // shaft width at the loop
e    = min(6, R * 0.4);            // rounding of the handle ends
sl   = max(shaft_length, 5);

zw   = 3.5;                        // zipper hook wire width
zg   = max(zipper_gap, 1.5);
rc   = (zg + zw) / 2;              // centre-line radius of the hook bend
tz   = 12;                         // neck taper on the zipper side
S    = tz + 14;                    // bend centre, measured from the handle end
zlen = zipper_hook == 1 ? S + rc + zw / 2 : 0;

L    = max(40, min(handle_length, 214 - sl - LL - zlen));
xl   = L + sl;                     // back of the button loop

// ---- handle: polyhedron of round rings, cut flat at z = 0 -----------------
x0 = L * 0.2;
x1 = L * 0.8;
function groove(x) = (finger_grooves > 0 && x > x0 && x < x1)
    ? gd * (0.5 - 0.5 * cos(360 * finger_grooves * (x - x0) / (x1 - x0))) : 0;

n  = 40;                           // stations along the grooved part
M  = 40;                           // points per ring
st = concat(                       // [x, radius] stations, rounded ends
    [for (a = [0 : 10 : 90]) [e - e * cos(a), R - e + e * sin(a)]],
    [for (i = [1 : n - 1]) let(x = e + i * (L - 2 * e) / n) [x, R - groove(x)]],
    [for (a = [90 : -10 : 0]) [L - e + e * cos(a), R - e + e * sin(a)]]
);
NS = len(st);
function ring(x, r) = let(pc = max(acos(min(1, h / r)), 180 / M))
    [for (i = [0 : M - 1]) let(p = pc + i * (360 - 2 * pc) / (M - 1))
        [x, r * sin(p), h - r * cos(p)]];
hpts   = [for (j = [0 : NS - 1]) each ring(st[j][0], st[j][1])];
hfaces = concat(
    [[for (i = [0 : M - 1]) i]],
    [[for (i = [M - 1 : -1 : 0]) (NS - 1) * M + i]],
    [for (j = [0 : NS - 2], i = [0 : M - 1]) let(a = j * M, b = (j + 1) * M, i2 = (i + 1) % M)
        each [[a + i, b + i, b + i2], [a + i, b + i2, a + i2]]]
);

module handle() polyhedron(points = hpts, faces = hfaces, convexity = 6);

// slice of the handle cross-section (flat bottom), used for the tapered necks
module d_slice(xa) translate([xa, 0, 0]) rotate([90, 0, 90]) linear_extrude(height = 0.5)
    intersection() {
        translate([0, h]) circle(r = R - 0.2);
        translate([-R, 0]) square([2 * R, h + R]);
    }

// flat bar along x on the bed, long edges chamfered
module slab(xa, xb, wd) hull() {
    translate([xa, -wd / 2 + c, 0]) cube([xb - xa, wd - 2 * c, t]);
    translate([xa, -wd / 2, c]) cube([xb - xa, wd, t - 2 * c]);
}

// ---- swept flat wire (loop, zipper hook): chamfered section along a 2D path --
// path entries: [x, y, nx, ny, u0, u1] = point, in-plane normal, section from u0 to u1
function sec(u0, u1) = [[u0 + c, 0], [u1 - c, 0], [u1, c], [u1, t - c], [u1 - c, t], [u0 + c, t], [u0, t - c], [u0, c]];
function sweep_pts(path) = [for (p = path) each [for (q = sec(p[4], p[5])) [p[0] + p[2] * q[0], p[1] + p[3] * q[0], q[1]]]];
function sweep_faces(np, closed) = concat(
    [for (j = [0 : (closed ? np - 1 : np - 2)], i = [0 : 7])
        let(a = j * 8, b = ((j + 1) % np) * 8, i2 = (i + 1) % 8)
        each [[a + i, a + i2, b + i2], [a + i, b + i2, b + i]]],
    closed ? [] : [[for (i = [7 : -1 : 0]) i], [for (i = [0 : 7]) (np - 1) * 8 + i]]
);
module sweep(path, closed) polyhedron(points = sweep_pts(path), faces = sweep_faces(len(path), closed), convexity = 4);

// ---- button loop: rounded diamond, centre line = hull of 4 circles ---------
rho = bar / 2 + 1;                 // centre-line corner radius (inner corners r = 1)
ys  = W / 2 - bar / 2 - rho;
lc  = [[xl - 1 + bar / 2 + rho, 0], [xl + 0.55 * LL, -ys], [xl + LL - bar / 2 - rho, 0], [xl + 0.55 * LL, ys]];
function nang(p, q) = atan2(q[1] - p[1], q[0] - p[0]) - 90;
function arc_pts(i) = let(
        p = lc[(i + 3) % 4], q = lc[i], r = lc[(i + 1) % 4],
        a0 = nang(p, q), sp = (nang(q, r) - a0 + 720) % 360,
        m = max(1, ceil(sp / 12)))
    [for (k = [0 : m]) let(a = a0 + sp * k / m)
        [q[0] + rho * cos(a), q[1] + rho * sin(a), cos(a), sin(a), -bar / 2, bar / 2]];
loop_path = [for (i = [0 : 3]) each arc_pts(i)];

// ---- zipper hook: J shape, the tip points back towards the handle ----------
j_path = concat(
    [[-tz + 1, 0, 0, 1, -zw / 2, zw / 2]],                                     // shank (starts inside the neck)
    [for (a = [90 : 15 : 270]) [-S + rc * cos(a), -rc + rc * sin(a), cos(a), sin(a), -zw / 2, zw / 2]],
    [[-S + 8, -2 * rc, 0, -1, -zw / 2, -zw / 2 + 2]]                           // tapered tip
);

union() {
    hull() { d_slice(L - e - 0.5); slab(xl - 3, xl + 1, bw); }              // neck + shaft
    sweep(loop_path, true);                                                  // button loop
    if (zipper_hook == 1) {
        hull() { d_slice(e); slab(-tz - 1, -tz, zw); }                       // neck
        sweep(j_path, false);                                                // zipper hook
    }
    handle();
}
