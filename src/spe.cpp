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
      else if (n >= sizeof(cmd) - 1) n = 0;   // junk — resync
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

void begin() {
  g_uart.begin(SPE_BAUD, SERIAL_8N1, SPE_RX_PIN, SPE_TX_PIN);
  xTaskCreatePinnedToCore(speTask, "spe", 4096, nullptr, 5, nullptr, 1);
}

}  // namespace spe
