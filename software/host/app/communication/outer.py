"""Comunicação externa com a UI (ponte UI <-> sistema).

A UI nunca chama o sistema direto na thread da janela: operações como o
sensoriamento (r0*) levam dezenas de segundos e congelariam a interface.
O TaskRunner executa cada operação numa thread de trabalho e devolve os
resultados à thread da UI por uma fila, consumida periodicamente pelo
agendador da própria UI (ex.: root.after do Tk).

Uma operação por vez: o protocolo é mestre/escravo (um comando e espera a
resposta), então o runner recusa uma nova tarefa enquanto outra roda.
"""

import queue
import threading
import traceback


class TaskRunner:
    """Executa funções bloqueantes fora da thread da UI.

    schedule(ms, callback): agendador da UI (no Tk, ``root.after``).
    """

    POLL_MS = 60

    def __init__(self, schedule):
        self._schedule = schedule
        self._queue = queue.Queue()
        self._busy = False
        self._schedule(self.POLL_MS, self._poll)

    @property
    def busy(self) -> bool:
        return self._busy

    def run(self, fn, on_done=None, on_progress=None, on_error=None) -> bool:
        """Roda ``fn(report)`` numa thread. Retorna False se já houver tarefa.

        report(x): chamada pela tarefa para publicar um resultado parcial;
                   chega na UI via ``on_progress(x)``.
        on_done(r): recebe o retorno de ``fn``.
        on_error(exc, tb): recebe exceções não tratadas pela tarefa.
        """
        if self._busy:
            return False
        self._busy = True

        def report(item):
            self._queue.put(("progress", on_progress, item))

        def worker():
            try:
                result = fn(report)
                self._queue.put(("done", on_done, result))
            except Exception as exc:                      # noqa: BLE001
                self._queue.put(("error", on_error, (exc, traceback.format_exc())))

        threading.Thread(target=worker, daemon=True).start()
        return True

    def _poll(self):
        try:
            while True:
                kind, callback, payload = self._queue.get_nowait()
                if kind in ("done", "error"):
                    self._busy = False
                if callback is None:
                    continue
                if kind == "error":
                    callback(*payload)
                else:
                    callback(payload)
        except queue.Empty:
            pass
        self._schedule(self.POLL_MS, self._poll)
