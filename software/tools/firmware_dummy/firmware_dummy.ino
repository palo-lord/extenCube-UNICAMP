// firmware_dummy — finge ser o firmware do robô para validar o host sem o robô.
//
// Grave num Arduino Uno (ou qualquer placa) e rode o raiden.py no modo
// "2) Uno dummy". Responde a cada comando no formato de
// software/contracts/serial_protocol.md, sem motores nem sensores.
// O STATE devolvido é o do embaralhamento de teste T0 (R U R D L U).

const char TERM = '*';
char rx[400];
int  rxLen = 0;

// Estado do T0 (48 chars, ordem URFDLB): o solver deve resolvê-lo.
const char* TEST_STATE =
    "OBBWRYYG" "GOOBBGGR" "RRWBOOGW" "RYYYWWOG" "WRBGYOBB" "WOGYYRRW";

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.print("READY*");
}

void handle(char* cmd, int n) {
  if (n <= 0) { Serial.print("e0*"); return; }

  if (cmd[0] == 'c' && cmd[1] == '0') {            // CALIBRATE (resposta real da bancada)
    Serial.print("109.0_346.4_122.3_60.4_359.8_232.5_"
                 "0.147_0.816_0.771_0.802_0.923_0.906_0.459_19_17_9*");
    return;
  }
  if (cmd[0] == 'c' && cmd[1] == '1') {            // CALIBRATE_RO (resposta real da bancada)
    Serial.print("9.02_19.82_5.80_17.23_16.17_50.04_"
                 "12.14_31.26_11.95_19.37_7.06_19.58*");
    return;
  }
  if (cmd[0] == 's' && cmd[1] == '0') { Serial.print("111111111111*"); return; }
  if (cmd[0] == 'r' && cmd[1] == '0') { Serial.print(TEST_STATE); Serial.print(TERM); return; }

  if (cmd[0] == 'k' && cmd[1] == '_') {            // KOLOR: cor da face do NS no HOME
    int ns = atoi(cmd + 2);
    if (ns < 0 || ns > 11) { Serial.print("e3*"); return; }
    const char* COLORS = "WWRRGGYYOOBB";
    Serial.print(COLORS[ns]); Serial.print(TERM);
    return;
  }
  if (cmd[0] == 'v' && cmd[1] == '_') { Serial.print("d*"); return; }
  if (cmd[0] == 'g' && cmd[1] == '_') { Serial.print("d*"); return; }

  // MOVE: 1..N chars A-R -> DONE com tempo simulado (50 ms por movimento)
  for (int i = 0; i < n; i++)
    if (cmd[i] < 'A' || cmd[i] > 'R') { Serial.print("e1*"); return; }
  Serial.print("d_"); Serial.print(n * 0.05, 3); Serial.print(TERM);
}

void loop() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\r' || ch == '\n') continue;
    if (ch == TERM) { rx[rxLen] = '\0'; handle(rx, rxLen); rxLen = 0; }
    else if (rxLen < (int)sizeof(rx) - 1) rx[rxLen++] = ch;
    else { rxLen = 0; Serial.print("e2*"); }
  }
}
