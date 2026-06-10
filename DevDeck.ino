#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <RotaryEncoder.h>

#define TCA_ADDR 0x70
#define NUM_OLEDS 6
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

void tcaSelect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

RotaryEncoder enc0(3, 2, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder enc1(6, 5, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder enc2(9, 8, RotaryEncoder::LatchMode::FOUR3);
RotaryEncoder* encoders[3] = { &enc0, &enc1, &enc2 };
const int SW_PINS[3] = { 4, 7, 10 };

int values[3] = { 50, 50, 50 };
int lastPosition[3] = { 0, 0, 0 };
bool lastButton[3] = { HIGH, HIGH, HIGH };
unsigned long pressTime[3] = { 0, 0, 0 };

char labels[3][16] = { "VOL", "MIC", "CAM" };

// Serial input buffer
String serialBuf = "";

void drawValue(uint8_t channel, const char* label, int value, bool pressed) {
  tcaSelect(channel);
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);

  oled.drawRect(0, 0, 128, 64, SSD1306_WHITE);

  oled.setTextSize(1);
  oled.setCursor(6, 6);
  oled.print(label);

  if (pressed) {
    oled.setTextSize(2);
    oled.setCursor(28, 28);
    oled.print("PRESS");
  } else {
    oled.setTextSize(3);
    int x = (value < 10) ? 50 : (value < 100) ? 38 : 26;
    oled.setCursor(x, 22);
    oled.print(value);

    int barW = map(value, 0, 100, 0, 116);
    oled.fillRect(6, 54, barW, 6, SSD1306_WHITE);
  }

  oled.display();
}

// Parse incoming serial commands: LABEL:i:TEXT  or  VAL:i:NUM
void handleSerialCommand(const String& line) {
  if (line.startsWith("LABEL:")) {
    int c1 = line.indexOf(':', 6);
    if (c1 < 0) return;
    int idx = line.substring(6, c1).toInt();
    if (idx < 0 || idx > 2) return;
    String text = line.substring(c1 + 1);
    text.trim();
    text.toCharArray(labels[idx], sizeof(labels[idx]));
    drawValue(idx * 2,     labels[idx], values[idx], false);
    drawValue(idx * 2 + 1, labels[idx], values[idx], false);
  } else if (line.startsWith("VAL:")) {
    int c1 = line.indexOf(':', 4);
    if (c1 < 0) return;
    int idx = line.substring(4, c1).toInt();
    if (idx < 0 || idx > 2) return;
    int val = line.substring(c1 + 1).toInt();
    values[idx] = constrain(val, 0, 100);
    drawValue(idx * 2,     labels[idx], values[idx], false);
    drawValue(idx * 2 + 1, labels[idx], values[idx], false);
  }
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();
  Wire.setClock(400000);

  for (int i = 0; i < 3; i++) {
    pinMode(SW_PINS[i], INPUT_PULLUP);
  }

  for (uint8_t ch = 0; ch < NUM_OLEDS; ch++) {
    tcaSelect(ch);
    if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) continue;
  }

  for (int i = 0; i < 3; i++) {
    drawValue(i * 2,     labels[i], values[i], false);
    drawValue(i * 2 + 1, labels[i], values[i], false);
  }
  Serial.println("READY");
}

void loop() {
  // Read incoming serial commands
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      serialBuf.trim();
      if (serialBuf.length() > 0) handleSerialCommand(serialBuf);
      serialBuf = "";
    } else {
      serialBuf += c;
    }
  }

  unsigned long now = millis();

  for (int i = 0; i < 3; i++) {
    encoders[i]->tick();

    int pos = encoders[i]->getPosition();
    if (pos != lastPosition[i]) {
      int delta = pos - lastPosition[i];
      lastPosition[i] = pos;

      values[i] = constrain(values[i] + delta, 0, 100);

      drawValue(i * 2,     labels[i], values[i], false);
      drawValue(i * 2 + 1, labels[i], values[i], false);

      // ENC:index:delta
      Serial.print("ENC:");
      Serial.print(i);
      Serial.print(":");
      Serial.println(delta);
    }

    bool button = digitalRead(SW_PINS[i]);
    if (button != lastButton[i]) {
      delay(20);
      button = digitalRead(SW_PINS[i]);
      if (button != lastButton[i]) {
        lastButton[i] = button;
        if (button == LOW) {
          pressTime[i] = now;
          drawValue(i * 2,     labels[i], values[i], true);
          drawValue(i * 2 + 1, labels[i], values[i], true);
          // BTN:index
          Serial.print("BTN:");
          Serial.println(i);
        }
      }
    }

    if (pressTime[i] != 0 && now - pressTime[i] > 800) {
      pressTime[i] = 0;
      drawValue(i * 2,     labels[i], values[i], false);
      drawValue(i * 2 + 1, labels[i], values[i], false);
    }
  }
}
