#pragma once
// Rig state + the radio task that owns the RGO ONE's CAT port.
// Every output (SPE UART, TCP CAT, MQTT) reads from this state; nothing
// but the radio task talks to the radio.
#include <Arduino.h>

struct RigState {
  bool     valid    = false;   // false until a good reply, and again once stale
  uint32_t freqHz   = 0;
  uint8_t  mode     = 0;       // Kenwood mode digit (1 LSB, 2 USB, 3 CW, 4 FM, 5 AM, 6 FSK, 7 CW-R, 9 FSK-R)
  bool     tx       = false;
  char     ifFrame[48] = {0};  // last raw "IF...;" frame from the radio, re-served verbatim
  uint32_t lastGood = 0;       // millis() of last good reply
  uint32_t seq      = 0;       // bumps on any change, for cheap change detection
};

namespace rig {

void begin();                    // start the radio task (call after ftdi::begin)
RigState get();                  // thread-safe snapshot

// Send a raw Kenwood command (e.g. "FA00014074000;" or "MD;") to the radio
// through the radio task's queue and collect any ';'-terminated reply.
// Returns false if the radio is not connected or the request timed out.
// reply is empty for set commands (the radio sends nothing back).
bool transact(const char* cmd, char* reply, size_t replyLen, uint32_t timeoutMs = 500);

const char* modeName(uint8_t mode);
const char* bandName(uint32_t freqHz);   // "40m", … or "" if outside a ham band

}  // namespace rig
