#pragma once
// Minimal FTDI FT232R USB host driver on the ESP-IDF USB host stack.
// The RGO ONE's USB-B socket is an FT232R, which is vendor-specific (not
// CDC-ACM), so this does the FTDI control requests itself.
#include <Arduino.h>

namespace ftdi {

// Install the USB host stack and start the driver tasks. Call once from setup().
// rtsIdleAsserted: the RTS level applied every time the radio is opened
// (the "not transmitting" level when RTS is used for PTT).
void begin(uint16_t vid, uint16_t pid, uint32_t baud, bool rtsIdleAsserted = false);

// True while the FTDI device is open and configured.
bool connected();

// Write bytes to the radio. Blocks until sent or timeout. Returns bytes written.
size_t write(const uint8_t* data, size_t len, uint32_t timeoutMs = 100);

// Read up to len bytes received from the radio. Waits up to timeoutMs for the
// first byte. Returns bytes read (0 on timeout).
size_t read(uint8_t* buf, size_t len, uint32_t timeoutMs);

// Discard anything received but not yet read.
void flushInput();

// Set the FTDI RTS line (true = asserted). Returns false if the radio is not
// connected or the control request failed. Safe to call from any task.
bool setRts(bool asserted);

}  // namespace ftdi
