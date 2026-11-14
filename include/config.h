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
// SPE CAT baud is an open item — set it to match the amp's CAT menu.
#define SPE_UART_NUM       1
#define SPE_TX_PIN         17      // S3 TX → SPE CAT in
#define SPE_RX_PIN         18      // SPE CAT out → S3 RX (only if the amp polls; check its voltage first)
#define SPE_BAUD           9600
#define SPE_PUSH_FA        1       // push unsolicited FA…; on every frequency change
#define SPE_PUSH_IF        0       // also push IF…; frames (Kenwood AI-style), if the amp wants them
#define SPE_KEEPALIVE_MS   2000    // re-push FA this often even without a change (0 = off)

// ── TCP CAT server (Kenwood over TCP, for Hamlib / WSJT-X) ─
// Hamlib: model TS-480 (2028), rig path "rgo-spe-cat.local:4533".
#define CAT_TCP_PORT       4533
#define CAT_TCP_MAX_CLIENTS 3

// ── MQTT broker (shack) ───────────────────────────────────
// Broker requires auth (since 2026-08-21). Role account + password come from
// secrets.h — this device uses the iot role. Passwords are in the shack
// password manager.
#define MQTT_HOST       "192.168.1.169"
#define MQTT_PORT       1883
#define MQTT_CLIENT_ID  "rgo-spe-cat"
#define MQTT_ENABLED    1

// ── Topics (shack/<service>/...) ──────────────────────────
#define T_STATUS   "shack/rgo-spe-cat/status"   // retained; LWT publishes {"event":"offline"}
#define T_RIG      "shack/rgo-spe-cat/rig"      // retained; {freq_hz, band, mode, tx, ok}

#include "secrets.h"

#ifndef OTA_PASS
#define OTA_PASS ""
#endif
