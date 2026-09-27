"""Validação de ponta a ponta da comunicação host<->firmware (contra o Uno dummy).
Rode com software/tools/firmware_dummy/firmware_dummy.ino gravado no Uno. Uso (de dentro de host/):  python -m tests.test_comm [COM5]
"""
import sys
from app.communication import open_link, close_link
from app.communication.embedded import FirmwareError, InvalidSensorError

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else None   # None = autodetecta
    link = open_link(port=port)                          # abre + consome READY*
    print(f"[ok] link aberto, READY recebido")

    # SCAN -> 12 bools
    scan = link.scan()
    assert scan == [True]*12, scan
    print(f"[ok] scan  -> {scan}")

    # CALIBRATE -> dict estruturado
    cal = link.calibrate()
    assert cal['hue']['R'] == 346.4 and cal['white_sat_thresh'] == 0.459, cal
    assert cal['white_balance'] == {'r':19.0,'g':17.0,'b':9.0}, cal
    print(f"[ok] calib -> R_hue={cal['hue']['R']}  thresh={cal['white_sat_thresh']}  wb={cal['white_balance']}")

    # CALIBRATE_RO -> referência R/O por face
    ro = link.calibrate_ro()
    assert list(ro) == list("URFDLB") and ro['L'] == {'R': 11.95, 'O': 19.37}, ro
    print(f"[ok] calib R/O -> L={ro['L']}")

    # SENSE -> matriz 6x8 (estado do T0 no dummy)
    state = link.sense()
    assert len(state) == 6 and all(len(f)==8 for f in state), state
    assert state[0] == list("OBBWRYYG") and state[5] == list("WOGYYRRW"), state
    print(f"[ok] sense -> face U={''.join(state[0])}  face B={''.join(state[5])}")

    # MOVE -> tempo (float)
    t = link.move("ADJ")            # 3 chars -> dummy responde d_0.150*
    assert abs(t - 0.15) < 1e-6, t
    print(f"[ok] move 'ADJ' -> {t}s")

    # KOLOR -> char
    c = link.read_color(4)         # ns 4 -> 'G' no dummy
    assert c == 'G', c
    print(f"[ok] read_color(4) -> {c}")

    # Erro nomeado: ns inválido -> InvalidSensorError (e3)
    try:
        link.read_color(99)        # o Tx já barra <0..11> no host (ValueError)
    except ValueError as e:
        print(f"[ok] read_color(99) barrado no host -> {e}")

    # Erro do firmware: move inválido é barrado no host antes de ir à serial
    try:
        link.move("AZ")            # 'Z' fora de A-R
    except ValueError as e:
        print(f"[ok] move 'AZ' barrado no host -> {e}")

    close_link()
    print("\n[SUCESSO] comunicação host<->firmware validada.")

if __name__ == "__main__":
    main()