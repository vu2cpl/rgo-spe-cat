// SPE output. Works whether the amp polls or only listens:
//  - answers FA; and IF; queries from the cached rig state
//  - pushes unsolicited FA…; (and optionally IF…;) on every change, plus a
//    keepalive re-push
// Fail-safe: while the rig state is invalid (radio not answering) it sends
// nothing at all, so the amp never sits on a stale band.

#include "spe.h"
#include "rig.h"
#include "config.h"
#include <HardwareSerial.h>

namespace spe {
namespace {

HardwareSerial g_uart(SPE_UART_NUM);

void sendFA(const RigState& s) {
  char buf[16];
  snprintf(buf, sizeof(buf), "FA%011lu;", (unsigned long)s.freqHz);
  g_uart.print(buf);
}

void sendIF(const RigState& s) { g_uart.print(s.ifFrame); }

void handleCmd(const char* cmd) {
  RigState s = rig::get();
#if SPE_LOG
  Serial.printf("[SPE] amp -> %s%s\n", cmd, s.valid ? "" : "  (rig invalid, not answered)");
#endif
  if (!s.valid) return;                       // fail-safe: say nothing
  if (!strcmp(cmd, "FA;"))      sendFA(s);
  else if (!strcmp(cmd, "IF;")) sendIF(s);
  else if (!strcmp(cmd, "AI;")) g_uart.print("AI0;");
  else if (!strcmp(cmd, "ID;")) g_uart.print("ID020;");  // TS-480
  // Anything else is ignored; the amp only needs frequency.
}

void speTask(void*) {
  char     cmd[16];
  size_t   n = 0;
  uint32_t lastSeq = 0, lastPush = 0;
  for (;;) {
    while (g_uart.available()) {
      char c = g_uart.read();
      if (c == '\r' || c == '\n') continue;
      if (n < sizeof(cmd) - 1) cmd[n++] = c;
      if (c == ';') { cmd[n] = 0; handleCmd(cmd); n = 0; }
      else if (n >= sizeof(cmd) - 1) {        // junk — resync
#if SPE_LOG
        char hex[3 * sizeof(cmd) + 1];
        for (size_t i = 0; i < n; i++) snprintf(hex + 3 * i, 4, "%02X ", (uint8_t)cmd[i]);
        hex[3 * n] = 0;
        Serial.printf("[SPE] junk from amp: %s\n", hex);
#endif
        n = 0;
      }
    }

    RigState s = rig::get();
    if (s.valid) {
      bool changed = s.seq != lastSeq;
      bool keepalive = SPE_KEEPALIVE_MS && millis() - lastPush > SPE_KEEPALIVE_MS;
      if (changed || keepalive) {
        if (SPE_PUSH_FA) sendFA(s);
        if (SPE_PUSH_IF) sendIF(s);
        lastPush = millis();
      }
    }
    lastSeq = s.seq;
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

}  // namespace

#if SPE_DIAG
// Bench diagnostic: time the edges on the RX pin instead of decoding them,
// to find the amp's real bit time and idle level.
namespace {
volatile uint32_t g_edges[512];
volatile uint16_t g_nEdges = 0;
void IRAM_ATTR onEdge() {
  if (g_nEdges < 512) g_edges[g_nEdges++] = micros();
}
void diagTask(void*) {
  for (;;) {
    g_nEdges = 0;
    int idle = digitalRead(SPE_RX_PIN);
    attachInterrupt(SPE_RX_PIN, onEdge, CHANGE);
    vTaskDelay(pdMS_TO_TICKS(600));
    detachInterrupt(SPE_RX_PIN);
    uint16_t n = g_nEdges;
    uint32_t minW = UINT32_MAX;
    for (uint16_t i = 1; i < n; i++) {
      uint32_t w = g_edges[i] - g_edges[i - 1];
      if (w < minW) minW = w;
    }
    Serial.printf("[DIAG] idle=%d edges=%u minPulse=%lu us (~%lu baud)\n", idle, n,
                  (unsigned long)minW, minW && minW != UINT32_MAX ? 1000000UL / minW : 0UL);
    // First burst: level after each edge and its width in us.
    String s;
    int lvl = digitalRead(SPE_RX_PIN);
    for (uint16_t i = 1; i < n && i < 60; i++) {
      uint32_t w = g_edges[i] - g_edges[i - 1];
      if (w > 5000) { s += "| "; continue; }
      s += String(w) + " ";
    }
    Serial.printf("[DIAG] widths: %s\n", s.c_str());
    vTaskDelay(pdMS_TO_TICKS(1400));
  }
}
}  // namespace
#endif

void begin() {
#if SPE_DIAG
  g_uart.begin(SPE_BAUD, SERIAL_8N1, -1, SPE_TX_PIN);   // TX only; RX pin timed below
  pinMode(SPE_RX_PIN, INPUT);
  xTaskCreatePinnedToCore(diagTask, "spediag", 4096, nullptr, 5, nullptr, 1);
#else
  // The SPE's TTL CAT lines idle LOW (RS-232 polarity at TTL levels), so
  // the UART runs inverted on both RX and TX. See SPE_INVERT in config.h.
  g_uart.begin(SPE_BAUD, SERIAL_8N1, SPE_RX_PIN, SPE_TX_PIN, SPE_INVERT);
#endif
  xTaskCreatePinnedToCore(speTask, "spe", 4096, nullptr, 5, nullptr, 1);
}

}  // namespace spe
