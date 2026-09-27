#include "sensing.h"
#include "../motion/motion.h"

// N' (anti-horário) de cada face — ordem canônica U,R,F,D,L,B.
const char FACE_TURN[6] = {'B','K','N','E','H','Q'};

// POS[face][papel][passo] -> índice canônico 0..7 onde gravar.
const uint8_t POS[6][2][4] = {
    /* U */ { {0,2,4,6}, {1,3,5,7} },
    /* R */ { {0,2,4,6}, {1,3,5,7} },
    /* F */ { {0,2,4,6}, {1,3,5,7} },
    /* D */ { {6,0,2,4}, {7,1,3,5} },
    /* L */ { {0,2,4,6}, {1,3,5,7} },
    /* B */ { {0,2,4,6}, {1,3,5,7} },
};

// Razão R/O de cada adesivo lido (mesma indexação do scramble).
static float roRatio[6][8];

// ---------------------------------------------------------------------------
// Peças do cubo na indexação {face, pos horária} (geradas do Kociemba).
// ---------------------------------------------------------------------------
static const uint8_t CORNER_FP[8][3][2] = {
    { {0,4}, {1,0}, {2,2} }, { {0,6}, {2,0}, {4,2} }, { {0,0}, {4,0}, {5,2} },
    { {0,2}, {5,0}, {1,2} }, { {3,2}, {2,4}, {1,6} }, { {3,0}, {4,4}, {2,6} },
    { {3,6}, {5,4}, {4,6} }, { {3,4}, {1,4}, {5,6} },
};
static const char CORNER_COL[8][3] = {
    {'W','R','G'}, {'W','G','O'}, {'W','O','B'}, {'W','B','R'},
    {'Y','G','R'}, {'Y','O','G'}, {'Y','B','O'}, {'Y','R','B'},
};
static const uint8_t EDGE_FP[12][2][2] = {
    { {0,3}, {1,1} }, { {0,5}, {2,1} }, { {0,7}, {4,1} }, { {0,1}, {5,1} },
    { {3,3}, {1,5} }, { {3,1}, {2,5} }, { {3,7}, {4,5} }, { {3,5}, {5,5} },
    { {2,3}, {1,7} }, { {2,7}, {4,3} }, { {5,3}, {4,7} }, { {5,7}, {1,3} },
};
static const char EDGE_COL[12][2] = {
    {'W','R'}, {'W','G'}, {'W','O'}, {'W','B'}, {'Y','R'}, {'Y','G'},
    {'Y','O'}, {'Y','B'}, {'G','R'}, {'G','O'}, {'B','O'}, {'B','R'},
};

static inline bool isRO(char c) { return c == 'R' || c == 'O'; }

// ---------------------------------------------------------------------------
// Calibração R/O por sensor (c1*). Arestas são sempre lidas pelo sensor de
// CENTRO da face (ns = 2f+1), então a referência é indexada por face.
// ---------------------------------------------------------------------------
static float roMid[6], roHalf[6];
static bool  roCal = false;

// Scrambles conhecidos: juntos, põem R e O nas arestas de todas as faces.
static const char CAL_SEQ[2][4]  = { "NRK", "BQE" };   // F' B2 R'  |  U' B' D'
static const char CAL_UNDO[2][4] = { "JRM", "DPA" };   // R B2 F    |  D B U
static const char CAL_STATE[2][49] = {
    "YYBBBRRWOOORYYYRGGYWRGGGOOGGGWWYROWWWORRWBBBBBOY",
    "OOBWWWWWGGWWBBRROOOGWRRGYYGRRYYYYBBOGGGYRBBBOOYR",
};

static inline float logR(float r) { return log(r < 0.5f ? 0.5f : r); }

// Pontuação R/O de um adesivo de aresta: >0 tende a laranja, <0 a vermelho.
static float roScore(uint8_t f, uint8_t p) {
    float lr = logR(roRatio[f][p]);
    if (!roCal) return lr;
    return (lr - roMid[f]) / roHalf[f];
}

// ---------------------------------------------------------------------------
// Leitura crua das 48 casas (sem resolução por peça).
// ---------------------------------------------------------------------------
static int senseScan() {
    int invalid = 0;
    for (uint8_t f = 0; f < 6; f++) {
        uint8_t nsQ = 2 * f;
        uint8_t nsC = 2 * f + 1;
        for (uint8_t k = 0; k < 4; k++) {
            float rq, rcen;
            char cq = detectColorLogicalRO(nsQ, rq);
            char cc = detectColorLogicalRO(nsC, rcen);
            if (cq == 'X') invalid++;
            if (cc == 'X') invalid++;
            scramble[f][ POS[f][0][k] ] = cq;
            scramble[f][ POS[f][1][k] ] = cc;
            roRatio[f][ POS[f][0][k] ] = rq;
            roRatio[f][ POS[f][1][k] ] = rcen;
            motionExecute(FACE_TURN[f]);
            _delay_ms(100);
        }
    }
    return invalid;
}

// ---------------------------------------------------------------------------
// 1) Quinas: a quiralidade determina R/O (não usa medida).
// ---------------------------------------------------------------------------
static void resolveCorners() {
    for (uint8_t i = 0; i < 8; i++) {
        char col[3]; int8_t amb = -1; uint8_t nAmb = 0;
        for (uint8_t k = 0; k < 3; k++) {
            col[k] = scramble[CORNER_FP[i][k][0]][CORNER_FP[i][k][1]];
            if (isRO(col[k])) { amb = k; nAmb++; }
        }
        if (nAmb != 1) continue;
        bool done = false;
        for (uint8_t t = 0; t < 8 && !done; t++) {
            for (uint8_t rot = 0; rot < 3 && !done; rot++) {
                bool ok = true;
                for (uint8_t k = 0; k < 3; k++) {
                    if ((int8_t)k == amb) continue;
                    if (CORNER_COL[t][(k + rot) % 3] != col[k]) { ok = false; break; }
                }
                char cand = CORNER_COL[t][(amb + rot) % 3];
                if (ok && isRO(cand)) {
                    scramble[CORNER_FP[i][amb][0]][CORNER_FP[i][amb][1]] = cand;
                    done = true;
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// 2) Arestas: por cor parceira, a de maior pontuação (normalizada) é laranja.
//    Guarda os grupos e margens para a checagem de paridade.
// ---------------------------------------------------------------------------
static uint8_t grpF[4][2], grpP[4][2];
static float   grpMargin[4];
static bool    grpValid[4];

static void resolveEdges() {
    const char PARTNER[4] = {'W','Y','G','B'};
    for (uint8_t p = 0; p < 4; p++) {
        uint8_t n = 0;
        grpValid[p] = false;
        for (uint8_t e = 0; e < 12; e++) {
            uint8_t f0 = EDGE_FP[e][0][0], q0 = EDGE_FP[e][0][1];
            uint8_t f1 = EDGE_FP[e][1][0], q1 = EDGE_FP[e][1][1];
            char a = scramble[f0][q0], b = scramble[f1][q1];
            if (isRO(a) && b == PARTNER[p]) { if (n < 2) { grpF[p][n] = f0; grpP[p][n] = q0; } n++; }
            else if (isRO(b) && a == PARTNER[p]) { if (n < 2) { grpF[p][n] = f1; grpP[p][n] = q1; } n++; }
        }
        if (n != 2) continue;
        float s0 = roScore(grpF[p][0], grpP[p][0]);
        float s1 = roScore(grpF[p][1], grpP[p][1]);
        bool firstIsO = s0 > s1;
        scramble[grpF[p][0]][grpP[p][0]] = firstIsO ? 'O' : 'R';
        scramble[grpF[p][1]][grpP[p][1]] = firstIsO ? 'R' : 'O';
        grpMargin[p] = fabs(s0 - s1);
        grpValid[p]  = true;
    }
}

// ---------------------------------------------------------------------------
// 3) Paridade: num cubo real, paridade(perm. quinas) == paridade(perm. arestas).
//    Um grupo de arestas R/O trocado quebra isso; inverte o de menor margem.
// ---------------------------------------------------------------------------
static int8_t cornerPiece(uint8_t i) {
    char col[3];
    for (uint8_t k = 0; k < 3; k++) col[k] = scramble[CORNER_FP[i][k][0]][CORNER_FP[i][k][1]];
    for (uint8_t t = 0; t < 8; t++)
        for (uint8_t rot = 0; rot < 3; rot++)
            if (CORNER_COL[t][rot] == col[0] &&
                CORNER_COL[t][(rot + 1) % 3] == col[1] &&
                CORNER_COL[t][(rot + 2) % 3] == col[2]) return t;
    return -1;
}

static int8_t edgePiece(uint8_t j) {
    char a = scramble[EDGE_FP[j][0][0]][EDGE_FP[j][0][1]];
    char b = scramble[EDGE_FP[j][1][0]][EDGE_FP[j][1][1]];
    for (uint8_t t = 0; t < 12; t++)
        if ((EDGE_COL[t][0] == a && EDGE_COL[t][1] == b) ||
            (EDGE_COL[t][0] == b && EDGE_COL[t][1] == a)) return t;
    return -1;
}

// Retorna 0/1 (paridade) ou -1 se a permutação não for válida.
static int8_t permParity(const int8_t *perm, uint8_t n) {
    uint16_t seen = 0; uint8_t inv = 0;
    for (uint8_t i = 0; i < n; i++) {
        if (perm[i] < 0 || (seen & (1u << perm[i]))) return -1;
        seen |= (1u << perm[i]);
        for (uint8_t j = i + 1; j < n; j++) if (perm[j] >= 0 && perm[j] < perm[i]) inv++;
    }
    return inv & 1;
}

static void fixParity() {
    int8_t cp[8], ep[12];
    for (uint8_t i = 0; i < 8; i++)  cp[i] = cornerPiece(i);
    for (uint8_t j = 0; j < 12; j++) ep[j] = edgePiece(j);
    int8_t pc = permParity(cp, 8);
    int8_t pe = permParity(ep, 12);
    if (pc < 0 || pe < 0 || pc == pe) return;          // inválido de outra forma, ou já ok
    int8_t best = -1;
    for (uint8_t g = 0; g < 4; g++)
        if (grpValid[g] && (best < 0 || grpMargin[g] < grpMargin[best])) best = g;
    if (best < 0) return;
    for (uint8_t n = 0; n < 2; n++) {
        char &c = scramble[grpF[best][n]][grpP[best][n]];
        c = (c == 'R') ? 'O' : 'R';
    }
}

int senseComplete() {
    int invalid = senseScan();
    if (invalid == 0) {
        resolveCorners();
        resolveEdges();
        fixParity();
    }
    return invalid;
}

// c1*: cubo RESOLVIDO no HOME. Aplica C1 e C2, lê, desfaz e aprende o viés R/O
// do sensor de centro de cada face. Retorno: 0 ok | 4 leitura inválida | 5 faltou R ou O.
int calibrateRO() {
    float sR[6] = {0}, sO[6] = {0};
    uint8_t nR[6] = {0}, nO[6] = {0};
    for (uint8_t c = 0; c < 2; c++) {
        motionExecuteSequence(CAL_SEQ[c], 3);
        int bad = senseScan();
        motionExecuteSequence(CAL_UNDO[c], 3);
        if (bad) return 4;
        for (uint8_t f = 0; f < 6; f++)
            for (uint8_t p = 1; p < 8; p += 2) {          // só arestas
                char truth = CAL_STATE[c][f * 8 + p];
                if (truth == 'R') { sR[f] += logR(roRatio[f][p]); nR[f]++; }
                else if (truth == 'O') { sO[f] += logR(roRatio[f][p]); nO[f]++; }
            }
    }
    for (uint8_t f = 0; f < 6; f++) {
        if (nR[f] == 0 || nO[f] == 0) return 5;
        float mR = sR[f] / nR[f], mO = sO[f] / nO[f];
        if (mO <= mR) return 5;                          // sensor não separa R de O
        roMid[f]  = 0.5f * (mR + mO);
        roHalf[f] = 0.5f * (mO - mR);
    }
    roCal = true;
    return 0;
}

// Referência aprendida (em razão, não log) para o relatório do c1*.
bool roGetRef(uint8_t f, float &refR, float &refO) {
    if (!roCal || f >= 6) return false;
    refR = exp(roMid[f] - roHalf[f]);
    refO = exp(roMid[f] + roHalf[f]);
    return true;
}