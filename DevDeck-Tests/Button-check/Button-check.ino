const int buttonPins[6] = {A0, A1, A2, A3, 11, 12};
bool lastState[6] = {HIGH, HIGH, HIGH, HIGH, HIGH, HIGH};

void setup() {
  Serial.begin(115200);
  delay(1500);
  for (int i = 0; i < 6; i++) pinMode(buttonPins[i], INPUT_PULLUP);
  Serial.println("Button-Test. A0-A3 = Btn0-3, D11 = Btn4, D12 = Btn5");
}

void loop() {
  for (int i = 0; i < 6; i++) {
    bool state = digitalRead(buttonPins[i]);
    if (state != lastState[i]) {
      delay(20);
      state = digitalRead(buttonPins[i]);
      if (state != lastState[i]) {
        Serial.print("Taste "); Serial.print(i);
        Serial.println(state == LOW ? " GEDRUECKT" : " losgelassen");
        lastState[i] = state;
      }
    }
  }
}