#include <Wire.h>
#define TCA_ADDR 0x70

void tcaSelect(uint8_t ch) {
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << ch);
  Wire.endTransmission();
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Wire.begin();
  Wire.setClock(400000);

  for (uint8_t ch = 0; ch < 6; ch++) {
    tcaSelect(ch);
    Wire.beginTransmission(0x3C);
    bool found = (Wire.endTransmission() == 0);
    Serial.print("Kanal "); Serial.print(ch);
    Serial.print(" (OLED "); Serial.print(ch + 1); Serial.print("): ");
    Serial.println(found ? "OK" : "NICHT GEFUNDEN");
  }
}
void loop() {}