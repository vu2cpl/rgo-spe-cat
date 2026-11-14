// Radio task: polls IF; and serialises every other CAT command through one
// queue, so PC software can never stall the poll or interleave replies.
//
// TS-480 IF; reply (verified on the RGO ONE 2026-11-14):
//   IF00007117850     -00000000001000000 ;
//   ^^ P1 freq (11)  P2 (5 sp)  P3 RIT ±4  P4 RIT  P5 XIT  P6 mem (3)
//      P7 TX/RX  P8 mode  P9 VFO  P10 scan  P11 split  P12 tone  P13 tone# (2)  P14
// i.e. after "IF": [0..10] freq, [26] TX/RX, [27] mode  (37 chars + ';')

#include "rig.h"
#include "config.h"
#include "ftdi_host.h"

namespace rig {
namespace {

struct Request {
  char              cmd[64];
  char*             reply;
  size_t            replyLen;
  bool              ok;
  SemaphoreHandle_t done;
};

RigState          g_state;
SemaphoreHandle_t g_lock;
QueueHandle_t     g_queue;

// Read one ';'-terminated reply. Returns its length (incl. ';'), 0 on timeout.
size_t readReply(char* buf, size_t len, uint32_t timeoutMs) {
  size_t n = 0;
  uint32_t start = millis();
  while (millis() - start < timeoutMs && n < len - 1) {
    uint8_t c;
    if (ftdi::read(&c, 1, 10) == 1) {
      if (c == '\r' || c == '\n') continue;
      buf[n++] = c;
      if (c == ';') { buf[n] = 0; return n; }
    }
  }
  buf[n] = 0;
  return 0;
}

bool sendCmd(const char* cmd) {
  size_t len = strlen(cmd);
  return ftdi::write(reinterpret_cast<const uint8_t*>(cmd), len) == len;
}

// A Kenwood command with no parameters ("FA;", "MD;", "IF;") is a read;
// those always get a reply. Sets normally get none, so wait less for them.
bool isQuery(const char* cmd) {
  size_t len = strlen(cmd);
  return len == 3 && cmd[2] == ';';
}

void applyIF(const char* f) {
  // f = "IF" + 35 chars + ";"
  if (strlen(f) < 38 || f[0] != 'I' || f[1] != 'F') return;
  char fbuf[12];
  memcpy(fbuf, f + 2, 11);
  fbuf[11] = 0;
  uint32_t freq = strtoul(fbuf, nullptr, 10);
  uint8_t  mode = f[2 + 27] - '0';
  bool     tx   = f[2 + 26] == '1';
  if (freq == 0) return;

  xSemaphoreTake(g_lock, portMAX_DELAY);
  bool changed = !g_state.valid || freq != g_state.freqHz ||
                 mode != g_state.mode || tx != g_state.tx;
  g_state.valid    = true;
  g_state.freqHz   = freq;
  g_state.mode     = mode;
  g_state.tx       = tx;
  g_state.lastGood = millis();
  strlcpy(g_state.ifFrame, f, sizeof(g_state.ifFrame));
  if (changed) g_state.seq++;
  xSemaphoreGive(g_lock);
}

void markStaleIfNeeded() {
  xSemaphoreTake(g_lock, portMAX_DELAY);
  if (g_state.valid &&
      (!ftdi::connected() || millis() - g_state.lastGood > RADIO_STALE_MS)) {
    g_state.valid = false;
    g_state.seq++;
    Serial.println("[RIG] radio not answering — state invalid");
  }
  xSemaphoreGive(g_lock);
}

void poll() {
  char buf[64];
  ftdi::flushInput();
  if (!sendCmd("IF;")) return;
  if (readReply(buf, sizeof(buf), RADIO_REPLY_MS)) applyIF(buf);
}

void serve(Request* r) {
  r->ok = false;
  if (r->reply && r->replyLen) r->reply[0] = 0;
  if (ftdi::connected()) {
    ftdi::flushInput();
    if (sendCmd(r->cmd)) {
      char buf[96];
      size_t n = readReply(buf, sizeof(buf), isQuery(r->cmd) ? RADIO_REPLY_MS : 60);
      if (n && r->reply) strlcpy(r->reply, buf, r->replyLen);
      if (n && buf[0] == 'I' && buf[1] == 'F') applyIF(buf);
      r->ok = true;
    }
  }
  xSemaphoreGive(r->done);
}

void radioTask(void*) {
  uint32_t lastPoll = 0;
  for (;;) {
    // Poll first whenever it is due, so a busy PC client can't starve it.
    if (lastPoll == 0 || millis() - lastPoll >= RADIO_POLL_MS) {
      lastPoll = millis();
      if (ftdi::connected()) poll();
      markStaleIfNeeded();
    }
    Request* r;
    uint32_t wait = RADIO_POLL_MS - min<uint32_t>(RADIO_POLL_MS, millis() - lastPoll);
    if (xQueueReceive(g_queue, &r, pdMS_TO_TICKS(wait)) == pdTRUE) {
      bool isSet = !isQuery(r->cmd);
      serve(r);   // r is invalid after this — the caller may return
      // A set command may have changed freq/mode — poll straight away so the
      // SPE follows without waiting for the next cycle.
      if (isSet) lastPoll = 0;
    }
  }
}

}  // namespace

void begin() {
  g_lock  = xSemaphoreCreateMutex();
  g_queue = xQueueCreate(8, sizeof(Request*));
  xTaskCreatePinnedToCore(radioTask, "radio", 4096, nullptr, 6, nullptr, 1);
}

RigState get() {
  xSemaphoreTake(g_lock, portMAX_DELAY);
  RigState s = g_state;
  xSemaphoreGive(g_lock);
  return s;
}

bool transact(const char* cmd, char* reply, size_t replyLen, uint32_t timeoutMs) {
  if (!ftdi::connected()) return false;
  Request r = {};
  strlcpy(r.cmd, cmd, sizeof(r.cmd));
  r.reply    = reply;
  r.replyLen = replyLen;
  r.done     = xSemaphoreCreateBinary();
  Request* p = &r;
  bool ok = false;
  if (xQueueSend(g_queue, &p, pdMS_TO_TICKS(timeoutMs)) == pdTRUE) {
    // The radio task always gives `done`, so wait for it even past our
    // timeout — `r` lives on this stack and must outlast the request.
    xSemaphoreTake(r.done, portMAX_DELAY);
    ok = r.ok;
  }
  vSemaphoreDelete(r.done);
  return ok;
}

const char* modeName(uint8_t m) {
  switch (m) {
    case 1: return "LSB";  case 2: return "USB";  case 3: return "CW";
    case 4: return "FM";   case 5: return "AM";   case 6: return "FSK";
    case 7: return "CW-R"; case 9: return "FSK-R";
    default: return "?";
  }
}

const char* bandName(uint32_t f) {
  struct B { uint32_t lo, hi; const char* n; };
  static const B bands[] = {
    {1800000, 2000000, "160m"}, {3500000, 4000000, "80m"},  {5250000, 5450000, "60m"},
    {7000000, 7300000, "40m"},  {10100000, 10150000, "30m"}, {14000000, 14350000, "20m"},
    {18068000, 18168000, "17m"}, {21000000, 21450000, "15m"}, {24890000, 24990000, "12m"},
    {28000000, 29700000, "10m"}, {50000000, 54000000, "6m"},
  };
  for (const auto& b : bands) if (f >= b.lo && f <= b.hi) return b.n;
  return "";
}

}  // namespace rig
