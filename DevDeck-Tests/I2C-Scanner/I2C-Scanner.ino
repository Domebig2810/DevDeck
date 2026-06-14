#include <Wire.h>

void setup() {
  Serial.begin(115200);
  delay(1500);
  Wire.begin();
  Serial.println("Scanning...");
  for (byte a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.print("Gefunden: 0x");
      Serial.println(a, HEX);
    }
  }
  Serial.println("Fertig.");
}
void loop() {}