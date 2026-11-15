// ============================================================
//  RGO ONE SPE CAT Server
//  ESP32-S3 CAT bridge: polls the RGO ONE over USB host and feeds
//  Kenwood-format frequency to the SPE amp, plus TCP CAT for Hamlib/WSJT-X.
//
//  Module map:
//    ftdi_host  USB host driver for the radio's FT232R
//    rig        radio task: owns the CAT port, polls IF;, queues PC commands
//    spe        Kenwood emulation to the amp on UART1 (fail-safe when stale)
//    tcp_cat    Kenwood over TCP for Hamlib / WSJT-X
//    main       WiFiManager, MQTT (status + rig), OTA, status LED
//
//  The radio → SPE path starts before WiFi and never depends on it, so the
//  amp keeps following band changes with WiFi down or the portal open.
// ============================================================

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>
#include "config.h"
#include "ftdi_host.h"
#include "rig.h"
#include "spe.h"
#include "tcp_cat.h"

WiFiClient   net;
PubSubClient mqtt(net);

// ── Status LED (on-board RGB): green = radio OK, amber = USB up but no
//    replies, red = no radio on USB, blue blink = no WiFi ──────────
void updateLed(const RigState& s) {
#ifdef RGB_BUILTIN
  static uint32_t last = 0;
  if (millis() - last < 250) return;
  last = millis();
  uint8_t r = 0, g = 0, b = 0;
  if (s.valid)                  g = 16;
  else if (ftdi::connected()) { r = 16; g = 8; }
  else                          r = 16;
  if (WiFi.status() != WL_CONNECTED && (millis() / 500) % 2) { r = g = 0; b = 16; }
  rgbLedWrite(RGB_BUILTIN, r, g, b);
#endif
}

// ── MQTT ─────────────────────────────────────────────────
bool mqttConnect() {
  Serial.print("[MQTT] connecting… ");
  bool ok = mqtt.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASS,
                         T_STATUS, 1, true, "{\"event\":\"offline\"}");
  if (ok) {
    Serial.println("ok");
    mqtt.publish(T_STATUS, "{\"event\":\"online\"}", true);
  } else {
    Serial.printf("failed rc=%d\n", mqtt.state());
  }
  return ok;
}

void publishRig(const RigState& s) {
  StaticJsonDocument<192> doc;
  doc["ok"] = s.valid;
  if (s.valid) {
    doc["freq_hz"] = s.freqHz;
    doc["band"]    = rig::bandName(s.freqHz);
    doc["mode"]    = rig::modeName(s.mode);
    doc["tx"]      = s.tx;
  }
  char buf[192];
  serializeJson(doc, buf);
  mqtt.publish(T_RIG, buf, true);
}

void mqttLoop(const RigState& s) {
#if MQTT_ENABLED
  if (WiFi.status() != WL_CONNECTED) return;
  if (!mqtt.connected()) {
    static uint32_t lastTry = 0;
    if (millis() - lastTry > 5000) { lastTry = millis(); mqttConnect(); }
    return;
  }
  mqtt.loop();

  // Rig state on change, at most 4×/s.
  static uint32_t lastSeq = UINT32_MAX, lastPub = 0;
  if (s.seq != lastSeq && millis() - lastPub > 250) {
    lastSeq = s.seq;
    lastPub = millis();
    publishRig(s);
  }

  static uint32_t lastBeat = 0;
  if (millis() - lastBeat > 30000) {
    lastBeat = millis();
    StaticJsonDocument<160> doc;
    doc["event"]    = "heartbeat";
    doc["uptime_s"] = millis() / 1000;
    doc["rssi"]     = WiFi.RSSI();
    doc["radio"]    = ftdi::connected();
    char buf[160];
    serializeJson(doc, buf);
    mqtt.publish(T_STATUS, buf, true);
  }
#endif
}

// ── Setup ─────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[BOOT] RGO ONE SPE CAT Server");

  // Radio + amp first: these must work with or without WiFi.
  ftdi::begin(RADIO_USB_VID, RADIO_USB_PID, RADIO_BAUD,
              RADIO_PTT_RTS && !RADIO_RTS_TX_ASSERTED);   // RTS idle = not transmitting
  rig::begin();
  spe::begin();

  WiFiManager wm;
  wm.setHostname(HOSTNAME);
  wm.setConfigPortalTimeout(WIFI_PORTAL_TIMEOUT_S);
  Serial.println("[WiFi] autoConnect (portal: " WIFI_AP_NAME ")");
  if (wm.autoConnect(WIFI_AP_NAME, WIFI_AP_PASS)) {
    Serial.printf("[WiFi] %s\n", WiFi.localIP().toString().c_str());
  } else {
    // Don't restart — that would interrupt the SPE feed. Saved creds (if
    // any) keep retrying in the background; the portal comes back on reboot.
    Serial.println("[WiFi] portal timed out — running offline");
  }
  WiFi.setAutoReconnect(true);
  // Modem-sleep (the default) holds replies until the next beacon: CAT
  // round trips jumped from ~7 ms to ~210 ms. Mains-powered, so keep the
  // radio awake.
  WiFi.setSleep(false);

  tcpcat::begin();

  ArduinoOTA.setHostname(HOSTNAME);
  if (strlen(OTA_PASS)) ArduinoOTA.setPassword(OTA_PASS);
  ArduinoOTA.begin();

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

// ── Loop ──────────────────────────────────────────────────
void loop() {
  RigState s = rig::get();
  ArduinoOTA.handle();
  mqttLoop(s);
  updateLed(s);

  static uint32_t lastSeq = UINT32_MAX;
  if (s.seq != lastSeq) {
    lastSeq = s.seq;
    if (s.valid)
      Serial.printf("[RIG] %lu Hz %s %s %s\n", (unsigned long)s.freqHz,
                    rig::bandName(s.freqHz), rig::modeName(s.mode), s.tx ? "TX" : "RX");
  }
  delay(5);
}
