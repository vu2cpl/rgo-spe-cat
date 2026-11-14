// RGO ONE CAT + audio box — 3D-printed enclosure (OpenSCAD).
//
// Two parts: an open-top BASE (floor + walls + everything mounted) and a flat
// LID with a locating lip. 4 × M3 screws go down through the lid into M3
// heat-set inserts in the base corner posts.
//
// Layout (looking down, back wall at the bottom of the picture):
//
//     ┌───────────────────────────────────────────┐
//     │ ●                                       ● │
//     │   ┌──────┐                              ══ DB15 FEMALE  (SPE amp)
//     │   │  S3  │       [ CM108 dongle ]          │
//     │   │board │                              ══ DB15 MALE    (radio ACC1)
//     │   └──────┘        [ USB ext socket ]       │
//     │ ●   ▀▀▀▀                     ▀▀        ● │
//     └─────USB-C x2 ─────────────────── cable ────┘
//         (COM = power,                notch (PC)
//          native = radio)
//
// - S3 board: its two USB-C sockets poke into one slot in the back wall, so
//   the radio and charger cables plug straight into the board. It sits on a
//   rib between its header rows (foam tape), with a stop block behind it so
//   plugging a cable can't push it back.
// - CM108 dongle and the USB extension's socket: held down by zip-tie anchors.
// - PC cable leaves through a notch at the top of the back wall; the lid has a
//   tab that closes the notch down to cable size, so the USB-A plug never has
//   to pass through a hole.
// - Both DB15s on the right end wall, opposite genders (can't be swapped),
//   labelled RADIO and AMP. The wall is thinned around them so the jack
//   screws reach.
//
// Values marked CHECK are from datasheets / guesses: measure your parts and
// change them before printing. part = "assembly" shows ghost parts.

/* [Part] */
part = "assembly";   // [assembly, base, lid, print]

/* [Box] */
in_l   = 120;   // inner length (X)
in_d   = 100;   // inner depth (Y)
in_h   = 32;    // inner height, floor top to lid underside
wall   = 2.5;
floor_t = 2.4;
lid_t  = 2.4;
corner_r = 3;

/* [Lid fixing] */
post_d        = 8.5;
insert_hole_d = 4.0;   // M3 heat-set insert bore (CHECK your inserts)
insert_depth  = 6;
screw_d       = 3.4;   // M3 clearance in the lid
csk_d         = 6.4;   // countersink for an M3 flat head
lip_h         = 3;     // lid locating lip depth
lip_t         = 1.6;
lip_clear     = 0.3;

/* [ESP32-S3 board — VCC-GND YD-ESP32-S3] */
pcb_l     = 63.5;  // CHECK (published size 63.5 × 28)
pcb_w     = 28;    // CHECK
pcb_t     = 1.6;
pcb_x0    = 12;    // board's left edge from the inner left wall
pin_clear = 10;    // CHECK floor → board underside. Wires soldered to the pins: 8-10.
                   // Dupont jumpers on downward pins need ~20 (and raise in_h).
rib_w     = 8;     // support rib, between the header rows
usbc_slot_w = 27;  // one slot over both USB-C sockets (overmolds fit side by side)
usbc_slot_h = 7;
usbc_z_above_pcb = 1.6;  // socket centre above the board's top face (CHECK)

/* [Status LED window] */
led_window = true;
led_x = 14;        // CHECK LED position on the board, from the board's left edge
led_y = 12;        // CHECK ... from the board's USB end
led_d = 3.2;

/* [DB15 (DA-15, shell size A) on the right end wall] */
db_hole_pitch = 33.32;   // jack-screw hole spacing (standard)
db_hole_d     = 3.2;
db_cut_top    = 26.4;    // D cutout, wide edge (with clearance)
db_cut_h      = 10.6;
db_angle      = 10;      // D side angle
db_flange_w   = 39.1;
db_flange_h   = 12.6;
db_panel_t    = 1.6;     // wall thinned to this around each D (jack screws reach)
db_z          = 14;      // connector centre above the floor top
db_radio_y    = 27;      // DB15 MALE  → radio ACC1
db_amp_y      = 73;      // DB15 FEMALE → SPE amp

/* [PC cable notch, back wall] */
notch_x = 100;     // notch centre from the inner left wall
notch_w = 6.5;     // CHECK: your USB extension cable diameter + 1
notch_d = 12;      // notch depth from the top of the wall
cable_h = 6;       // hole left for the cable once the lid tab is in

/* [Zip-tie anchors] */
// [x, y, angle]: centre of each anchor on the floor; the tie runs across the anchor.
ties = [[60, 60, 0], [85, 60, 0], [95, 22, 0]];
tie_slot_w = 4.2;  // zip-tie width + clearance
tie_slot_h = 1.8;
tie_block  = [6, 12, 4];

$fn = 48;
eps = 0.01;

out_l = in_l + 2*wall;
out_d = in_d + 2*wall;
base_h = floor_t + in_h;
pcb_z  = floor_t + pin_clear;       // board underside
usbc_z = pcb_z + pcb_t + usbc_z_above_pcb;

// inner coordinates → base coordinates
function ix(x) = wall + x;
function iy(y) = wall + y;

post_c = post_d/2;
posts = [[post_c, post_c], [in_l - post_c, post_c],
         [post_c, in_d - post_c], [in_l - post_c, in_d - post_c]];

module rbox(l, d, h, r) {
    hull() for (x = [r, l - r], y = [r, d - r]) translate([x, y, 0]) cylinder(r = r, h = h);
}

// ---------- cutouts ----------
module dsub_cut(y) {
    bot = db_cut_top - 2 * db_cut_h * tan(db_angle);
    // through the wall
    translate([out_l - wall - 1, iy(y), floor_t + db_z]) rotate([90, 0, 90])
        linear_extrude(wall + 2) polygon([[-db_cut_top/2,  db_cut_h/2], [db_cut_top/2,  db_cut_h/2],
                                           [ bot/2,       -db_cut_h/2], [-bot/2,       -db_cut_h/2]]);
    for (s = [-1, 1])
        translate([out_l - wall - 1, iy(y) + s*db_hole_pitch/2, floor_t + db_z])
            rotate([0, 90, 0]) cylinder(d = db_hole_d, h = wall + 2);
    // thin the wall from inside around the connector
    translate([out_l - wall - eps, iy(y) - (db_flange_w + 4)/2, floor_t + db_z - (db_flange_h + 4)/2])
        cube([wall - db_panel_t + eps, db_flange_w + 4, db_flange_h + 4]);
}

module labels() {
    for (l = [[db_radio_y, "RADIO"], [db_amp_y, "AMP"]])
        translate([out_l - 0.6, iy(l[0]), floor_t + db_z + db_flange_h/2 + 5])
            rotate([90, 0, 90]) linear_extrude(1)
                text(l[1], size = 5, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    translate([ix(pcb_x0 + pcb_w/2), 0.6, usbc_z - usbc_slot_h/2 - 5])
        rotate([90, 0, 0]) linear_extrude(1)
            text("RIG    PWR", size = 3.5, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    translate([ix(notch_x), 0.6, base_h - notch_d - 5])
        rotate([90, 0, 0]) linear_extrude(1)
            text("PC", size = 4, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}

module usbc_slot() {
    translate([ix(pcb_x0 + pcb_w/2), -1, usbc_z]) rotate([-90, 0, 0])
        hull() for (s = [-1, 1]) translate([s*(usbc_slot_w - usbc_slot_h)/2, 0, 0])
            cylinder(d = usbc_slot_h, h = wall + 2);
}

module notch() {
    translate([ix(notch_x) - notch_w/2, -1, base_h - notch_d]) cube([notch_w, wall + 2, notch_d + 1]);
}

// ---------- base ----------
module tie_anchor(t) {
    translate([ix(t[0]), iy(t[1]), floor_t - eps]) rotate([0, 0, t[2]])
        difference() {
            translate([-tie_block[0]/2, -tie_block[1]/2, 0]) cube(tie_block);
            translate([-tie_block[0]/2 - 1, -tie_slot_w/2, 1]) cube([tie_block[0] + 2, tie_slot_w, tie_slot_h]);
        }
}

module base() {
    difference() {
        union() {
            difference() {
                rbox(out_l, out_d, base_h, corner_r);
                translate([wall, wall, floor_t]) cube([in_l, in_d, in_h + 1]);
            }
            // corner posts
            for (p = posts) translate([ix(p[0]), iy(p[1]), 0]) cylinder(d = post_d, h = base_h);
            // board support rib (stops short of the back wall: sockets overhang there)
            translate([ix(pcb_x0 + pcb_w/2 - rib_w/2), iy(6), 0]) cube([rib_w, pcb_l - 12, pcb_z]);
            // stop block behind the board's far end
            translate([ix(pcb_x0 + pcb_w/2 - 6), iy(pcb_l + 0.4), 0]) cube([12, 4, pcb_z + pcb_t + 2]);
            for (t = ties) tie_anchor(t);
        }
        for (p = posts) translate([ix(p[0]), iy(p[1]), base_h - insert_depth]) cylinder(d = insert_hole_d, h = insert_depth + 1);
        usbc_slot();
        notch();
        dsub_cut(db_radio_y);
        dsub_cut(db_amp_y);
        labels();
    }
}

// ---------- lid (modelled in place, sitting on the base) ----------
module lid() {
    lip_in = lip_clear;
    difference() {
        union() {
            translate([0, 0, base_h]) rbox(out_l, out_d, lid_t, corner_r);
            // locating lip just inside the walls
            translate([0, 0, base_h - lip_h]) difference() {
                translate([wall + lip_in, wall + lip_in, 0]) cube([in_l - 2*lip_in, in_d - 2*lip_in, lip_h + eps]);
                translate([wall + lip_in + lip_t, wall + lip_in + lip_t, -1]) cube([in_l - 2*(lip_in + lip_t), in_d - 2*(lip_in + lip_t), lip_h + 2]);
            }
            // tab that closes the cable notch down to cable size
            translate([ix(notch_x) - notch_w/2 + 0.2, 0, base_h - (notch_d - cable_h)])
                cube([notch_w - 0.4, wall + lip_in + lip_t, notch_d - cable_h + eps]);
        }
        // clear the lip around the posts
        for (p = posts) translate([ix(p[0]), iy(p[1]), base_h - lip_h - 1]) cylinder(d = post_d + 2*lip_clear + 0.4, h = lip_h + 1);
        // screw holes, countersunk from the top
        for (p = posts) translate([ix(p[0]), iy(p[1]), base_h - 1]) {
            cylinder(d = screw_d, h = lid_t + 2);
            translate([0, 0, 1 + lid_t - (csk_d - screw_d)/2]) cylinder(d1 = screw_d, d2 = csk_d, h = (csk_d - screw_d)/2 + eps);
        }
        if (led_window)
            translate([ix(pcb_x0 + led_x), iy(led_y), base_h - 1]) cylinder(d = led_d, h = lid_t + 2);
    }
}

// ---------- ghosts ----------
module ghosts() {
    // S3 board
    %translate([ix(pcb_x0), iy(0), pcb_z]) cube([pcb_w, pcb_l, pcb_t]);
    // CM108 dongle (CHECK ~ 50 × 20 × 10 incl. USB plug) + extension socket
    %translate([ix(48), iy(55), floor_t + 4]) cube([50, 20, 10]);
    %translate([ix(80), iy(15), floor_t + 4]) cube([30, 14, 8]);
    // DB15 flanges outside the end wall
    for (y = [db_radio_y, db_amp_y])
        %translate([out_l, iy(y) - db_flange_w/2, floor_t + db_z - db_flange_h/2]) cube([1, db_flange_w, db_flange_h]);
}

echo(str("Outer size: ", out_l, " × ", out_d, " × ", base_h + lid_t, " mm"));
assert(db_amp_y - db_radio_y >= db_flange_w + 2, "DB15 flanges overlap");
assert(db_z + db_flange_h/2 <= in_h - lip_h, "DB15 hits the lid lip");
assert(pcb_x0 >= post_d, "board clashes with a corner post");

if (part == "assembly") {
    base();
    color("SteelBlue", 0.35) translate([0, 0, 8]) lid();
    ghosts();
} else if (part == "base") {
    base();
} else if (part == "lid") {
    translate([0, out_d, base_h + lid_t]) rotate([180, 0, 0]) lid();
} else if (part == "print") {
    base();
    translate([0, 2*out_d + 10, base_h + lid_t]) rotate([180, 0, 0]) lid();
}
