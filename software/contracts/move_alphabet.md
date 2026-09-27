# Contrato: Alfabeto de Movimentos (A–R)

Fonte única da notação de movimentos. Cada movimento vai pela serial como
**um caractere ASCII** `A`..`R`, para máxima velocidade de comunicação.

> A ordem das faces nas letras (U, D, L, R, F, B) é a da Tabela 1 do artigo e
> **difere** da ordem das faces no estado (`URFDLB`, ver `cube_state.md`).
> Não confundir as duas.

## Onde a tradução acontece (toda no host)

```
solver → notação de cubo (U, U', U2, ...)
       → host/solver/base.py traduz para 'A'..'R'  (MOVE_TABLE, to_robot_sequence)
       → firmware recebe só a letra e a mapeia na LUT (índice 0..17)
```

- `MOVE_TABLE` em `host/solver/base.py` é o espelho desta tabela no host.
- `embedded.py` **não** traduz: só valida que os chars estão em A..R.
- O firmware nunca vê a notação de cubo. A tabela `MOVES` em
  `firmware/src/motion/motion.cpp` é o espelho desta tabela no firmware.
  (`firmware/src/protocol/protocol.h` está reservado para centralizar esses
  códigos, mas hoje é só um esqueleto.)

## Tabela canônica

| Notação | Descrição | Ângulo | Char | Índice LUT |
|---|---|---|---|---|
| U | Superior horário | 90° | A | 0 |
| U' | Superior anti-horário | −90° | B | 1 |
| U2 | Superior duplo | 180° | C | 2 |
| D | Inferior horário | 90° | D | 3 |
| D' | Inferior anti-horário | −90° | E | 4 |
| D2 | Inferior duplo | 180° | F | 5 |
| L | Esquerda horário | 90° | G | 6 |
| L' | Esquerda anti-horário | −90° | H | 7 |
| L2 | Esquerda duplo | 180° | I | 8 |
| R | Direita horário | 90° | J | 9 |
| R' | Direita anti-horário | −90° | K | 10 |
| R2 | Direita duplo | 180° | L | 11 |
| F | Frontal horário | 90° | M | 12 |
| F' | Frontal anti-horário | −90° | N | 13 |
| F2 | Frontal duplo | 180° | O | 14 |
| B | Traseira horário | 90° | P | 15 |
| B' | Traseira anti-horário | −90° | Q | 16 |
| B2 | Traseira duplo | 180° | R | 17 |

`Índice LUT = char − 'A'`. "Horário" é visto de fora da face.

## Faces opostas

O firmware aciona dois motores ao mesmo tempo quando dois movimentos
consecutivos são de faces opostas: (U, D), (R, L), (F, B), ou seja, letras
`A–C` com `D–F`, `G–I` com `J–L`, `M–O` com `P–R`.
