# Guia de Calibração e Ajuste dos Sensores

Onde mexer quando a leitura de cor dá errado, organizado por **sintoma**.
Companion de `sensor_map.md`. Regra de ouro: o sintoma diz a camada; mexa em
uma camada por vez e revalide.

## Protocolo de calibração (a cada sessão)

Com o cubo **resolvido** no HOME (branco em cima, verde à frente), sem
reflexo nem sombra de mão sobre os sensores:

1. `s0*` → deve voltar `111111111111*`. Um `0` localiza um sensor mudo
   (hardware, não código).
2. `c0*` → conferir a resposta com os critérios abaixo.
3. `c1*` → leva alguns minutos e **termina com o cubo resolvido**. Conferir
   que em cada face R fica bem abaixo de O.
4. Opcional: `k_0*` … `k_11*` no resolvido, cada NS lendo a cor da sua face.

Pelo host, o passo 1 → 3 é o item **1) Preparar** do `raiden.py`.

**Refazer** após reset do Mega ou novo upload (as calibrações ficam em RAM),
ou após mudar sensor, LED, fiação, `integrationTime`, ganho ou
`SENSE_SETTLE_MS`. O `c1*` usa RGB cru, então refazer só o `c0*` não exige
refazer o `c1*`.

## Lendo a resposta do `c0*`

Formato: `H×6 _ S×6 _ whiteSatThresh _ wR _ wG _ wB` (cores W R G Y O B).

Uma calibração **boa**:

- `S(W)` é a menor saturação, com folga (ex.: ~0.15 contra cromáticas > 0.7);
- `whiteSatThresh` fica entre `S(W)` e a menor cromática, sem colar em
  nenhuma;
- `wR`, `wG`, `wB` da mesma ordem (ex.: `19_17_9`);
- `H(R)` perto de 350° e `H(O)` perto de 0°. Se `H(R)` sair "no meio do nada"
  (ex.: 290°), um sensor da face vermelha viu outra cor: cubo fora do HOME ou
  sensor desalinhado.

`H(W)` não importa (o branco é decidido por saturação).

Referência da bancada (set/2026), `integrationTime` 50 ms:

```
109.0_346.4_122.3_60.4_359.8_232.5_0.147_0.816_0.771_0.802_0.923_0.906_0.459_19_17_9
```

## Diagnóstico rápido (sintoma → onde mexer)

| Sintoma | Causa provável | Onde mexer |
|---|---|---|
| `c0*` ou `c1*` volta `e5*` logo de cara | cubo fora do HOME | reposicionar e repetir |
| R↔O trocados no `r0*` | viés entre sensores | refazer `c1*`; conferir face L (a mais apertada) |
| Branco vira amarelo, ou cromática vira branco | referência de branco ruim | refazer `c0*` sem reflexo |
| Erros de cor espalhados, que mudam a cada leitura | cross-talk ou luz ambiente | conferir LEDs individuais (só um aceso por leitura) |
| `X` intermitente / leitura instável | settle curto ou ruído I2C | `SENSE_SETTLE_MS`, timeout do `senseRaw` |
| `X` sempre no mesmo sensor, `e6*` | contato ou solda | hardware: `s0*` e `k_<ns>*` para localizar |
| Azul lê morto (`soma` ~0) | pouca luz | subir `integrationTime` |
| Cores certas, **posições** trocadas | tabela `POS` | `sense_complete.cpp` (não é calibração) |

## Camada 1 — Aquisição (sensor)

`firmware/src/sensing/scan.cpp`, em `sensingInit()`:

```cpp
tcs.integrationTime(50);          // ms
tcs.gain(TCS34725::Gain::X01);
```

`firmware/src/sensing/sensing.h` e `detect_color.cpp` (`senseRaw`):

```cpp
#define SENSE_SETTLE_MS 50        // espera após acender o LED / trocar canal
// + delay(50) antes e depois, descarte da 1ª integração, timeout de 300 ms
```

| Parâmetro | Efeito | Quando mexer |
|---|---|---|
| `integrationTime` | maior = mais luz e mais estável, porém mais lento | azul fraco → subir; algo saturando → descer |
| `gain` | maior clareia cores escuras, arrisca saturar as claras | só se o azul continuar fraco com integração alta |
| `SENSE_SETTLE_MS` | tempo para o LED estabilizar | leituras instáveis logo após trocar sensor |

Qualquer mudança aqui exige refazer `c0*` e `c1*`.

## Camada 2 — Referências de cor (`c0*`)

Geradas pela calibração, não editar à mão (`detect_color.cpp`):
`whiteBal[3]`, `globalRef[6]`, `whiteSatThresh`. Os `DEFAULT_HUE` só valem
antes do primeiro `c0*`.

## Camada 3 — Referência R/O (`c1*`)

`sense_complete.cpp`: `roMid[6]`, `roHalf[6]`, aprendidos com os scrambles
`NRK` e `BQE`. A decisão R/O final **não** usa limiar: vem da resolução por
peça (quiralidade, pares de arestas, paridade; ver `sensor_map.md`).

O `RO_RATIO_THRESH` em `detect_color.cpp` só afeta o palpite do `k_<ns>*`.
Não adianta ajustá-lo para corrigir o `r0*`.

## Camada 4 — Auto-validação do `c0*`

`firmware/src/sensing/calibration.cpp`, fim de `calibrateSolved()`:

```cpp
if (globalRef[0].s >= 0.5f * minChroma) return 5;   // branco não dessaturou
if (globalRef[c].s < 0.30f) return 5;               // cromática morta
if (wmax > 10.0f * wmin) return 5;                  // reflexo no branco
```

Calibração boa sendo recusada → afrouxar o limiar correspondente; calibração
ruim passando → apertar.

## Camada 5 — Índice de gravação (não é calibração)

`sense_complete.cpp`, tabela `POS[face][papel][passo]`:

```cpp
/* U */ { {0,2,4,6}, {1,3,5,7} },
/* R */ { {0,2,4,6}, {1,3,5,7} },
/* F */ { {0,2,4,6}, {1,3,5,7} },
/* D */ { {6,0,2,4}, {7,1,3,5} },
/* L */ { {0,2,4,6}, {1,3,5,7} },
/* B */ { {0,2,4,6}, {1,3,5,7} },
```

- Invariante: `centro[k] == quina[k] + 1` (sensores em adesivos vizinhos).
- Passo: `(início_HOME + 2*k) % 8`, porque cada `N'` traz o adesivo seguinte
  (no sentido horário) para baixo do sensor.
- Teste: cubo resolvido → `A*` (U) → `r0*`. Cada face lateral deve ter
  exatamente 3 adesivos trocados, no topo (posições 0, 1, 2).

## Validação com embaralhamentos conhecidos

Para cada teste: cubo resolvido → enviar → `r0*` e comparar → desfazer.

| Teste | Scramble | Enviar | Estado esperado (`r0*`) | Desfazer |
|---|---|---|---|---|
| T0 | R U R D L U | `JAJDGA*` | `OBBWRYYG GOOBBGGR RRWBOOGW RYYYWWOG WRBGYOBB WOGYYRRW` | `BHEKBK*` |
| T1 | F R U' B D' L2 | `MJBPEI*` | `BRROOWRR GGBYWBBR YOYYYRWW RBOOOYWW YGGGGBBY WWRGOOGB` | `IDQAKN*` |
| T2 | R2 D F' U L' B2 R' | `LDNAHRK*` | `WWGRRYGG BBOGYYGB ORYWYGWY ROROOWWB BWWBGOBR YRRGOOBY` | `JRGBMEL*` |
| T3 | U F2 L' D R B' U2 F L D2 | `AOHDJQCMGF*` | `WYRGGOBR RRBWOBGG OYYWRWYG OBWOGRYB OYYOGRBB WGBYRWWO` | `FHNCPKEGOB*` |
| T4 | B L U' R2 F D' B2 U R' L | `PGBLMERAKG*` | `GRYYYYGG OOBBWBWO ORGGGGOO BWRWRWOG RRWWWYBB RBYYYRBO` | `HJBRDNLAHQ*` |

O `r0*` devolve os 48 chars colados (os espaços acima separam as faces).
Resultado de set/2026: 48/48 nos cinco testes.
