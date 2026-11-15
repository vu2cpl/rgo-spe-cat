// RGO ONE CAT + audio box — 3D-printed enclosure (OpenSCAD).
//
// Two parts: an open-top BASE (floor + walls + everything mounted) and a flat
// LID with a locating lip. 4 × M3 screws go down through the lid into M3
// heat-set inserts in the base corner posts.
//
// Layout (looking down). All connectors are on the front panel; only the
// PC cable leaves through a notch in the back wall, straight behind the dongle:
//
//     ┌──────────────────┤PC├─────────────────────┐
//     │ ●                                       ● │
//     │                [ ext  ]                   │
//     │   ┌──────┐     [socket]                   │
//     │   │  S3  │     [CM108 ]                   │
//     │   │board │     [dongle]                   │
//     │ ● └──────┘     [      ]                 ● │
//     └───USB-C x2─────IN──OUT───AMP────────────┘
//        RIG  PWR     1/8" jacks  2.5mm
//
// - S3 board: its two USB-C sockets poke into one slot, so the radio and
//   charger cables plug straight into the board. Held without tape: rib
//   below, stop block behind, corner fences at the sides, lid fingers above.
// - CM108 dongle: its jack end sits in a panel window, flush with the
//   outside, so 1/8" plugs seat fully; stop posts behind its body. The radio
//   cable (DB15 plug on ACC1, resistors in its hood, two 1/8" plugs) plugs in
//   there. A zip tie through the cradle holds it. The USB extension socket
//   sits behind it on a zip-tie anchor.
// - AMP: a 2.5 mm stereo (TRS) panel jack — the amp needs only 3 wires. A
//   different size from the 1/8" audio jacks, so the cables can't be mixed
//   up. Amp cable: 2.5 mm TRS plug → DB15 male (amp).
// - PC cable runs straight back from the extension socket and leaves
//   through a notch at the top of the BACK wall, so no U-turn is needed and
//   longer socket housings fit. A lid tab closes the notch to cable size.
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
pcb_l     = 63.5;  // measured, including the antenna end
pcb_w     = 28;    // measured
pcb_t     = 1.6;
pcb_x0    = 9;     // board's left edge from the inner left wall
pin_clear = 12;    // floor → board underside. Wires are soldered to the header pins;
                   // 12 clears downward headers (~8.5) plus the solder joints.
rib_w     = 8;     // support rib, between the header rows
usbc_slot_w = 27;  // one slot over both USB-C sockets (overmolds fit side by side)
usbc_slot_h = 7;   // proven: USB-C plugs seat fully in the draft-6 test fit
// Board retention: no foam tape. Rib below, wall in front, stop block behind,
// four corner fences at the sides, and two lid fingers pressing down from above.
fence_t     = 1.6;   // corner fence thickness
fence_l     = 5;     // corner fence length along the board edge
fence_clear = 0.3;   // gap between fence and board edge
module_h    = 3.2;   // ESP32-S3 module shield height above the board top (confirmed)
press_y     = 46;    // (confirmed) lid press point on the module shield, from the board's USB end
press_d     = 6;
press_gap   = 0.3;   // gap between lid fingers and the parts they press on
usbc_h      = 3.1;   // USB-C socket height above the board top (measured)
usbc_bar_l  = 4.5;   // lid bar over the USB-C socket shells, from the inner wall
usbc_z_above_pcb = 1.55; // socket centre above the board's top face (measured: 3.1 tall)

/* [Status LED window] */
led_window = true;
// The RGB LED (a small square part) is 23 mm from the board's USB end
// (measured 2026-11-15). The window is a slot across the board there, so it
// shows the LED wherever it sits across the width.
led_x = 14;        // slot centre, from the board's left edge
led_y = 23;        // slot centre, from the board's USB end (measured)
led_d = 3.2;       // slot width
led_slot_l = 18;   // slot length, across the board

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
// The dongle's jack end sits in a window in the panel, flush with the outside,
// so any 1/8" plug seats fully. Stop posts behind its body take the push.
dongle_proud = 0;    // how far the jack face stands out from the panel (0 = flush)
dongle_body = 29;    // body length, jack end to the USB plug shoulder
usb_plug_w  = 12;    // width of the dongle's USB-A plug
ext_sock_w  = 18;    // CHECK: width of the USB extension's socket housing
window_clear = 0.3;  // clearance around the dongle in the panel window
pad_h       = 4;     // cradle floor the dongle sits on (zip tie runs through it)
rail_t      = 2;     // cradle side rails
cradle_clear = 0.4;

/* [AMP jack — 2.5 mm TRS, panel mount] */
amp_jack_x      = 80;    // centre, from the inner left wall
amp_jack_hole_d = 6.2;   // jack thread measured ~5.8 mm
amp_jack_body   = 11;    // CHECK width of the jack body behind the panel

/* [PC cable notch, back wall] */
// As cut on the draft-6 box (2026-11-15): 6 wide × 14 deep, behind the dongle.
notch_x = dongle_x; // notch centre from the inner left wall (in line with the dongle)
notch_w = 6;       // USB extension cable diameter + clearance
notch_d = 14;      // notch depth from the top of the wall
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
dongle_y0 = -wall - dongle_proud;   // dongle jack face, inner coordinates
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
    panel_text(in_jack_x,  floor_t + pad_h + dongle_h + window_clear + 3.2, "IN", 3.2);
    panel_text(out_jack_x, floor_t + pad_h + dongle_h + window_clear + 3.2, "OUT", 3.2);
    panel_text(pcb_x0 + pcb_w/2, usbc_z - usbc_slot_h/2 - 4, "RIG    PWR", 3.5);
    // "PC" on the outside of the back wall, below the notch
    translate([ix(notch_x), out_d - 0.6, base_h - notch_d - 5]) rotate([90, 0, 180]) linear_extrude(1)
        text("PC", size = 4, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
}

module usbc_slot() {
    translate([ix(pcb_x0 + pcb_w/2), -1, usbc_z]) rotate([-90, 0, 0])
        hull() for (s = [-1, 1]) translate([s*(usbc_slot_w - usbc_slot_h)/2, 0, 0])
            cylinder(d = usbc_slot_h, h = wall + 2);
}

module jack_holes() {
    // window the dongle's jack end fits into
    translate([ix(dongle_x - dongle_w/2 - window_clear), -1, floor_t + pad_h - eps])
        cube([dongle_w + 2*window_clear, wall + 2, dongle_h + window_clear + eps]);
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
    // stop posts behind the dongle body, either side of its USB plug: a plug
    // pushed into a jack can't shove the dongle back into the box
    for (sx = [-1, 1])
        translate([ix(dongle_x + sx*(dongle_w/2 - 2) - 2), iy(dongle_y0 + dongle_body + 0.3), floor_t - eps])
            cube([4, 3, pad_h + dongle_h*0.8]);
}

module notch() {
    translate([ix(notch_x) - notch_w/2, out_d - wall - 1, base_h - notch_d]) cube([notch_w, wall + 2, notch_d + 1]);
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
            // corner fences: hold the board sideways at both ends
            for (fx = [pcb_x0 - fence_clear - fence_t, pcb_x0 + pcb_w + fence_clear],
                 fy = [0, pcb_l - fence_l])
                translate([ix(fx), iy(fy), 0]) cube([fence_t, fence_l, pcb_z + pcb_t + 1.5]);
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
            // fingers that press the S3 board down onto its rib
            translate([ix(pcb_x0 + pcb_w/2), iy(press_y), pcb_z + pcb_t + module_h + press_gap])
                cylinder(d = press_d, h = base_h - (pcb_z + pcb_t + module_h + press_gap) + eps);
            translate([ix(pcb_x0 + 2), iy(lip_in + lip_t), pcb_z + pcb_t + usbc_h + press_gap])
                cube([pcb_w - 4, usbc_bar_l - lip_in - lip_t, base_h - (pcb_z + pcb_t + usbc_h + press_gap) + eps]);
            // tab that closes the cable notch down to cable size
            translate([ix(notch_x) - notch_w/2 + 0.2, out_d - wall - lip_in - lip_t, base_h - (notch_d - cable_h)])
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
            translate([ix(pcb_x0 + led_x), iy(led_y), base_h - 1])
                hull() for (sx = [-1, 1]) translate([sx*(led_slot_l - led_d)/2, 0, 0]) cylinder(d = led_d, h = lid_t + 2);
    }
}

// ---------- ghosts ----------
module ghosts() {
    // S3 board
    %translate([ix(pcb_x0), iy(0), pcb_z]) cube([pcb_w, pcb_l, pcb_t]);
    // CM108 dongle in its cradle + the extension socket behind it
    %translate([ix(dongle_x - dongle_w/2), iy(dongle_y0), floor_t + pad_h]) cube([dongle_w, dongle_body, dongle_h]);
    %translate([ix(dongle_x - usb_plug_w/2), iy(dongle_y0 + dongle_body), floor_t + pad_h + 3]) cube([usb_plug_w, dongle_l - dongle_body, 4.5]);
    %translate([ix(dongle_x - ext_sock_w/2), iy(dongle_y0 + dongle_l - 12), floor_t + pad_h + 1]) cube([ext_sock_w, 26, 8]);
    // AMP jack body behind the panel
    %translate([ix(amp_jack_x - amp_jack_body/2), iy(0), jack_zabs - amp_jack_body/2]) cube([amp_jack_body, 14, amp_jack_body]);
}

echo(str("Outer size: ", out_l, " × ", out_d, " × ", base_h + lid_t, " mm"));
assert(dongle_x - cradle_w/2 - rail_t >= pcb_x0 + pcb_w + 3, "dongle cradle hits the S3 board");
assert(dongle_x - cradle_w/2 - rail_t >= pcb_x0 + pcb_w/2 + usbc_slot_w/2 + 3, "jack holes crowd the USB-C slot");
assert(amp_jack_x - amp_jack_body/2 >= dongle_x + cradle_w/2 + rail_t + 1, "AMP jack hits the dongle cradle");
assert(dongle_y0 + dongle_l + 22 <= in_d, "no room behind the dongle for the extension socket");
assert(ext_sock_w/2 <= dongle_w/2 - 4 - 0.5, "extension socket hits the dongle stop posts");
assert(usbc_slot_w/2 + pcb_x0 + pcb_w/2 <= dongle_x - dongle_w/2 - window_clear - 3, "USB-C slot crowds the dongle window");
assert(notch_x - notch_w/2 >= post_d && notch_x + notch_w/2 <= in_l - post_d, "cable notch hits a corner post");
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
