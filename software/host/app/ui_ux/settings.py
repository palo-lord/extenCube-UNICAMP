"""Configurações e parâmetros da GUI (cores, medidas, textos fixos)."""

APP_TITLE = "Raiden · Solucionador de Cubo Mágico"
WINDOW_SIZE = "1320x700"
MIN_SIZE = (1180, 620)

APPEARANCE = "dark"          # "dark" | "light" | "system"
COLOR_THEME = "blue"

# Cor de exibição de cada adesivo (chars do contrato cube_state.md).
STICKER_COLORS = {
    "W": "#F2F2F2",
    "R": "#C62828",
    "G": "#2E7D32",
    "Y": "#FBC02D",
    "O": "#EF6C00",
    "B": "#1565C0",
    None: "#3A3A3A",          # casa ainda não lida
}

# Faces na ordem do contrato (URFDLB) e cor do centro de cada uma (HOME).
FACES = "URFDLB"
FACE_CENTER = {"U": "W", "R": "R", "F": "G", "D": "Y", "L": "O", "B": "B"}
FACE_NAMES = {"U": "Cima", "R": "Direita", "F": "Frente",
              "D": "Baixo", "L": "Esquerda", "B": "Trás"}

# Posição de cada face na planificação em cruz (coluna, linha), em blocos 3x3:
#            U
#        L   F   R   B
#            D
NET_LAYOUT = {"U": (1, 0), "L": (0, 1), "F": (1, 1),
              "R": (2, 1), "B": (3, 1), "D": (1, 2)}

# Posição horária (0..7, contrato) -> índice na grade 3x3 linha a linha.
CW_TO_GRID = [0, 1, 2, 5, 8, 7, 6, 3]

STICKER_PX = 30              # lado de cada adesivo no desenho
STICKER_GAP = 3
FACE_GAP = 8

# Cores de estado usadas no log e na barra de status.
OK_COLOR = "#43A047"
ERR_COLOR = "#E53935"
INFO_COLOR = "#9E9E9E"
WARN_COLOR = "#FB8C00"

# Modos de operação (valores iguais a app.main_raiden.Mode).
MODES = {"Demo": "demo", "Uno dummy": "uno_dummy", "Real": "real"}
METHODS = ["kociemba", "m2op"]
