"""Controles do usuário: conexão, fluxos, etapas isoladas e configuração.

O painel não conhece o sistema: cada botão chama um callback recebido de
fora (main_ui). Assim a lógica fica toda num lugar e o painel só desenha.
"""

import customtkinter as ctk

from app.ui_ux import settings as S


def _section(master, title):
    ctk.CTkLabel(master, text=title, text_color=S.INFO_COLOR,
                 font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=14, pady=(14, 4))


class ControlPanel(ctk.CTkScrollableFrame):
    """Coluna de controles. ``actions`` mapeia nome -> callable."""

    def __init__(self, master, actions):
        super().__init__(master, width=290)
        self._a = actions
        self._op_buttons = []       # desabilitados sem conexão ou durante tarefas

        # --- Conexão ---------------------------------------------------
        _section(self, "CONEXÃO")
        self.mode = ctk.CTkSegmentedButton(self, values=list(S.MODES))
        self.mode.set("Demo")
        self.mode.pack(fill="x", padx=14)
        self.port = ctk.CTkEntry(self, placeholder_text="Porta (vazio = automática)")
        self.port.pack(fill="x", padx=14, pady=(6, 0))
        self.connect_btn = ctk.CTkButton(self, text="Conectar", command=actions["connect"])
        self.connect_btn.pack(fill="x", padx=14, pady=6)

        # --- Fluxos ----------------------------------------------------
        _section(self, "FLUXOS")
        self._op(ctk.CTkButton(self, text="1 · Preparar", height=40,
                               font=ctk.CTkFont(size=14, weight="bold"),
                               command=actions["prepare"]))
        ctk.CTkLabel(self, text="cubo resolvido · scan + calibrações",
                     text_color=S.INFO_COLOR, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)
        self._op(ctk.CTkButton(self, text="2 · Resolver e executar", height=40,
                               font=ctk.CTkFont(size=14, weight="bold"),
                               fg_color="#2E7D32", hover_color="#1B5E20",
                               command=actions["solve_and_execute"]))
        ctk.CTkLabel(self, text="lê → calcula → executa",
                     text_color=S.INFO_COLOR, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)

        # --- Etapas isoladas ------------------------------------------
        _section(self, "ETAPAS ISOLADAS")
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=14)
        steps = [("Scan", "scan"), ("Calibrar", "calibrate"),
                 ("Calibrar R/O", "calibrate_ro"), ("Sensoriar", "sense"),
                 ("Resolver", "solve"), ("Executar solução", "execute")]
        for i, (label, key) in enumerate(steps):
            b = ctk.CTkButton(grid, text=label, height=30, command=actions[key])
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
            self._op_buttons.append(b)
        grid.grid_columnconfigure((0, 1), weight=1)

        seq = ctk.CTkFrame(self, fg_color="transparent")
        seq.pack(fill="x", padx=14, pady=(6, 0))
        self.sequence = ctk.CTkEntry(seq, placeholder_text="Sequência A–R (ex.: JAJDGA)")
        self.sequence.pack(side="left", fill="x", expand=True)
        b = ctk.CTkButton(seq, text="Enviar", width=64, command=actions["send_sequence"])
        b.pack(side="left", padx=(4, 0))
        self._op_buttons.append(b)

        # --- Configuração ---------------------------------------------
        _section(self, "CONFIGURAÇÃO")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14)
        ctk.CTkLabel(row, text="Método").pack(side="left")
        self.method = ctk.CTkOptionMenu(row, values=S.METHODS, width=130,
                                        command=actions["method"])
        self.method.pack(side="right")
        self._op_buttons.append(self.method)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(6, 0))
        self.speed = ctk.CTkEntry(row, placeholder_text="passo µs", width=90)
        self.speed.pack(side="left")
        self.gap = ctk.CTkEntry(row, placeholder_text="pausa ms", width=90)
        self.gap.pack(side="left", padx=4)
        b = ctk.CTkButton(row, text="Aplicar", width=64, command=actions["speed_gap"])
        b.pack(side="left")
        self._op_buttons.append(b)

        self.set_state(connected=False, busy=False)

    def _op(self, button):
        button.pack(fill="x", padx=14, pady=(6, 0))
        self._op_buttons.append(button)

    def set_state(self, connected, busy):
        """Habilita operações só com conexão ativa e nenhuma tarefa em curso."""
        ops = "normal" if connected and not busy else "disabled"
        for w in self._op_buttons:
            w.configure(state=ops)
        idle = "disabled" if busy else "normal"
        self.connect_btn.configure(text="Desconectar" if connected else "Conectar", state=idle)
        self.mode.configure(state="disabled" if connected or busy else "normal")
        self.port.configure(state="disabled" if connected or busy else "normal")
