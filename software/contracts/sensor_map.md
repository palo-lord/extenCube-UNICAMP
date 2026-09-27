# Contrato: Mapa dos Sensores e Pipeline de Cor

Identidade dos 12 TCS34725, sua relação com faces, adesivos e multiplexador,
e como a cor de cada adesivo é decidida.
Depende de: `cube_state.md` (faces e índices) e `move_alphabet.md`.
Biblioteca: `TCS34725.h` (hideakitai), **instância única** re-selecionada
via mux (todos os sensores têm o mesmo endereço I2C).

## Faces (idêntico a `cube_state.md`)

`U=0  R=1  F=2  D=3  L=4  B=5`

HOME do robô: face branca (U) para cima, face verde (F) à frente.
Cores no HOME: U=Branca, R=Vermelha, F=Verde, D=Amarela, L=Laranja, B=Azul.

## Dois sensores por face

- **QUINA** (tag `q`): lê um adesivo de canto (posições pares 0, 2, 4, 6).
- **CENTRO** (tag `c`): lê um adesivo de aresta (posições ímpares 1, 3, 5, 7).

"Centro" é o adesivo do meio da borda (aresta), **não** o centro fixo da
face. Os dois sensores leem adesivos móveis, sempre vizinhos: a aresta é a
vizinha horária da quina.

## Número do Sensor lógico (NS)

`NS = 2*face + papel` (papel: 0 = quina, 1 = centro). As estruturas de dados
usam sempre o NS lógico, na ordem de contrato.

| NS | Tag | Face | Papel | Cor no HOME | Canal físico do mux | Pino do LED |
|---|---|---|---|---|---|---|
| 0 | Uq | Up | quina | Branca | 2 | 24 |
| 1 | Uc | Up | centro | Branca | 3 | 25 |
| 2 | Rq | Right | quina | Vermelha | 4 | 26 |
| 3 | Rc | Right | centro | Vermelha | 5 | 27 |
| 4 | Fq | Front | quina | Verde | 6 | 28 |
| 5 | Fc | Front | centro | Verde | 7 | 29 |
| 6 | Dq | Down | quina | Amarela | 10 | 32 |
| 7 | Dc | Down | centro | Amarela | 11 | 33 |
| 8 | Lq | Left | quina | Laranja | 8 | 30 |
| 9 | Lc | Left | centro | Laranja | 9 | 31 |
| 10 | Bq | Back | quina | Azul | 0 | 22 |
| 11 | Bc | Back | centro | Azul | 1 | 23 |

## Indireção da fiação (hardware pronto, imutável)

A fiação **não** segue `NS = 2*face + papel`. Só a seleção física é
remapeada; o resto do código trabalha em NS lógico:

```cpp
MUX_CHANNEL[NS] = {2,3, 4,5, 6,7, 10,11, 8,9, 0,1};   // scan.cpp
LED_GPIO[canal físico] = {22, 23, ..., 33};             // scan.cpp
```

Canais físicos por face: Back=0,1 · Up=2,3 · Right=4,5 · Front=6,7 ·
Left=8,9 · Down=10,11.

## Fiação

- Barramento compartilhado: VIN (5 V), GND, SCL.
- Por sensor: **SDA** pelo mux CD74HC4067 (seleção S0..S3 nos pinos 11, 10,
  9, 8; S0 = LSB) e **LED** num GPIO próprio (22..33), indexado pelo canal
  físico do mesmo módulo.
- LEDs individuais: só o LED do sensor lido fica aceso durante a leitura.
  Isso eliminou o cross-talk entre sensores vizinhos (a causa dos erros
  aleatórios de cor antes dessa mudança).
- Cores de jumper da bancada: LED=azul, SDA=verde, SCL=amarelo,
  GND=laranja, VIN=vermelho.

## Leitura de um adesivo (`senseRaw`, `detect_color.cpp`)

1. seleciona o canal do mux e acende **só** o LED daquele sensor;
2. espera a luz estabilizar e descarta a primeira integração;
3. lê o RGBC cru e apaga o LED.

Com `SENSE_DEBUG 1` cada leitura é impressa como `[DBG ns=.. rgb=..]`.
**Deve ficar em 0 para rodar com o host**, porque as linhas de debug não
terminam em `*` e quebram o parser.

## Classificação por adesivo

1. **Balanço de branco (von Kries).** O RGB é dividido por `whiteBal`, a
   resposta do sensor à face branca medida no `c0*`. O TCS34725 não responde
   a um alvo neutro com R=G=B; sem essa correção o branco sai com cor falsa
   e colide com o amarelo.
2. **Branco por saturação.** Após o balanço, o branco é acromático:
   `S < whiteSatThresh` → `W`. O hue do branco é irrelevante.
3. **Demais cores por hue.** Menor distância angular aos 5 hues de
   referência (`globalRef`, calibrados no `c0*`, iguais para os 12 sensores).
4. **R/O provisório.** Vermelho e laranja ficam a poucos graus de hue. Aqui
   só se decide que o adesivo é "R ou O"; o palpite pela razão
   `(r - g - b) / b` contra `RO_RATIO_THRESH` vale apenas para o `k_<ns>*`.

## Resolução R/O por peça (`sense_complete.cpp`)

Nenhuma métrica por adesivo separa vermelho de laranja com segurança: cada
sensor tem seu brilho, e o vermelho de um sensor forte se parece com o
laranja de um sensor fraco. Depois das 48 leituras, o firmware decide R/O
usando a estrutura do cubo:

1. **Quinas por quiralidade.** Toda quina tem três cores numa ordem horária
   fixa (ex.: `W-R-G`). Com as duas cores confiáveis e suas posições, a
   terceira é determinada. Não usa medida.
2. **Arestas por pares.** Cada cor confiável (W, Y, G, B) aparece em duas
   arestas com R/O, uma vermelha e uma laranja. Entre as duas, a de maior
   pontuação R/O é a laranja. A pontuação é o log da razão, normalizado pela
   referência R/O daquele sensor (`c1*`); sem `c1*`, usa a razão pura.
3. **Paridade.** Num cubo real, a permutação das arestas e a das quinas têm
   a mesma paridade. Trocar o R/O de um par de arestas quebra isso; se
   quebrar, o firmware inverte o par com a decisão mais apertada.

Se algo não bater (peça com duas cores ambíguas, grupo com mais de 2
arestas), o firmware não força nada: mantém a leitura, e o solver recusa o
estado se ele for inválido.

## Calibrações

| Comando | Cubo | Aprende | Detalhes |
|---|---|---|---|
| `c0*` | resolvido, sem movimento | `whiteBal`, `globalRef`, `whiteSatThresh` | premissas abaixo |
| `c1*` | resolvido, com 2 scrambles | referência R/O por face | `serial_protocol.md` |

### Premissas de um `c0*` válido (auto-validadas, falha → `e5*`)

- O branco é a cor **menos** saturada, com folga:
  `S(W) < 0.5 × menor S cromática`.
- Toda cor cromática tem saturação viva (`S > 0.30`).
- `wR`, `wG`, `wB` da mesma ordem de grandeza (razão < 10), senão há reflexo
  na face branca.

Ver critérios de leitura da resposta em `calibration.md`.

## Validação na bancada (set/2026)

Com `s0* → c0* → c1*` e os embaralhamentos de teste T0–T4 (5 a 10
movimentos, as 6 faces), o `r0*` acertou **48/48 nos cinco**. A referência
R/O medida no `c1*`:

| Face | U | R | F | D | L | B |
|---|---|---|---|---|---|---|
| R | 9.02 | 5.80 | 16.17 | 12.14 | 11.95 | 7.06 |
| O | 19.82 | 17.23 | 50.04 | 31.26 | 19.37 | 19.58 |

A face L (ns 9) é a mais apertada (O/R ≈ 1.6×): se um erro de R/O aparecer,
é o primeiro suspeito.
