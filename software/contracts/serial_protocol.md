# Contrato: Protocolo Serial (host ↔ firmware)

Um único link serial. O **host é mestre** e o **firmware é escravo**: o
firmware só age em resposta a um comando e nunca toma iniciativa própria.

- Baud: **115200** (casa com `host/app/communication/embedded.py`).
- Ao ligar ou resetar, o firmware emite o banner `READY*`.
- Espelhos deste contrato: `firmware/src/main.cpp` (dispatcher) e
  `host/app/communication/embedded.py` (classes `Tx`, `Rx`, `SerialLink`).

## Formato das mensagens

- Todo comando e toda resposta terminam no delimitador `*`.
- Argumentos opcionais vêm após o código, separados por `_`.
- `\r` e `\n` são ignorados pelo firmware (o Serial Monitor pode enviar LF).
- Sem checksum nesta versão.
- O firmware lê incrementalmente até o `*` e guarda a linha num buffer de
  400 bytes (`rx[400]`), então uma sequência longa de movimentos não estoura
  o buffer de hardware da serial (64 bytes).

## Host → Firmware (comandos)

| Comando | Código | Pré-condição | Resposta |
|---|---|---|---|
| SCAN | `s0*` | — | SCAN-MAP |
| CALIBRATE | `c0*` | cubo **resolvido** no HOME | CALIB |
| CALIBRATE_RO | `c1*` | cubo **resolvido** no HOME | CALIB-RO |
| SENSE | `r0*` | calibrado (`c0*`, idealmente `c1*`) | STATE |
| KOLOR | `k_<ns>*` (ex.: `k_4*`) | — | 1 char de cor |
| MOVE | `<chars>*` (ex.: `J*`, `JAJDGA*`) | — | DONE |
| SPEED | `v_<us>*` (ex.: `v_850*`) | — | DONE |
| GAP | `g_<ms>*` (ex.: `g_10*`) | — | DONE |

Todo comando que começa com letra minúscula é tratado **antes** da
interpretação como MOVE; caso contrário cairia em `e1*`.

### SCAN (`s0*`)
Self-check de hardware. Resposta: 12 chars, um por sensor, na ordem de
**canal físico** 0..11 do mux. `1` = sensor respondeu via I2C, `0` = mudo.

### CALIBRATE (`c0*`)
Cubo resolvido no HOME, sem movimento. Estabelece o balanço de branco e as
referências de cor (detalhes em `sensor_map.md`). Resposta com 16 campos:

```
H(W)_H(R)_H(G)_H(Y)_H(O)_H(B)_S(W)_S(R)_S(G)_S(Y)_S(O)_S(B)_whiteSatThresh_wR_wG_wB*
```

Erros: `e4*` (sensor sem leitura válida), `e5*` (premissa violada).

### CALIBRATE_RO (`c1*`)
Cubo resolvido no HOME. O firmware aplica dois embaralhamentos conhecidos,
sensoria cada um e desfaz:

| Etapa | Aplica | Desfaz |
|---|---|---|
| C1 | `NRK` (F' B2 R') | `JRM` (R B2 F) |
| C2 | `BQE` (U' B' D') | `DPA` (D B U) |

Como os estados são conhecidos, aprende a razão R/O típica do sensor de
centro de cada face. **O cubo termina resolvido.** Resposta com 12 campos
(par vermelho/laranja por face, ordem U R F D L B):

```
R(U)_O(U)_R(R)_O(R)_R(F)_O(F)_R(D)_O(D)_R(L)_O(L)_R(B)_O(B)*
```

Em cada face, R deve ficar bem abaixo de O. Erros: `e4*` (leitura inválida),
`e5*` (algum sensor não separou R de O; primeiro suspeito: cubo fora do HOME).

A calibração fica em RAM: refazer após reset, novo upload ou mudança de
aquisição (sensor, LED, integração, ganho). Sem `c1*`, o sensoriamento ainda
funciona (razão pura + paridade), com menos margem.

### SENSE (`r0*`)
O firmware aciona sozinho os motores para apresentar as faces aos sensores
(4× `N'` por face, o que devolve o cubo ao estado inicial), lê, classifica e
resolve R/O por peça. O host não comanda motor durante o sensoriamento.
Resposta: STATE com 48 chars (ver `cube_state.md`). Erro: `e6*`.

### KOLOR (`k_<ns>*`) — diagnóstico
Lê um único sensor lógico (`ns` 0..11, ver `sensor_map.md`) e devolve 1 char
`W R G Y O B`, ou `X` para leitura inválida. É a classificação **por adesivo**
(o R/O vem só do limiar `RO_RATIO_THRESH`, sem a resolução por peça). Erro:
`e3*` (ns fora de 0..11).

### MOVE (`<chars>*`)
Sequência de 1 a N chars do alfabeto A–R (`move_alphabet.md`). O firmware
executa a sequência inteira, acionando dois motores ao mesmo tempo quando
dois movimentos consecutivos são de faces opostas, e responde **um único**
DONE no final. Durante a execução o firmware não lê a serial.

### SPEED / GAP (`v_<us>*`, `g_<ms>*`)
Ajustam o meio-período do pulso STEP (µs) e a pausa entre movimentos (ms).
Úteis para demonstração (devagar) e testes de velocidade.

## Firmware → Host (respostas)

| Resposta | Formato | Quando |
|---|---|---|
| READY | `READY*` | boot/reset |
| DONE | `d*` ou `d_<seg>*` (ex.: `d_1.820*`) | MOVE, SPEED, GAP |
| SCAN-MAP | 12 chars `1`/`0` + `*` | `s0*` |
| CALIB | 16 floats separados por `_` + `*` | `c0*` |
| CALIB-RO | 12 floats separados por `_` + `*` | `c1*` |
| STATE | 48 chars `W R G Y O B` + `*` | `r0*` |
| cor | 1 char + `*` | `k_<ns>*` |
| ERROR | `e<n>*` | falha |

O argumento do DONE é o tempo de execução em segundos (telemetria); SPEED e
GAP respondem `d*` sem tempo.

### Códigos de erro

| Código | Significado | Exceção no host |
|---|---|---|
| `e0*` | comando desconhecido | `UnknownCommandError` |
| `e1*` | char de movimento inválido (fora de A–R) | `InvalidMoveError` |
| `e2*` | overflow da linha de recepção | `LineOverflowError` |
| `e3*` | índice de sensor inválido | `InvalidSensorError` |
| `e4*` | calibração: sensor sem leitura válida | `CalibrationReadError` |
| `e5*` | calibração: premissa violada | `CalibrationPremiseError` |
| `e6*` | sensoriamento incompleto (alguma leitura `X`) | `SenseIncompleteError` |
| `e9*` | comando não implementado (stub) | `NotImplementedFirmwareError` |

Resposta malformada ou ausente vira `ProtocolError` no host (problema de
conexão ou de timing, não recusa do firmware).

## Handshake e tempos de resposta

O host envia **um** comando e aguarda a resposta antes do próximo. Alguns
comandos levam dezenas de segundos sem enviar nada, então o host usa um
timeout **por comando** (`SerialLink` em `embedded.py`):

| Comando | Timeout no host |
|---|---|
| `s0*`, `k_*`, `v_*`, `g_*` | 5 s |
| `c0*` | 30 s |
| `r0*` | 120 s |
| `c1*` | 240 s (dois sensoriamentos completos) |
| MOVE | 300 s (soluções longas do M2OP) |

Se o firmware ficar mais lento (mais pausas, integração maior), ajuste
`TIMEOUT_*` em `embedded.py`.
