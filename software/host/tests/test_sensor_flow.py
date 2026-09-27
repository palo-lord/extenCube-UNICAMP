"""Testa o SensorFlow com um link falso — sem serial, sem hardware.
Roda de dentro de host/:  python -m tests.test_sensor_flow
"""
from sensor.main_sensor import SensorFlow
from app.communication.embedded import (
    CalibrationPremiseError, SenseIncompleteError,
)

class FakeLink:
    """Link dublê: você programa o que cada método devolve ou levanta."""
    def __init__(self, scan=None, calibrate=None, sense=None, calibrate_ro=None):
        self._scan, self._calibrate, self._sense = scan, calibrate, sense
        self._calibrate_ro = calibrate_ro
    def _resolve(self, v):
        if isinstance(v, Exception):      # programado pra falhar
            raise v
        return v
    def scan(self):      return self._resolve(self._scan)
    def calibrate(self): return self._resolve(self._calibrate)
    def sense(self):     return self._resolve(self._sense)
    def calibrate_ro(self): return self._resolve(self._calibrate_ro)


CAL_OK = {'hue':{}, 'sat':{}, 'white_sat_thresh':0.355,
          'white_balance':{'r':18.0,'g':18.0,'b':7.0}}
# Resposta do c1* (R/O por face), igual à calibração real da bancada.
CAL_RO_OK = {f: {'R': r, 'O': o} for f, (r, o) in zip("URFDLB",
             [(9.02, 19.82), (5.80, 17.23), (16.17, 50.04),
              (12.14, 31.26), (11.95, 19.37), (7.06, 19.58)])}
STATE_OK = [list("WWWWWWWW"),list("RRRRRRRR"),list("GGGGGGGG"),
            list("YYYYYYYY"),list("OOOOOOOO"),list("BBBBBBBB")]

# 1) Caminho feliz: prepare() encadeia scan->calibrate->calibrate_ro
f = SensorFlow(FakeLink(scan=[True]*12, calibrate=CAL_OK, calibrate_ro=CAL_RO_OK))
r = f.prepare()
assert r.ok and r.step == "calibrate_ro", r
assert "L" in r.message                      # face mais apertada da bancada
assert f.calibrated is True
print(f"[ok] prepare feliz -> parou em '{r.step}', ok={r.ok}")

# 2) Scan falho: prepare() PARA no scan, NÃO chama calibrate
f = SensorFlow(FakeLink(scan=[True]*5 + [False] + [True]*6))
r = f.prepare()
assert not r.ok and r.step == "scan", r
assert f.calibrated is False                 # nunca calibrou
print(f"[ok] prepare com sensor mudo -> parou em '{r.step}': {r.message}")

# 3) Calibração viola premissa (e5): etapa isolada mapeia p/ StepResult
f = SensorFlow(FakeLink(scan=[True]*12,
                        calibrate=CalibrationPremiseError("e5")))
r = f.calibrate()
assert not r.ok and r.error == 5, r
print(f"[ok] calibrate e5 -> error={r.error}: {r.message}")

# 4) Momento 2 feliz: read_for_solution -> scan->sense, entrega matriz
f = SensorFlow(FakeLink(scan=[True]*12, sense=STATE_OK))
r = f.read_for_solution()
assert r.ok and r.step == "sense" and r.data[0] == list("WWWWWWWW"), r
print(f"[ok] read_for_solution feliz -> estado {len(r.data)}x{len(r.data[0])}")

# 5) Sense incompleto (e6): read_for_solution para no sense
f = SensorFlow(FakeLink(scan=[True]*12, sense=SenseIncompleteError("e6")))
r = f.read_for_solution()
assert not r.ok and r.error == 6, r
print(f"[ok] read_for_solution e6 -> error={r.error}")

# 6) Calibração R/O falha (e5): prepare() para no calibrate_ro
f = SensorFlow(FakeLink(scan=[True]*12, calibrate=CAL_OK,
                        calibrate_ro=CalibrationPremiseError("e5")))
r = f.prepare()
assert not r.ok and r.step == "calibrate_ro" and r.error == 5, r
print(f"[ok] prepare com c1* e5 -> parou em '{r.step}': {r.message}")

print("\n[SUCESSO] lógica do SensorFlow validada sem hardware.")