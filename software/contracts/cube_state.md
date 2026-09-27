# Contrato: Estado do Cubo (6×8 = 48)

Formato do estado do cubo entregue pelo sensoriamento (`r0*`) e consumido
pelo `solver/`.

## Dimensão

54 adesivos, dos quais 6 são centros fixos → **48 adesivos móveis** →
matriz 6×8.

## Alfabeto de cor

O firmware devolve a cor **já classificada** (inclusive com a resolução R/O
por peça, ver `sensor_map.md`), nunca RGB cru.

| Char | Cor |
|---|---|
| W | Branca |
| R | Vermelha |
| G | Verde |
| Y | Amarela |
| O | Laranja |
| B | Azul |

## Ordem das faces (linhas 0..5)

```
0=U (branca)  1=R (vermelha)  2=F (verde)  3=D (amarela)  4=L (laranja)  5=B (azul)
```

É a mesma ordem `URFDLB` usada pelo Kociemba. Convenção física: face branca
sempre para cima, face verde sempre à frente (motor designado como frente).

## Ordem dentro de cada face

Sentido horário, começando pelo adesivo superior esquerdo, pulando o centro:

```
0 1 2
7 · 3
6 5 4
```

Posições pares são quinas; ímpares são arestas.

## Indexação

```
índice = face * 8 + posição        (0..47)
```

No fio (`r0*`), o STATE é a concatenação das 6 faces nessa ordem, seguida de
`*`. No host, `SerialLink.sense()` devolve `state[face][posição]`.

## Centros e conversão para o solver

Os centros não são sensoriados. O adapter `state_to_cube_string` em
`host/solver/base.py` insere os 6 centros conhecidos, reordena cada face do
sentido horário para linha por linha (`0 1 2 / 3 4 5 / 6 7 8`) e troca cada
cor pela letra da face do HOME (W→U, R→R, G→F, Y→D, O→L, B→B), gerando a
string de 54 facelets que o Kociemba e o M2OP recebem.

No firmware, o estado vive em `scramble[6][8]` (`detect_color.cpp`), já
nesta indexação. `firmware/src/protocol/cube_state.h` está reservado para o
schema, mas hoje é só um esqueleto.
