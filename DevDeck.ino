/*
 * Stream Deck – Arduino UNO R4 WiFi
 * JSON-Kommunikation mit PC-Skript.
 *
 * Layout:
 *   [ENC 0]   [OLED 0]  [OLED 1]
 *   [ENC 1]   [OLED 2]  [OLED 3]
 *   [ENC 2]   [OLED 4]  [OLED 5]
 *
 * --- VOM ARDUINO ZUM PC ---
 *   {"event":"ready"}
 *   {"event":"encoder","index":0,"value":1}        // +1 oder -1
 *   {"event":"encoder_button","index":0,"value":1} // 1=press, 0=release
 *   {"event":"button","index":3,"value":1}         // 1=press, 0=release
 *
 * --- VOM PC ZUM ARDUINO ---
 *   {"cmd":"image","slot":2,"data":"<base64>"}                // 1024 Byte Bitmap
 *   {"cmd":"overlay","slot":2,"label":"VOL","value":75,"duration_ms":1000}
 *   {"cmd":"clear","slot":2}
 *   {"cmd":"flash","slot":3}
 *
 * Benötigte Libraries (Library Manager):
 *   - Adafruit SSD1306
 *   - Adafruit GFX
 *   - RotaryEncoder by Matthias Hertel
 *   - ArduinoJson by Benoit Blanchon
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <RotaryEncoder.h>
#include <ArduinoJson.h>

// ───── Pin-Belegung ─────
const uint8_t ENC_SW[3]  = { 4, 7, 10 };
const uint8_t BTN_PINS[6] = { A0, A1, A2, A3, A4, A5 };

// ───── TCA9548A + OLEDs ─────
#define TCA_ADDR 0x70
#define NUM_OLEDS 6
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

void tcaSelect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

// ───── Encoder ─────
RotaryEncoder enc0(3, 2, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder enc1(6, 5, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder enc2(9, 8, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder* encoders[3] = { &enc0, &enc1, &enc2 };
int lastEncPos[3] = { 0, 0, 0 };

// Layout: welche zwei OLEDs gehören zu welchem Encoder
// Encoder 0 -> Slots 0+1, Encoder 1 -> Slots 2+3, Encoder 2 -> Slots 4+5
const uint8_t ENC_SLOTS[3][2] = { {0,1}, {2,3}, {4,5} };

// ───── Button-Debouncing ─────
struct BtnState {
  bool stable;
  bool lastReading;
  uint32_t lastChange;
};
BtnState btns[6];
BtnState encBtns[3];
const uint16_t DEBOUNCE_MS = 25;

// Forward-Declaration verhindert, dass die Arduino-IDE einen falschen
// Auto-Prototype generiert, bevor sie BtnState kennt.
bool debouncedRead(uint8_t pin, BtnState& st);

bool debouncedRead(uint8_t pin, BtnState& st) {
  bool reading = digitalRead(pin) == LOW;
  uint32_t now = millis();
  if (reading != st.lastReading) {
    st.lastReading = reading;
    st.lastChange = now;
  }
  if ((now - st.lastChange) > DEBOUNCE_MS && reading != st.stable) {
    st.stable = reading;
    return true;
  }
  return false;
}

// ───── OLED-Zustand pro Slot ─────
struct SlotState {
  uint8_t image[1024];
  bool hasImage;

  bool overlayActive;
  uint32_t overlayUntil;
  char overlayLabel[16];
  int overlayValue;

  uint32_t flashUntil;
};
SlotState slots[NUM_OLEDS];

void drawSlot(uint8_t slot) {
  if (slot >= NUM_OLEDS) return;
  tcaSelect(slot);
  oled.clearDisplay();

  bool invert = slots[slot].flashUntil > millis();

  if (slots[slot].overlayActive) {
    uint16_t fg = invert ? SSD1306_BLACK : SSD1306_WHITE;
    if (invert) oled.fillRect(0, 0, 128, 64, SSD1306_WHITE);
    oled.setTextColor(fg);
    oled.drawRect(0, 0, 128, 64, fg);

    oled.setTextSize(1);
    oled.setCursor(6, 6);
    oled.print(slots[slot].overlayLabel);

    int v = slots[slot].overlayValue;
    oled.setTextSize(3);
    int x = (v < 10) ? 50 : (v < 100) ? 38 : 26;
    if (v < 0) x = 32;
    oled.setCursor(x, 22);
    oled.print(v);

    int barW = map(constrain(v, 0, 100), 0, 100, 0, 116);
    oled.fillRect(6, 54, barW, 6, fg);
  }
  else if (slots[slot].hasImage) {
    oled.drawBitmap(0, 0, slots[slot].image, 128, 64,
                    invert ? SSD1306_BLACK : SSD1306_WHITE,
                    invert ? SSD1306_WHITE : SSD1306_BLACK);
  }
  else {
    oled.setTextColor(SSD1306_WHITE);
    oled.drawRect(0, 0, 128, 64, SSD1306_WHITE);
    oled.setTextSize(1);
    oled.setCursor(20, 28);
    oled.print("Slot ");
    oled.print(slot);
  }

  oled.display();
}

// ───── Base64-Decoder ─────
static const int8_t b64lookup[256] = {
  -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
  -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
  -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,62,-1,-1,-1,63,
  52,53,54,55,56,57,58,59,60,61,-1,-1,-1,-1,-1,-1,
  -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,
  15,16,17,18,19,20,21,22,23,24,25,-1,-1,-1,-1,-1,
  -1,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,
  41,42,43,44,45,46,47,48,49,50,51,-1,-1,-1,-1,-1,
};

int base64Decode(const char* src, uint8_t* dst, size_t maxOut) {
  size_t outLen = 0;
  uint32_t buf = 0;
  int bits = 0;
  while (*src && outLen < maxOut) {
    char c = *src++;
    if (c == '=' || c == '\n' || c == '\r' || c == ' ') continue;
    int8_t v = b64lookup[(uint8_t)c];
    if (v < 0) continue;
    buf = (buf << 6) | v;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      dst[outLen++] = (buf >> bits) & 0xFF;
    }
  }
  return outLen;
}

// ───── Serial-Verarbeitung ─────
String serialBuffer;
const size_t MAX_LINE = 2500;

void handleCommand(const String& line) {
  DynamicJsonDocument doc(3000);
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    Serial.print("{\"event\":\"error\",\"msg\":\"json:");
    Serial.print(err.c_str());
    Serial.println("\"}");
    return;
  }

  const char* cmd = doc["cmd"] | "";
  int slot = doc["slot"] | -1;
  if (slot < 0 || slot >= NUM_OLEDS) return;

  if (strcmp(cmd, "image") == 0) {
    const char* data = doc["data"] | "";
    int n = base64Decode(data, slots[slot].image, 1024);
    slots[slot].hasImage = (n == 1024);
    drawSlot(slot);
  }
  else if (strcmp(cmd, "overlay") == 0) {
    const char* label = doc["label"] | "";
    int value = doc["value"] | 0;
    uint32_t dur = doc["duration_ms"] | 1000;
    slots[slot].overlayActive = true;
    slots[slot].overlayUntil = millis() + dur;
    strncpy(slots[slot].overlayLabel, label, sizeof(slots[slot].overlayLabel) - 1);
    slots[slot].overlayLabel[sizeof(slots[slot].overlayLabel) - 1] = 0;
    slots[slot].overlayValue = value;
    drawSlot(slot);
  }
  else if (strcmp(cmd, "clear") == 0) {
    slots[slot].hasImage = false;
    slots[slot].overlayActive = false;
    drawSlot(slot);
  }
  else if (strcmp(cmd, "flash") == 0) {
    slots[slot].flashUntil = millis() + 150;
    drawSlot(slot);
  }
}

void processSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      if (serialBuffer.length() > 0) {
        handleCommand(serialBuffer);
        serialBuffer = "";
      }
    } else if (c != '\r') {
      serialBuffer += c;
      if (serialBuffer.length() > MAX_LINE) {
        serialBuffer = "";
      }
    }
  }
}

void sendEvent(const char* type, int index, int value) {
  Serial.print("{\"event\":\"");
  Serial.print(type);
  Serial.print("\",\"index\":");
  Serial.print(index);
  Serial.print(",\"value\":");
  Serial.print(value);
  Serial.println("}");
}

// ───── Setup ─────
void setup() {
  Serial.begin(115200);
  delay(1500);

  for (int i = 0; i < 3; i++) pinMode(ENC_SW[i], INPUT_PULLUP);
  for (int i = 0; i < 6; i++) pinMode(BTN_PINS[i], INPUT_PULLUP);

  for (int i = 0; i < NUM_OLEDS; i++) {
    slots[i].hasImage = false;
    slots[i].overlayActive = false;
    slots[i].flashUntil = 0;
  }

  Wire.begin();
  Wire.setClock(400000);

  for (uint8_t ch = 0; ch < NUM_OLEDS; ch++) {
    tcaSelect(ch);
    oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
    drawSlot(ch);
  }

  Serial.println("{\"event\":\"ready\"}");
}

// ───── Hauptschleife ─────
void loop() {
  uint32_t now = millis();
  processSerial();

  for (int i = 0; i < 3; i++) {
    encoders[i]->tick();
    int pos = encoders[i]->getPosition();
    int delta = pos - lastEncPos[i];
    if (delta != 0) {
      lastEncPos[i] = pos;
      sendEvent("encoder", i, delta);
    }
  }

  for (int i = 0; i < 3; i++) {
    if (debouncedRead(ENC_SW[i], encBtns[i])) {
      sendEvent("encoder_button", i, encBtns[i].stable ? 1 : 0);
    }
  }

  for (int i = 0; i < 6; i++) {
    if (debouncedRead(BTN_PINS[i], btns[i])) {
      sendEvent("button", i, btns[i].stable ? 1 : 0);
    }
  }

  for (int i = 0; i < NUM_OLEDS; i++) {
    if (slots[i].overlayActive && slots[i].overlayUntil <= now) {
      slots[i].overlayActive = false;
      drawSlot(i);
    }
    if (slots[i].flashUntil != 0 && slots[i].flashUntil <= now) {
      slots[i].flashUntil = 0;
      drawSlot(i);
    }
  }
}
