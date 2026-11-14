// Minimal FTDI FT232R USB host driver — see ftdi_host.h.
//
// Task layout:
//   usb_lib   — runs usb_host_lib_handle_events() (the host library daemon)
//   usb_cli   — runs usb_host_client_handle_events(); all transfer callbacks
//               fire in this task, so it must never block on a transfer
//   usb_drv   — opens/configures/closes the device; this is where we wait on
//               control transfers, which is why it is separate from usb_cli
//
// FTDI specifics: vendor control requests (bmRequestType 0x40) set baud, line
// format, flow control and modem lines; every bulk-IN packet starts with two
// modem-status bytes, which are stripped.

#include "ftdi_host.h"
#include <usb/usb_host.h>
#include <freertos/stream_buffer.h>

namespace ftdi {
namespace {

constexpr uint8_t  REQ_RESET      = 0x00;
constexpr uint8_t  REQ_MODEM_CTRL = 0x01;
constexpr uint8_t  REQ_SET_FLOW   = 0x02;
constexpr uint8_t  REQ_SET_BAUD   = 0x03;
constexpr uint8_t  REQ_SET_DATA   = 0x04;
constexpr uint8_t  REQ_SET_LAT    = 0x09;
constexpr uint16_t DATA_8N1       = 0x0008;
constexpr uint16_t DTR_LOW        = 0x0100;   // mask bit set, value bit clear
constexpr uint16_t RTS_LOW        = 0x0200;
constexpr uint8_t  LATENCY_MS     = 4;

enum : uint32_t { EV_NEW_DEV = 1, EV_DEV_GONE = 2 };

uint16_t g_vid, g_pid;
uint32_t g_baud;

usb_host_client_handle_t g_client = nullptr;
usb_device_handle_t      g_dev    = nullptr;
volatile uint8_t         g_newAddr = 0;
volatile bool            g_ready   = false;
volatile bool            g_gone    = false;
volatile bool            g_inBusy  = false;

uint8_t  g_epIn = 0, g_epOut = 0;
uint16_t g_mpsIn = 64;

usb_transfer_t* g_ctrl = nullptr;
usb_transfer_t* g_in   = nullptr;
usb_transfer_t* g_out  = nullptr;

SemaphoreHandle_t    g_ctrlDone, g_outDone, g_outLock;
StreamBufferHandle_t g_rx;
TaskHandle_t         g_drvTask;

// ── callbacks (run in usb_cli) ───────────────────────────
void clientEvent(const usb_host_client_event_msg_t* msg, void*) {
  if (msg->event == USB_HOST_CLIENT_EVENT_NEW_DEV) {
    g_newAddr = msg->new_dev.address;
    xTaskNotify(g_drvTask, EV_NEW_DEV, eSetBits);
  } else if (msg->event == USB_HOST_CLIENT_EVENT_DEV_GONE) {
    if (msg->dev_gone.dev_hdl == g_dev) {
      g_gone  = true;
      g_ready = false;
      xTaskNotify(g_drvTask, EV_DEV_GONE, eSetBits);
    }
  }
}

void ctrlCb(usb_transfer_t*) { xSemaphoreGive(g_ctrlDone); }
void outCb(usb_transfer_t*)  { xSemaphoreGive(g_outDone); }

void inCb(usb_transfer_t* t) {
  if (t->status == USB_TRANSFER_STATUS_COMPLETED && t->actual_num_bytes > 2) {
    // Strip the 2 modem-status bytes at the start of each max-packet chunk.
    for (int off = 0; off < t->actual_num_bytes; off += g_mpsIn) {
      int n = min<int>(g_mpsIn, t->actual_num_bytes - off) - 2;
      if (n > 0) xStreamBufferSend(g_rx, t->data_buffer + off + 2, n, 0);
    }
  }
  if (!g_gone && t->status != USB_TRANSFER_STATUS_NO_DEVICE &&
      t->status != USB_TRANSFER_STATUS_CANCELED) {
    if (usb_host_transfer_submit(t) == ESP_OK) return;
  }
  g_inBusy = false;
}

// ── helpers (run in usb_drv) ─────────────────────────────
bool vendorOut(uint8_t req, uint16_t value, uint16_t index) {
  auto* s = reinterpret_cast<usb_setup_packet_t*>(g_ctrl->data_buffer);
  s->bmRequestType = 0x40;
  s->bRequest      = req;
  s->wValue        = value;
  s->wIndex        = index;
  s->wLength       = 0;
  g_ctrl->num_bytes        = sizeof(usb_setup_packet_t);
  g_ctrl->device_handle    = g_dev;
  g_ctrl->bEndpointAddress = 0;
  g_ctrl->callback         = ctrlCb;
  g_ctrl->timeout_ms       = 500;
  if (usb_host_transfer_submit_control(g_client, g_ctrl) != ESP_OK) return false;
  if (xSemaphoreTake(g_ctrlDone, pdMS_TO_TICKS(1000)) != pdTRUE) return false;
  return g_ctrl->status == USB_TRANSFER_STATUS_COMPLETED;
}

// FT232R/BM baud divisor: 3 MHz / baud, integer part plus 1/8 fractions
// encoded in the top bits of wValue and bit 0 of wIndex.
void baudDivisor(uint32_t baud, uint16_t& value, uint16_t& index) {
  static const uint8_t fracCode[8] = {0, 3, 2, 4, 1, 5, 6, 7};
  uint32_t div8 = (3000000UL * 8 + baud / 2) / baud;   // divisor in 1/8 units
  uint32_t d    = (div8 >> 3) | (uint32_t(fracCode[div8 & 7]) << 14);
  if (d == 1) d = 0;                  // 3 Mbaud special cases
  else if (d == 0x4001) d = 1;        // 2 Mbaud
  value = d & 0xFFFF;
  index = (d >> 16) & 0xFFFF;
}

bool findEndpoints() {
  const usb_config_desc_t* cfg;
  if (usb_host_get_active_config_descriptor(g_dev, &cfg) != ESP_OK) return false;
  int offset = 0;
  const usb_intf_desc_t* intf = usb_parse_interface_descriptor(cfg, 0, 0, &offset);
  if (!intf) return false;
  for (int i = 0; i < intf->bNumEndpoints; i++) {
    int epOff = offset;
    const usb_ep_desc_t* ep =
        usb_parse_endpoint_descriptor_by_index(intf, i, cfg->wTotalLength, &epOff);
    if (!ep || (ep->bmAttributes & USB_BM_ATTRIBUTES_XFERTYPE_MASK) != USB_BM_ATTRIBUTES_XFER_BULK)
      continue;
    if (ep->bEndpointAddress & USB_B_ENDPOINT_ADDRESS_EP_DIR_MASK) {
      g_epIn  = ep->bEndpointAddress;
      g_mpsIn = ep->wMaxPacketSize;
    } else {
      g_epOut = ep->bEndpointAddress;
    }
  }
  return g_epIn && g_epOut;
}

void closeDevice() {
  g_ready = false;
  if (!g_dev) return;
  // Wait for the IN transfer to finish (it stops resubmitting once g_gone).
  for (int i = 0; i < 50 && g_inBusy; i++) {
    usb_host_endpoint_halt(g_dev, g_epIn);
    usb_host_endpoint_flush(g_dev, g_epIn);
    vTaskDelay(pdMS_TO_TICKS(10));
  }
  usb_host_interface_release(g_client, g_dev, 0);
  usb_host_device_close(g_client, g_dev);
  g_dev = nullptr;
  g_epIn = g_epOut = 0;
  Serial.println("[USB] radio closed");
}

void openDevice(uint8_t addr) {
  if (g_dev) return;   // one radio only
  usb_device_handle_t dev;
  if (usb_host_device_open(g_client, addr, &dev) != ESP_OK) return;
  const usb_device_desc_t* dd;
  usb_host_get_device_descriptor(dev, &dd);
  Serial.printf("[USB] device %04x:%04x at addr %u\n", dd->idVendor, dd->idProduct, addr);
  if (dd->idVendor != g_vid || dd->idProduct != g_pid) {
    usb_host_device_close(g_client, dev);
    return;
  }
  g_dev  = dev;
  g_gone = false;
  if (!findEndpoints() || usb_host_interface_claim(g_client, g_dev, 0, 0) != ESP_OK) {
    Serial.println("[USB] FTDI: no bulk endpoints / claim failed");
    usb_host_device_close(g_client, g_dev);
    g_dev = nullptr;
    return;
  }
  uint16_t bv, bi;
  baudDivisor(g_baud, bv, bi);
  // DTR/RTS are forced low first thing, so they can never key the radio.
  bool ok = vendorOut(REQ_RESET, 0, 0) &&
            vendorOut(REQ_MODEM_CTRL, DTR_LOW, 0) &&
            vendorOut(REQ_MODEM_CTRL, RTS_LOW, 0) &&
            vendorOut(REQ_SET_BAUD, bv, bi) &&
            vendorOut(REQ_SET_DATA, DATA_8N1, 0) &&
            vendorOut(REQ_SET_FLOW, 0, 0) &&
            vendorOut(REQ_SET_LAT, LATENCY_MS, 0);
  if (!ok) {
    Serial.println("[USB] FTDI setup failed");
    usb_host_interface_release(g_client, g_dev, 0);
    usb_host_device_close(g_client, g_dev);
    g_dev = nullptr;
    return;
  }
  xStreamBufferReset(g_rx);
  g_in->device_handle    = g_dev;
  g_in->bEndpointAddress = g_epIn;
  g_in->num_bytes        = g_mpsIn;
  g_in->callback         = inCb;
  g_in->timeout_ms       = 0;
  g_inBusy = true;
  if (usb_host_transfer_submit(g_in) != ESP_OK) g_inBusy = false;
  g_ready = true;
  Serial.printf("[USB] FTDI ready, %lu baud 8N1, EP in 0x%02x out 0x%02x\n",
                (unsigned long)g_baud, g_epIn, g_epOut);
}

// ── tasks ────────────────────────────────────────────────
void libTask(void*) {
  for (;;) {
    uint32_t flags;
    usb_host_lib_handle_events(portMAX_DELAY, &flags);
    if (flags & USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS) usb_host_device_free_all();
  }
}

void clientTask(void*) {
  for (;;) usb_host_client_handle_events(g_client, portMAX_DELAY);
}

void drvTask(void*) {
  for (;;) {
    uint32_t ev = 0;
    xTaskNotifyWait(0, UINT32_MAX, &ev, portMAX_DELAY);
    if (ev & EV_DEV_GONE) closeDevice();
    if (ev & EV_NEW_DEV)  openDevice(g_newAddr);
  }
}

}  // namespace

void begin(uint16_t vid, uint16_t pid, uint32_t baud) {
  g_vid = vid; g_pid = pid; g_baud = baud;
  g_ctrlDone = xSemaphoreCreateBinary();
  g_outDone  = xSemaphoreCreateBinary();
  g_outLock  = xSemaphoreCreateMutex();
  g_rx       = xStreamBufferCreate(1024, 1);

  usb_host_config_t hc = {};
  hc.skip_phy_setup = false;
  hc.intr_flags     = ESP_INTR_FLAG_LEVEL1;
  ESP_ERROR_CHECK(usb_host_install(&hc));
  xTaskCreatePinnedToCore(libTask, "usb_lib", 4096, nullptr, 10, nullptr, 0);

  usb_host_client_config_t cc = {};
  cc.is_synchronous    = false;
  cc.max_num_event_msg = 5;
  cc.async.client_event_callback = clientEvent;
  cc.async.callback_arg          = nullptr;
  ESP_ERROR_CHECK(usb_host_client_register(&cc, &g_client));

  usb_host_transfer_alloc(sizeof(usb_setup_packet_t) + 64, 0, &g_ctrl);
  usb_host_transfer_alloc(512, 0, &g_in);
  usb_host_transfer_alloc(64, 0, &g_out);

  xTaskCreatePinnedToCore(drvTask, "usb_drv", 4096, nullptr, 8, &g_drvTask, 0);
  xTaskCreatePinnedToCore(clientTask, "usb_cli", 4096, nullptr, 9, nullptr, 0);
}

bool connected() { return g_ready; }

size_t write(const uint8_t* data, size_t len, uint32_t timeoutMs) {
  if (!g_ready) return 0;
  if (xSemaphoreTake(g_outLock, pdMS_TO_TICKS(timeoutMs)) != pdTRUE) return 0;
  size_t sent = 0;
  while (sent < len && g_ready) {
    size_t n = min<size_t>(64, len - sent);
    memcpy(g_out->data_buffer, data + sent, n);
    g_out->num_bytes        = n;
    g_out->device_handle    = g_dev;
    g_out->bEndpointAddress = g_epOut;
    g_out->callback         = outCb;
    g_out->timeout_ms       = timeoutMs;
    if (usb_host_transfer_submit(g_out) != ESP_OK) break;
    if (xSemaphoreTake(g_outDone, pdMS_TO_TICKS(timeoutMs + 50)) != pdTRUE) break;
    if (g_out->status != USB_TRANSFER_STATUS_COMPLETED) break;
    sent += n;
  }
  xSemaphoreGive(g_outLock);
  return sent;
}

size_t read(uint8_t* buf, size_t len, uint32_t timeoutMs) {
  return xStreamBufferReceive(g_rx, buf, len, pdMS_TO_TICKS(timeoutMs));
}

void flushInput() { xStreamBufferReset(g_rx); }

}  // namespace ftdi
