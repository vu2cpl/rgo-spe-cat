// TCP CAT server. Each ';'-terminated command from a client goes to the
// radio through rig::transact() (the radio task's queue), except FA; and IF;
// which are answered from the cached state to keep the radio link free for
// the poll. Replies go back only to the client that asked.
//
// PTT (RADIO_PTT_RTS): TX;/TX0;/TX1;/TX2; raise the radio's USB RTS line and
// RX; drops it; neither goes to the radio as CAT (its CAT TX is display-only).
// Replies mimic the radio's own echo ("TX0;" / "RX0;"), which Hamlib already
// worked with. RTS also drops when the keying client disconnects, when the
// radio's USB goes away, and after PTT_MAX_MS.

#include "tcp_cat.h"
#include "rig.h"
#include "ftdi_host.h"
#include "config.h"
#include <WiFi.h>

namespace tcpcat {
namespace {

WiFiServer g_server(CAT_TCP_PORT);

struct Client {
  WiFiClient sock;
  char       buf[64];
  size_t     n = 0;
};
Client g_clients[CAT_TCP_MAX_CLIENTS];

// ── PTT state (touched only by tcpTask) ──────────────────
int      g_pttOwner = -1;   // index of the client that keyed; -1 = not keyed
uint32_t g_pttSince = 0;

bool rtsPtt(bool tx) { return ftdi::setRts(tx == bool(RADIO_RTS_TX_ASSERTED)); }

void pttOff(const char* why) {
  if (g_pttOwner < 0) return;
  // If the radio's USB is gone there is nothing to release: the driver puts
  // RTS back to idle when the radio is opened again.
  if (rtsPtt(false) || !ftdi::connected()) {
    if (PTT_ALSO_CAT && strcmp(why, "RX;")) {   // watchdog drop: take the radio out of CAT TX too
      char tmp[16];
      rig::transact("RX;", tmp, sizeof(tmp));
    }
    Serial.printf("[PTT] off (%s)\n", why);
    g_pttOwner = -1;
  }
  // else: keep the owner and retry on the next loop pass.
}

bool isTxCmd(const char* cmd) {
  return cmd[0] == 'T' && cmd[1] == 'X' &&
         (cmd[2] == ';' || (cmd[2] >= '0' && cmd[2] <= '2' && cmd[3] == ';'));
}

void pttWatchdog() {
  if (g_pttOwner < 0) return;
  if (!g_clients[g_pttOwner].sock.connected()) pttOff("client gone");
  else if (millis() - g_pttSince > PTT_MAX_MS) pttOff("max key-down time");
  else if (!ftdi::connected()) pttOff("radio USB gone");
}

void handleCmd(int idx, const char* cmd) {
  Client& c = g_clients[idx];
  uint32_t t0 = millis();
  RigState s = rig::get();
  char reply[96] = {0};
  if (s.valid && !strcmp(cmd, "FA;")) {
    snprintf(reply, sizeof(reply), "FA%011lu;", (unsigned long)s.freqHz);
  } else if (s.valid && !strcmp(cmd, "IF;")) {
    strlcpy(reply, s.ifFrame, sizeof(reply));
  } else if (s.valid && !strcmp(cmd, "MD;")) {
    // The RGO ONE answers MD; with a bare "MD;" — take the mode digit
    // from the cached IF frame (position 27 after "IF").
    snprintf(reply, sizeof(reply), "MD%c;", s.ifFrame[2 + 27]);
  } else if (!strcmp(cmd, "PS;")) {
    // Not supported by the radio; Hamlib probes it on open (1 s timeout x4).
    strlcpy(reply, s.valid ? "PS1;" : "PS0;", sizeof(reply));
  } else if (!strcmp(cmd, "FW;")) {
    // Filter width: the radio never answers, and Hamlib's get_mode asks for
    // it after MD; — 4 retries of ~1 s, then WSJT-X drops the rig and
    // reconnects every ~9 s. "0000" = no fixed width; Hamlib falls back to
    // the mode's normal passband.
    strlcpy(reply, "FW0000;", sizeof(reply));
  } else if (RADIO_PTT_RTS && isTxCmd(cmd)) {
    char tmp[16];
    if (PTT_ALSO_CAT) rig::transact(cmd, tmp, sizeof(tmp));   // radio echoes "TX0;"
    if (rtsPtt(true)) {
      if (g_pttOwner < 0) Serial.printf("[PTT] on (%s)\n", cmd);
      g_pttOwner = idx;
      g_pttSince = millis();
      strlcpy(reply, "TX0;", sizeof(reply));
    } else {
      strlcpy(reply, "?;", sizeof(reply));   // radio not there
    }
  } else if (RADIO_PTT_RTS && !strcmp(cmd, "RX;")) {
    pttOff("RX;");
    char tmp[16];
    if (PTT_ALSO_CAT) rig::transact(cmd, tmp, sizeof(tmp));
    strlcpy(reply, "RX0;", sizeof(reply));
  } else if (!strcmp(cmd, "AI;")) {
    strlcpy(reply, "AI0;", sizeof(reply));
  } else if (!strncmp(cmd, "AI", 2)) {
    // Absorb AI set commands: AI1/AI2 would make the radio send unsolicited
    // frames and break the poll. No reply to a set command.
  } else if (!rig::transact(cmd, reply, sizeof(reply))) {
    strlcpy(reply, "?;", sizeof(reply));   // radio not there
  }
  if (reply[0]) c.sock.print(reply);
#if CAT_TCP_LOG
  Serial.printf("[TCP] %s -> %s (%lu ms)\n", cmd, reply[0] ? reply : "(none)",
                (unsigned long)(millis() - t0));
#endif
}

void tcpTask(void*) {
  g_server.begin();
  g_server.setNoDelay(true);
  Serial.printf("[TCP] CAT server on port %d\n", CAT_TCP_PORT);
  for (;;) {
    pttWatchdog();   // before accept(), so a freed slot is checked before reuse
    WiFiClient incoming = g_server.accept();
    if (incoming) {
      bool placed = false;
      for (auto& c : g_clients) {
        if (!c.sock.connected()) {
          c.sock = incoming;
          c.sock.setNoDelay(true);
          c.n = 0;
          placed = true;
          Serial.printf("[TCP] client %s\n", incoming.remoteIP().toString().c_str());
          break;
        }
      }
      if (!placed) incoming.stop();
    }
    for (int i = 0; i < CAT_TCP_MAX_CLIENTS; i++) {
      Client& c = g_clients[i];
      if (!c.sock.connected()) continue;
      while (c.sock.available()) {
        char ch = c.sock.read();
        if (ch == '\r' || ch == '\n') continue;
        if (c.n < sizeof(c.buf) - 1) c.buf[c.n++] = ch;
        if (ch == ';') { c.buf[c.n] = 0; handleCmd(i, c.buf); c.n = 0; }
        else if (c.n >= sizeof(c.buf) - 1) c.n = 0;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

}  // namespace

void begin() {
  xTaskCreatePinnedToCore(tcpTask, "tcpcat", 6144, nullptr, 4, nullptr, 1);
}

}  // namespace tcpcat
