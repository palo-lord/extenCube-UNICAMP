"""Orquestra a GUI: monta a janela e liga os controles ao sistema.

A GUI é só uma cliente da classe Raiden (app/main_raiden.py), sem alterá-la:
as mesmas etapas que o menu do terminal usa, agora disparadas por botões.
Toda operação roda fora da thread da janela (TaskRunner, em outer.py), e os
fluxos são executados etapa a etapa para mostrar o andamento de cada uma.
"""

from tkinter import messagebox

import customtkinter as ctk

from app.communication import SerialConnectionError
from app.communication.embedded import ProtocolError
from app.communication.outer import TaskRunner
from app.main_raiden import Raiden, Mode
from app.ui_ux import settings as S
from app.ui_ux.controls import ControlPanel
from app.ui_ux.hud import CubeNet, LogPanel, SolutionPanel, StatusBar


class RaidenApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(S.APP_TITLE)
        self.geometry(S.WINDOW_SIZE)
        self.minsize(*S.MIN_SIZE)

        self.rd = None                 # instância de Raiden quando conectado
        self._mode_label = ""
        self._state = None             # último estado lido (6x8)
        self._solution = None          # última solução (dict do solver)
        self.runner = TaskRunner(self.after)

        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.controls = ControlPanel(self, {
            "connect": self.on_connect,
            "prepare": self.on_prepare,
            "solve_and_execute": self.on_solve_and_execute,
            "scan": lambda: self._single("Scan", lambda: self.rd.scan()),
            "calibrate": lambda: self._single("Calibração (c0)", lambda: self.rd.calibrate()),
            "calibrate_ro": lambda: self._single("Calibração R/O (c1)", lambda: self.rd.calibrate_ro()),
            "sense": self.on_sense,
            "solve": self.on_solve,
            "execute": self.on_execute,
            "send_sequence": self.on_send_sequence,
            "method": self.on_method,
            "speed_gap": self.on_speed_gap,
        })
        self.controls.grid(row=0, column=0, sticky="nsw", padx=(10, 5), pady=10)

        # Centro: cubo + solução.  Direita: registro, com a altura inteira.
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        center.grid_columnconfigure(0, weight=1)
        self.cube = CubeNet(center)
        self.cube.grid(row=0, column=0, sticky="ew")
        self.solution = SolutionPanel(center)
        self.solution.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        self.log = LogPanel(self)
        self.log.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)
        self.grid_columnconfigure(2, weight=1, minsize=340)

        self.status = StatusBar(self)
        self.status.grid(row=1, column=0, columnspan=3, sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.log.write("Escolha o modo e clique em Conectar.")
        self._refresh()

    # ------------------------------------------------------------------
    # Infraestrutura
    # ------------------------------------------------------------------
    def _refresh(self):
        self.controls.set_state(connected=self.rd is not None, busy=self.runner.busy)
        self.status.connection(self.rd is not None, self._mode_label)
        self.status.method(self.rd.solver.method if self.rd else "")

    def _start(self, label, fn, on_done=None, on_progress=None):
        """Dispara uma tarefa em segundo plano, com indicador e botões travados."""
        if not self.runner.run(fn, on_done=self._finish(on_done),
                               on_progress=on_progress, on_error=self._on_error):
            self.log.write("Aguarde a operação em andamento terminar.", "warn")
            return
        self.status.busy(label + "…")
        self._refresh()

    def _finish(self, on_done):
        def wrapper(result):
            self.status.busy(None)
            if on_done:
                on_done(result)
            self._refresh()
        return wrapper

    def _on_error(self, exc, tb):
        self.status.busy(None)
        if isinstance(exc, ProtocolError):
            self.log.write(f"Serial/conexão: {exc}. Confira o cabo e reconecte.", "err")
        elif isinstance(exc, SerialConnectionError):
            self.log.write(f"Conexão: {exc}", "err")
            self.log.write("Informe a porta no campo Porta (ex.: COM5) e tente de novo.", "warn")
        else:
            self.log.write(f"Erro inesperado: {exc}", "err")
            print(tb)
        self._refresh()

    def _single(self, label, call, after=None):
        """Etapa isolada: roda ``call()`` e registra o StepResult."""
        def done(res):
            self.log.result(res)
            if after:
                after(res)
        self._start(label, lambda report: call(), on_done=done)

    def _chain(self, label, stages, on_done=None):
        """Roda etapas em sequência e para na primeira falha.

        stages: lista de (rótulo, função, após_sucesso) — a função recebe o
        resultado da etapa anterior. Cada resultado aparece no log ao vivo.
        """
        def work(report):
            prev = None
            for stage_label, fn, _ in stages:
                report(("stage", stage_label))
                res = fn(prev)
                report(("result", stage_label, res))
                if not res.ok:
                    return res
                prev = res
            return prev

        def progress(item):
            if item[0] == "stage":
                self.status.busy(item[1] + "…")
                return
            _, stage_label, res = item
            self.log.result(res)
            for s_label, _, after in stages:
                if s_label == stage_label and res.ok and after:
                    after(res)

        self.log.write(f"{label}: iniciando.")
        self._start(label, work, on_done=on_done, on_progress=progress)

    # ------------------------------------------------------------------
    # Conexão
    # ------------------------------------------------------------------
    def on_connect(self):
        if self.rd is not None:
            self.rd.close()
            self.rd = None
            self._mode_label = ""
            self.log.write("Desconectado.")
            self._refresh()
            return

        label = self.controls.mode.get()
        mode = S.MODES[label]
        if mode == Mode.REAL and not messagebox.askokcancel(
                "Modo Real", "No modo Real os motores do robô vão se mover.\nContinuar?"):
            return
        port = self.controls.port.get().strip() or None
        method = self.controls.method.get()

        def done(rd):
            self.rd = rd
            self._mode_label = label
            self.log.write(f"Conectado no modo {label}.", "ok")
            if mode == Mode.REAL:
                self.log.write("Com o cubo resolvido no HOME, rode 1 · Preparar.", "warn")

        self._start("Conectando", lambda report: Raiden(mode, port=port, method=method),
                    on_done=done)

    # ------------------------------------------------------------------
    # Fluxos (espelham Raiden.prepare / Raiden.solve_and_execute, etapa a etapa)
    # ------------------------------------------------------------------
    def on_prepare(self):
        rd = self.rd
        self._chain("Preparar", [
            ("Scan", lambda _: rd.scan(), None),
            ("Calibração (c0)", lambda _: rd.calibrate(), None),
            ("Calibração R/O (c1)", lambda _: rd.calibrate_ro(), None),
        ])

    def on_solve_and_execute(self):
        rd = self.rd
        self._chain("Resolver e executar", [
            ("Lendo o cubo", lambda _: rd.sensor.read_for_solution(), self._show_state),
            ("Calculando a solução", lambda prev: rd.solve(prev.data), self._show_solution),
            ("Executando", lambda _: rd.execute(), None),
        ])

    # ------------------------------------------------------------------
    # Etapas isoladas
    # ------------------------------------------------------------------
    def on_sense(self):
        self._single("Sensoriando", lambda: self.rd.sense(),
                     after=lambda r: r.ok and self._show_state(r))

    def on_solve(self):
        if self._state is None:
            self.log.write("Nenhum estado lido. Sensorie antes.", "warn")
            return
        state = self._state
        self._single("Calculando a solução", lambda: self.rd.solve(state),
                     after=lambda r: r.ok and self._show_solution(r))

    def on_execute(self):
        if not self._solution:
            self.log.write("Nenhuma solução para executar. Resolva antes.", "warn")
            return
        seq = self._solution["robot_sequence"]
        self._single("Executando a solução", lambda: self.rd.execute(seq))

    def on_send_sequence(self):
        seq = self.controls.sequence.get().strip().upper()
        if not seq:
            self.log.write("Digite uma sequência de letras A–R.", "warn")
            return
        self._single(f"Executando {seq}", lambda: self.rd.execute(seq))

    # ------------------------------------------------------------------
    # Configuração
    # ------------------------------------------------------------------
    def on_method(self, name):
        if self.rd is None:
            return
        self.log.result(self.rd.set_method(name))     # local, não usa a serial
        self._refresh()

    def on_speed_gap(self):
        speed = self.controls.speed.get().strip()
        gap = self.controls.gap.get().strip()
        if not speed and not gap:
            self.log.write("Preencha passo (µs) e/ou pausa (ms).", "warn")
            return
        if not (speed.isdigit() or not speed) or not (gap.isdigit() or not gap):
            self.log.write("Passo e pausa devem ser números inteiros.", "warn")
            return
        rd = self.rd
        stages = []
        if speed:
            stages.append(("Ajustando velocidade", lambda _: rd.set_speed(int(speed)), None))
        if gap:
            stages.append(("Ajustando pausa", lambda _: rd.set_gap(int(gap)), None))
        self._chain("Configuração de movimento", stages)

    # ------------------------------------------------------------------
    # Atualização da visualização
    # ------------------------------------------------------------------
    def _show_state(self, res):
        self._state = res.data
        self.cube.show(res.data, caption="Última leitura do robô.")

    def _show_solution(self, res):
        self._solution = res.data
        self.solution.show(res.data, self.rd.solver.method)

    # ------------------------------------------------------------------
    def on_close(self):
        if self.runner.busy and not messagebox.askokcancel(
                "Operação em andamento",
                "O robô ainda está executando uma operação.\nFechar mesmo assim?"):
            return
        if self.rd is not None:
            self.rd.close()
        self.destroy()


def main():
    ctk.set_appearance_mode(S.APPEARANCE)
    ctk.set_default_color_theme(S.COLOR_THEME)
    RaidenApp().mainloop()
