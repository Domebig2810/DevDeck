#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define TCA_ADDR 0x70
#define NUM_OLEDS 6
Adafruit_SSD1306 oled(128, 64, &Wire, -1);

void tcaSelect(uint8_t channel) {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Wire.begin();
  Wire.setClock(400000);
  Serial.println("Initialisiere alle OLEDs...");

  for (uint8_t ch = 0; ch < NUM_OLEDS; ch++) {
    tcaSelect(ch);
    if (!oled.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
      Serial.print("OLED "); Serial.print(ch); Serial.println(" NICHT gefunden!");
      continue;
    }
    oled.clearDisplay();
    oled.setTextSize(3);
    oled.setTextColor(SSD1306_WHITE);
    oled.setCursor(40, 20);
    oled.print("#"); oled.print(ch + 1);
    oled.display();
    Serial.print("OLED "); Serial.print(ch); Serial.println(" OK");
  }
  Serial.println("Fertig!");
}
void loop() {}
