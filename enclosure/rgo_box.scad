// RGO ONE CAT + audio box — 3D-printed enclosure (OpenSCAD).
//
// Two parts: an open-top BASE (floor + walls + everything mounted) and a flat
// LID with a locating lip. 4 × M3 screws go down through the lid into M3
// heat-set inserts in the base corner posts.
//
// Layout (looking down). ALL connectors are on ONE panel — the back wall:
//
//     ┌───────────────────────────────────────────┐
//     │ ●                                       ● │
//     │                [ ext  ]                   │
//     │   ┌──────┐     [socket]                   │
//     │   │  S3  │     [CM108 ]                   │
//     │   │board │     [dongle]                   │
//     │ ● └──────┘     [      ]                 ● │
//     └───USB-C x2─────IN──OUT───AMP───cable──┘
//        RIG  PWR     1/8" jacks  2.5mm  PC notch
//
// - S3 board: its two USB-C sockets poke into one slot, so the radio and
//   charger cables plug straight into the board. It sits on a rib between
//   its header rows (foam tape), with a stop block behind it so plugging a
//   cable can't push it back.
// - CM108 dongle: lies in a cradle with its jack end against the panel; its
//   own mic (IN) and headphone (OUT) jacks show through two holes. The radio
//   cable (DB15 plug on ACC1, resistors in its hood, two 1/8" plugs) plugs in
//   there. A zip tie through the cradle holds it. The USB extension socket
//   sits behind it on a zip-tie anchor.
// - AMP: a 2.5 mm stereo (TRS) panel jack — the amp needs only 3 wires. A
//   different size from the 1/8" audio jacks, so the cables can't be mixed
//   up. Amp cable: 2.5 mm TRS plug → DB15 male (amp).
// - PC cable leaves through a notch at the top of the panel; the lid has a
//   tab that closes it down to cable size, so the USB-A plug never has to
//   pass through a hole.
//
// Values marked CHECK are from datasheets / guesses: measure your parts and
// change them before printing. part = "assembly" shows ghost parts.

/* [Part] */
part = "assembly";   // [assembly, base, lid, print]

/* [Box] */
in_l   = 102;   // inner length (X), along the connector panel
in_d   = 70;    // inner depth (Y)
in_h   = 23;    // inner height, floor top to lid underside
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
pcb_x0    = 9;     // board's left edge from the inner left wall
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

/* [USB audio dongle — jacks through the panel] */
// Measured 2026-11-14 (black aluminium "USB Audio Adapter"): body 28 × 29 ×
// 11.3 mm + USB-A plug 14 long. Jack openings: 16.6 outer-to-outer, 8.2
// inner-to-inner (→ 12.4 pitch); lower edge 4.6 from the bottom, upper edge
// 3.2 from the top (→ centre 6.35 up). Pink mic on the left at the jack end.
dongle_x    = 56.5;  // dongle centre line, from the inner left wall
dongle_l    = 43;    // length, jack end to the end of its USB plug (29 + 14)
dongle_w    = 28;    // width
dongle_h    = 11.3;  // height
jack_pitch  = 12.4;  // centre-to-centre of its two 1/8" jacks
jack_z      = 6.35;  // jack centre above the dongle's underside
mic_left    = true;  // mic jack on the LEFT seen from outside the panel
jack_hole_d = 8;     // fits a 1/8" plug's body through the wall
pad_h       = 4;     // cradle floor the dongle sits on (zip tie runs through it)
rail_t      = 2;     // cradle side rails
cradle_clear = 0.4;

/* [AMP jack — 2.5 mm TRS, panel mount] */
amp_jack_x      = 80;    // centre, from the inner left wall
amp_jack_hole_d = 6.2;   // CHECK your jack's thread (usually M6 for a panel jack)
amp_jack_body   = 11;    // CHECK width of the jack body behind the panel

/* [PC cable notch, back wall] */
notch_x = 90;     // notch centre from the inner left wall
notch_w = 6.5;     // CHECK: your USB extension cable diameter + 1
notch_d = 12;      // notch depth from the top of the wall
cable_h = 6;       // hole left for the cable once the lid tab is in

/* [Zip-tie anchors] */
// [x, y, angle]: centre of each anchor on the floor; the tie runs across the anchor.
// Default: one for the USB extension socket, behind the dongle.
ties = [[56.5, 56, 0]];
tie_slot_w = 4.2;  // zip-tie width + clearance
tie_slot_h = 1.8;
tie_block  = [12, 8, 4];   // same height as the dongle cradle floor

$fn = 48;
eps = 0.01;

out_l = in_l + 2*wall;
out_d = in_d + 2*wall;
base_h = floor_t + in_h;
pcb_z  = floor_t + pin_clear;       // board underside
usbc_z = pcb_z + pcb_t + usbc_z_above_pcb;
jack_zabs = floor_t + pad_h + jack_z;
in_jack_x  = dongle_x + (mic_left ? -1 : 1) * jack_pitch/2;
out_jack_x = dongle_x - (mic_left ? -1 : 1) * jack_pitch/2;
cradle_w = dongle_w + 2*cradle_clear;

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
module panel_text(x, z, t, sz = 4) {
    translate([ix(x), 0.6, z]) rotate([90, 0, 0]) linear_extrude(1)
        text(t, size = sz, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}

module labels() {
    panel_text(amp_jack_x, jack_zabs + amp_jack_hole_d/2 + 4, "AMP", 3.5);
    panel_text(in_jack_x,  jack_zabs + jack_hole_d/2 + 4, "IN", 3.5);
    panel_text(out_jack_x, jack_zabs + jack_hole_d/2 + 4, "OUT", 3.5);
    panel_text(pcb_x0 + pcb_w/2, usbc_z - usbc_slot_h/2 - 4, "RIG    PWR", 3.5);
    panel_text(notch_x, base_h - notch_d - 5, "PC");
}

module usbc_slot() {
    translate([ix(pcb_x0 + pcb_w/2), -1, usbc_z]) rotate([-90, 0, 0])
        hull() for (s = [-1, 1]) translate([s*(usbc_slot_w - usbc_slot_h)/2, 0, 0])
            cylinder(d = usbc_slot_h, h = wall + 2);
}

module jack_holes() {
    for (x = [in_jack_x, out_jack_x])
        translate([ix(x), -1, jack_zabs]) rotate([-90, 0, 0]) cylinder(d = jack_hole_d, h = wall + 2);
    translate([ix(amp_jack_x), -1, jack_zabs]) rotate([-90, 0, 0]) cylinder(d = amp_jack_hole_d, h = wall + 2);
}

// Dongle cradle: a floor pad with a zip-tie tunnel across it, and side rails.
module cradle() {
    translate([ix(dongle_x - cradle_w/2), iy(0), floor_t - eps]) difference() {
        cube([cradle_w, dongle_l, pad_h]);
        translate([-1, dongle_l/2 - tie_slot_w/2, 1]) cube([cradle_w + 2, tie_slot_w, tie_slot_h]);
    }
    for (sx = [-1, 1])
        translate([ix(dongle_x + sx*(cradle_w/2 + rail_t/2) - rail_t/2), iy(0), floor_t - eps])
            difference() {
                cube([rail_t, dongle_l, pad_h + dongle_h*0.6]);
                translate([-1, dongle_l/2 - tie_slot_w/2, 1]) cube([rail_t + 2, tie_slot_w, tie_slot_h]);
            }
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
            cradle();
            for (t = ties) tie_anchor(t);
        }
        for (p = posts) translate([ix(p[0]), iy(p[1]), base_h - insert_depth]) cylinder(d = insert_hole_d, h = insert_depth + 1);
        usbc_slot();
        notch();
        jack_holes();
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
    // CM108 dongle in its cradle + the extension socket behind it
    %translate([ix(dongle_x - dongle_w/2), iy(0), floor_t + pad_h]) cube([dongle_w, dongle_l, dongle_h]);
    %translate([ix(dongle_x - 7), iy(dongle_l - 10), floor_t + pad_h]) cube([14, 24, 8]);
    // AMP jack body behind the panel
    %translate([ix(amp_jack_x - amp_jack_body/2), iy(0), jack_zabs - amp_jack_body/2]) cube([amp_jack_body, 14, amp_jack_body]);
}

echo(str("Outer size: ", out_l, " × ", out_d, " × ", base_h + lid_t, " mm"));
assert(dongle_x - cradle_w/2 - rail_t >= pcb_x0 + pcb_w + 3, "dongle cradle hits the S3 board");
assert(dongle_x - cradle_w/2 - rail_t >= pcb_x0 + pcb_w/2 + usbc_slot_w/2 + 3, "jack holes crowd the USB-C slot");
assert(amp_jack_x - amp_jack_body/2 >= dongle_x + cradle_w/2 + rail_t + 1, "AMP jack hits the dongle cradle");
assert(dongle_l + 22 <= in_d, "no room behind the dongle for the extension socket");
assert(notch_x - notch_w/2 >= amp_jack_x + amp_jack_body/2 + 1, "cable notch hits the AMP jack");
assert(notch_x + notch_w/2 <= in_l - post_d, "cable notch hits a corner post");
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
