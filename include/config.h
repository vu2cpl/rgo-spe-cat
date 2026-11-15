#pragma once

// ============================================================
//  RGO ONE SPE CAT Server — config
//  Non-secret build config. Real credentials live in secrets.h
//  (git-ignored) — see secrets.h.example.
// ============================================================

#define HOSTNAME  "rgo-spe-cat"

// ── WiFi onboarding (WiFiManager captive portal) ──────────
// No compile-time SSID/password. First boot — or whenever the saved network is
// unreachable — the node opens AP vu2cpl-rgo-spe-cat-setup. Join it, pick your
// network, enter its password; creds persist in NVS.
#define WIFI_AP_NAME           "vu2cpl-rgo-spe-cat-setup"
#define WIFI_AP_PASS           "vu2cpl1234"
#define WIFI_PORTAL_TIMEOUT_S  180

// ── Radio link: RGO ONE over USB host ─────────────────────
// Measured 2026-11-14 on the Mac: the radio's USB-B socket is an FTDI FT232R
// (VID 0x0403, PID 0x6001). CAT answers at 19200 8N1, TS-480-style Kenwood
// (FA; / IF; work, ID; gets no reply).
#define RADIO_USB_VID      0x0403
#define RADIO_USB_PID      0x6001
#define RADIO_BAUD         19200
#define RADIO_POLL_MS      150     // IF; poll interval
#define RADIO_REPLY_MS     200     // max wait for a ';'-terminated reply
#define RADIO_STALE_MS     1500    // no good reply for this long → rig state invalid

// ── SPE amplifier: Kenwood emulation on UART1 (direct TTL) ─
// Expert 1.5K-FA, DB15 CAT connector (manual rev 3.2 §12.1/12.3): 5 V TTL
// Kenwood, pin 11 (KEN TTL) tied to GND. Amp baud: SET → CAT → KENWOOD →
// baud (manual: "almost always 9600"); power-cycle the amp after changing it.
#define SPE_UART_NUM       1
#define SPE_TX_PIN         17      // S3 TX → DB15 pin 10 (RX TTL)
#define SPE_RX_PIN         18      // DB15 pin 3 (TX TTL, 5 V!) → divider → S3 RX. Optional: amp's polls
#define SPE_BAUD           9600
#define SPE_PUSH_FA        1       // push unsolicited FA…; on every frequency change
#define SPE_PUSH_IF        1       // also push IF…; frames (Kenwood AI-style), if the amp wants them
#define SPE_LOG            0       // 1 = log every amp poll (and undecodable bytes, in hex) on the console
#define SPE_DIAG           0       // bench: time edges on the RX pin instead of decoding
#define SPE_INVERT         true    // SPE TTL CAT idles low (measured 2026-11-14: amp polls "IF;" inverted, 9600)
#define SPE_KEEPALIVE_MS   2000    // re-push FA this often even without a change (0 = off)

// ── TCP CAT server (Kenwood over TCP, for Hamlib / WSJT-X) ─
// Hamlib: model TS-480 (2028), rig path "rgo-spe-cat.local:4533".
#define CAT_TCP_PORT       4533
#define CAT_TCP_MAX_CLIENTS 3
#define CAT_TCP_LOG        0     // 1 = log every TCP command, reply and time on the console

// ── PTT via the radio's USB RTS line ──────────────────────
// The RGO ONE's CAT "TX;" only shows TX: no RF, no amp key, ACC1 audio not
// passed (found 2026-11-15). Real PTT from a PC is the USB RTS line, radio
// menu 33 = ON. With RADIO_PTT_RTS 1, TX;/TX0;/TX1;/TX2; from a TCP client
// raise RTS instead of going to the radio as CAT, and RX; drops it.
// Fail-safes: RTS drops on RX;, when the keying client disconnects, when the
// radio's USB goes away, and after PTT_MAX_MS.
#define RADIO_PTT_RTS        1
#define RADIO_RTS_TX_ASSERTED 1      // 1 = RTS asserted keys the radio; 0 = inverted
#define PTT_MAX_MS           180000  // longest key-down before RTS is forced off
#define PTT_ALSO_CAT         1       // also send the TX/RX command to the radio as CAT
                                     // (RTS keys the RF; CAT TX may be what selects LINE IN)

// ── MQTT broker (shack) ───────────────────────────────────
// Broker requires auth (since 2026-08-21). Role account + password come from
// secrets.h — this device uses the iot role. Passwords are in the shack
// password manager.
#define MQTT_PORT       1883
#define MQTT_CLIENT_ID  "rgo-spe-cat"
#define MQTT_ENABLED    1

// ── Topics (shack/<service>/...) ──────────────────────────
#define T_STATUS   "shack/rgo-spe-cat/status"   // retained; LWT publishes {"event":"offline"}
#define T_RIG      "shack/rgo-spe-cat/rig"      // retained; {freq_hz, band, mode, tx, ok}

#include "secrets.h"

#ifndef MQTT_HOST
#error "Set MQTT_HOST (broker address) in include/secrets.h"
#endif

#ifndef OTA_PASS
#define OTA_PASS ""
#endif
