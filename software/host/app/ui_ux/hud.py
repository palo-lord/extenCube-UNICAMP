"""Esqueleto visual da GUI: cubo planificado, painel de solução, log e status."""

import time
import tkinter as tk

import customtkinter as ctk

from app.ui_ux import settings as S


class CubeNet(ctk.CTkFrame):
    """Planificação do cubo em cruz, desenhada a partir de state[face][pos]."""

    def __init__(self, master):
        super().__init__(master)
        cell = S.STICKER_PX + S.STICKER_GAP
        self._face_px = 3 * cell
        width = 4 * self._face_px + 3 * S.FACE_GAP
        height = 3 * self._face_px + 2 * S.FACE_GAP

        ctk.CTkLabel(self, text="Estado do cubo",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=12, pady=(10, 0))
        self._caption = ctk.CTkLabel(self, text="Nenhuma leitura ainda.",
                                     text_color=S.INFO_COLOR)
        self._caption.pack(anchor="w", padx=12)
        self._canvas = tk.Canvas(self, width=width, height=height,
                                 highlightthickness=0, bg=self._bg())
        self._canvas.pack(padx=12, pady=10)
        self.show(None)

    def _bg(self):
        color = self.cget("fg_color")
        if isinstance(color, (list, tuple)):
            color = color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
        return color

    def show(self, state, caption=None):
        """Desenha o estado (6x8, ordem URFDLB) ou só os centros se None."""
        c = self._canvas
        c.delete("all")
        cell = S.STICKER_PX + S.STICKER_GAP
        for f, face in enumerate(S.FACES):
            col, row = S.NET_LAYOUT[face]
            x0 = col * (self._face_px + S.FACE_GAP)
            y0 = row * (self._face_px + S.FACE_GAP)
            grid = [None] * 9
            grid[4] = S.FACE_CENTER[face]
            if state is not None:
                for pos in range(8):
                    grid[S.CW_TO_GRID[pos]] = state[f][pos]
            for i, ch in enumerate(grid):
                x = x0 + (i % 3) * cell
                y = y0 + (i // 3) * cell
                c.create_rectangle(x, y, x + S.STICKER_PX, y + S.STICKER_PX,
                                   fill=S.STICKER_COLORS.get(ch, S.STICKER_COLORS[None]),
                                   outline="#111111", width=1)
            c.create_text(x0 + self._face_px / 2 - S.STICKER_GAP / 2,
                          y0 + self._face_px / 2 - S.STICKER_GAP / 2,
                          text=face, fill="#111111", font=("Segoe UI", 11, "bold"))
        if caption is not None:
            self._caption.configure(text=caption)


class SolutionPanel(ctk.CTkFrame):
    """Mostra a última solução calculada (notação de cubo e sequência do robô)."""

    def __init__(self, master):
        super().__init__(master)
        ctk.CTkLabel(self, text="Solução",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=12, pady=(10, 0))
        self._summary = ctk.CTkLabel(self, text="Nenhuma solução calculada.",
                                     text_color=S.INFO_COLOR)
        self._summary.pack(anchor="w", padx=12)
        self._text = ctk.CTkTextbox(self, height=110, wrap="word",
                                    font=ctk.CTkFont(family="Consolas", size=12))
        self._text.pack(fill="x", padx=12, pady=(4, 10))
        self._text.configure(state="disabled")

    def show(self, data, method):
        self._summary.configure(
            text=f"{method} · {data['move_count']} movimentos", text_color=S.OK_COLOR)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("end", f"Notação: {data['solution'] or '(já resolvido)'}\n")
        self._text.insert("end", f"Robô:    {data['robot_sequence'] or '-'}")
        self._text.configure(state="disabled")

    def clear(self):
        self._summary.configure(text="Nenhuma solução calculada.", text_color=S.INFO_COLOR)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


class LogPanel(ctk.CTkFrame):
    """Registro cronológico de cada etapa (✓ sucesso, ✗ falha, · informação)."""

    def __init__(self, master):
        super().__init__(master)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(head, text="Registro",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(head, text="Limpar", width=70, height=24,
                      fg_color="transparent", border_width=1,
                      command=self.clear).pack(side="right")
        self._text = ctk.CTkTextbox(self, wrap="word",
                                    font=ctk.CTkFont(family="Consolas", size=12))
        self._text.pack(fill="both", expand=True, padx=12, pady=10)
        self._text.tag_config("ok", foreground=S.OK_COLOR)
        self._text.tag_config("err", foreground=S.ERR_COLOR)
        self._text.tag_config("warn", foreground=S.WARN_COLOR)
        self._text.tag_config("info", foreground=S.INFO_COLOR)
        self._text.configure(state="disabled")

    def write(self, message, kind="info"):
        mark = {"ok": "✓", "err": "✗", "warn": "!", "info": "·"}[kind]
        self._text.configure(state="normal")
        self._text.insert("end", time.strftime("%H:%M:%S "), "info")
        self._text.insert("end", f"{mark} {message}\n", kind)
        self._text.see("end")
        self._text.configure(state="disabled")

    def result(self, res):
        """Registra um StepResult."""
        self.write(res.message or res.step, "ok" if res.ok else "err")

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


class StatusBar(ctk.CTkFrame):
    """Linha inferior: conexão, modo, método e indicador de operação em curso."""

    def __init__(self, master):
        super().__init__(master, height=34, corner_radius=0)
        self._dot = ctk.CTkLabel(self, text="●", text_color=S.ERR_COLOR, width=18)
        self._dot.pack(side="left", padx=(12, 4))
        self._conn = ctk.CTkLabel(self, text="Desconectado")
        self._conn.pack(side="left")
        self._method = ctk.CTkLabel(self, text="", text_color=S.INFO_COLOR)
        self._method.pack(side="left", padx=20)
        self._busy_label = ctk.CTkLabel(self, text="", text_color=S.WARN_COLOR)
        self._busy_label.pack(side="right", padx=12)
        self._bar = ctk.CTkProgressBar(self, width=140, mode="indeterminate")

    def connection(self, connected, mode_label=""):
        self._dot.configure(text_color=S.OK_COLOR if connected else S.ERR_COLOR)
        self._conn.configure(text=f"Conectado · {mode_label}" if connected else "Desconectado")

    def method(self, name):
        self._method.configure(text=f"Solver: {name}" if name else "")

    def busy(self, label):
        """label=None encerra o indicador."""
        if label:
            self._busy_label.configure(text=label)
            self._bar.pack(side="right", padx=4)
            self._bar.start()
        else:
            self._bar.stop()
            self._bar.pack_forget()
            self._busy_label.configure(text="")
