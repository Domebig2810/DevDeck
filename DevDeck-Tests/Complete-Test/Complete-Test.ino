#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <RotaryEncoder.h>

const uint8_t BTN_PINS[6] = { A0, A1, A2, A3, 11, 12 };
const uint8_t ENC_SW[3]   = { 4, 7, 10 };

RotaryEncoder enc0(3, 2, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder enc1(6, 5, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder enc2(9, 8, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder* encoders[3] = { &enc0, &enc1, &enc2 };
int lastEncPos[3] = { 0, 0, 0 };

#define TCA_ADDR 0x70
#define NUM_OLEDS 6
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

void tcaSelect(uint8_t ch) {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);
  Wire.endTransmission();
}

bool lastBtn[6]    = { HIGH,HIGH,HIGH,HIGH,HIGH,HIGH };
bool lastEncBtn[3] = { HIGH,HIGH,HIGH };
unsigned long lastBtnTime[6]    = {0};
unsigned long lastEncBtnTime[3] = {0};
const uint16_t DEBOUNCE = 25;
unsigned long lastStatus = 0;

void setup() {
  Serial.begin(115200);
  delay(1500);
  for (int i = 0; i < 6; i++) pinMode(BTN_PINS[i], INPUT_PULLUP);
  for (int i = 0; i < 3; i++) pinMode(ENC_SW[i],   INPUT_PULLUP);

  Wire.begin();
  Wire.setClock(400000);

  Serial.println("===========================================");
  Serial.println("  DEVDECK KOMPLETT-TEST");
  Serial.println("===========================================");

  Serial.println("\n--- I2C-Scanner ---");
  for (byte a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.print("  Gefunden: 0x"); Serial.println(a, HEX);
    }
  }

  Serial.println("\n--- OLED-Test ---");
  for (uint8_t ch = 0; ch < NUM_OLEDS; ch++) {
    tcaSelect(ch);
    if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
      Serial.print("  OLED "); Serial.print(ch); Serial.println(": FEHLER");
    } else {
      oled.clearDisplay();
      oled.setTextSize(3);
      oled.setTextColor(SSD1306_WHITE);
      oled.setCursor(36, 18);
      oled.print("#"); oled.print(ch + 1);
      oled.display();
      Serial.print("  OLED "); Serial.print(ch); Serial.println(": OK");
    }
  }

  Serial.println("\n--- Live-Test gestartet ---\n");
}

void loop() {
  unsigned long now = millis();

  for (int i = 0; i < 3; i++) {
    encoders[i]->tick();
    int pos = encoders[i]->getPosition();
    int delta = pos - lastEncPos[i];
    if (delta != 0) {
      lastEncPos[i] = pos;
      Serial.print("ENC"); Serial.print(i);
      Serial.print(": "); Serial.print(delta > 0 ? "+" : "");
      Serial.print(delta);
      Serial.print("  (Pos: "); Serial.print(pos); Serial.println(")");
    }
  }

  for (int i = 0; i < 3; i++) {
    bool state = digitalRead(ENC_SW[i]) == LOW;
    if (state != lastEncBtn[i] && (now - lastEncBtnTime[i]) > DEBOUNCE) {
      lastEncBtnTime[i] = now;
      lastEncBtn[i] = state;
      Serial.print("ENC"); Serial.print(i);
      Serial.println(state ? "_BTN: GEDRUECKT" : "_BTN: losgelassen");
    }
  }

  for (int i = 0; i < 6; i++) {
    bool state = digitalRead(BTN_PINS[i]) == LOW;
    if (state != lastBtn[i] && (now - lastBtnTime[i]) > DEBOUNCE) {
      lastBtnTime[i] = now;
      lastBtn[i] = state;
      Serial.print("BTN"); Serial.print(i);
      Serial.print(i < 4 ? " (A" : " (D");
      Serial.print(i < 4 ? i : (i == 4 ? 11 : 12));
      Serial.println(state ? "): GEDRUECKT" : "): losgelassen");
    }
  }

  if (now - lastStatus >= 2000) {
    lastStatus = now;
    Serial.print("STATUS | BTN: ");
    for (int i = 0; i < 6; i++) Serial.print(digitalRead(BTN_PINS[i]) == LOW ? "1" : "0");
    Serial.print("  ENC_SW: ");
    for (int i = 0; i < 3; i++) Serial.print(digitalRead(ENC_SW[i]) == LOW ? "1" : "0");
    Serial.print("  ENC_POS: ");
    for (int i = 0; i < 3; i++) {
      Serial.print(encoders[i]->getPosition());
      if (i < 2) Serial.print("/");
    }
    Serial.println();
  }
}