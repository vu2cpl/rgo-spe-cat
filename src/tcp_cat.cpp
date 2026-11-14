// TCP CAT server. Each ';'-terminated command from a client goes to the
// radio through rig::transact() (the radio task's queue), except FA; and IF;
// which are answered from the cached state to keep the radio link free for
// the poll. Replies go back only to the client that asked.

#include "tcp_cat.h"
#include "rig.h"
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

void handleCmd(Client& c, const char* cmd) {
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
  } else if (!strcmp(cmd, "AI;")) {
    strlcpy(reply, "AI0;", sizeof(reply));
  } else if (!strncmp(cmd, "AI", 2)) {
    // Absorb AI set commands: AI1/AI2 would make the radio send unsolicited
    // frames and break the poll. No reply to a set command.
  } else if (!rig::transact(cmd, reply, sizeof(reply))) {
    strlcpy(reply, "?;", sizeof(reply));   // radio not there
  }
  if (reply[0]) c.sock.print(reply);
}

void tcpTask(void*) {
  g_server.begin();
  g_server.setNoDelay(true);
  Serial.printf("[TCP] CAT server on port %d\n", CAT_TCP_PORT);
  for (;;) {
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
    for (auto& c : g_clients) {
      if (!c.sock.connected()) continue;
      while (c.sock.available()) {
        char ch = c.sock.read();
        if (ch == '\r' || ch == '\n') continue;
        if (c.n < sizeof(c.buf) - 1) c.buf[c.n++] = ch;
        if (ch == ';') { c.buf[c.n] = 0; handleCmd(c, c.buf); c.n = 0; }
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
