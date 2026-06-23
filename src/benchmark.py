
from __future__ import annotations
import time
from collections import deque
from typing import Deque
import pygame

from state import GameState, crear_estado_inicial


COLOR_TITULO  = (255, 220, 50)
COLOR_VALOR   = (255, 255, 255)
COLOR_SEQ     = (255, 100, 100)
COLOR_PAR     = (100, 255, 150)
COLOR_HINT    = (150, 150, 170)
COLOR_BUSCAN  = (220, 60, 60)
COLOR_REGRESAN= (255, 160, 20)

WINDOW_SIZE   = 60

class FPSCounter:

    def __init__(self, window: int = WINDOW_SIZE) -> None:
        self._tiempos: Deque[float] = deque(maxlen=window)
        self._ultimo: float = time.perf_counter()

    def tick(self) -> None:
        ahora = time.perf_counter()
        self._tiempos.append(ahora - self._ultimo)
        self._ultimo = ahora

    @property
    def fps(self) -> float:
        if len(self._tiempos) < 2:
            return 0.0
        promedio = sum(self._tiempos) / len(self._tiempos)
        return 1.0 / promedio if promedio > 0 else 0.0

    @property
    def frame_ms(self) -> float:
        if not self._tiempos:
            return 0.0
        return (sum(self._tiempos) / len(self._tiempos)) * 1000


class BenchmarkTable:

    def __init__(self) -> None:
        self._registros: dict = {}

    def registrar(self, n_hormigas: int, modo: str, fps: float) -> None:
        self._registros[(n_hormigas, modo)] = round(fps, 1)

    def obtener(self, n_hormigas: int, modo: str) -> str:
        val = self._registros.get((n_hormigas, modo))
        return f"{val}" if val is not None else "---"


def render_metrics(
    screen: pygame.Surface,
    state: GameState,
    fps_counter: FPSCounter,
    table: BenchmarkTable,
) -> None:
    font_titulo = pygame.font.SysFont("monospace", 13, bold=True)
    font_normal = pygame.font.SysFont("monospace", 12)
    font_small  = pygame.font.SysFont("monospace", 11)

    fps_actual  = fps_counter.fps
    modo_texto  = state.mode.upper()
    n_hormigas  = len(state.hormigas)
    n_buscan    = sum(1 for h in state.hormigas if h.estado == "buscando")
    n_regresan  = n_hormigas - n_buscan

    table.registrar(n_hormigas, state.mode, fps_actual)

    px, py = 10, 10
    lh = 17

    color_modo = COLOR_PAR if state.mode == "parallel" else COLOR_SEQ

    lineas = [
        (f"MODO: {modo_texto}",                   color_modo),
        (f"FPS: {fps_actual:.1f}",                COLOR_VALOR),
        (f"Tiempo/frame: {fps_counter.frame_ms:.1f}ms", COLOR_VALOR),
        (f"Hormigas: {n_hormigas:,}",             COLOR_VALOR),
        (f"  Buscando:   {n_buscan:,}",           COLOR_BUSCAN),
        (f"  Regresando: {n_regresan:,}",         COLOR_REGRESAN),
        (f"Feromonas: {len(state.feromonas):,}",  COLOR_PAR),
        (f"Comida en nido: {state.nido.comida_recolectada}", COLOR_TITULO),
        (f"Frame: {state.frame}",                 COLOR_HINT),
    ]

    for i, (texto, color) in enumerate(lineas):
        surf = font_normal.render(texto, True, color)
        screen.blit(surf, (px, py + i * lh))

    tw  = 340
    tx  = screen.get_width() - tw - 10
    ty  = 10
    col = tw // 3

    titulo = font_titulo.render("TABLA COMPARATIVA (FPS)", True, COLOR_TITULO)
    screen.blit(titulo, (tx, ty))

    headers = ["Hormigas", "Secuencial", "Paralelo"]
    for j, h in enumerate(headers):
        s = font_small.render(h, True, COLOR_TITULO)
        screen.blit(s, (tx + j * col, ty + 18))

    pygame.draw.line(screen, COLOR_HINT,
                     (tx, ty + 32), (tx + tw, ty + 32), 1)

    filas = [1000, 3000, 5000]
    for i, n in enumerate(filas):
        seq = table.obtener(n, "sequential")
        par = table.obtener(n, "parallel")
        ry  = ty + 38 + i * lh

        datos   = [f"{n:,}", seq, par]
        colores = [COLOR_VALOR, COLOR_SEQ, COLOR_PAR]
        for j, (val, col_color) in enumerate(zip(datos, colores)):
            s = font_small.render(val, True, col_color)
            screen.blit(s, (tx + j * col, ry))

    leyenda_y = screen.get_height() - 38
    items = [
        ("● Buscando", COLOR_BUSCAN),
        ("● Regresando", COLOR_REGRESAN),
        ("● Feromona", COLOR_PAR),
        ("● Comida", COLOR_TITULO),
    ]
    lx = 10
    for texto, color in items:
        s = font_small.render(texto, True, color)
        screen.blit(s, (lx, leyenda_y))
        lx += s.get_width() + 20

    hint = font_small.render(
        "[P] Cambiar modo  [1] 1000 hormigas  [3] 3000  [5] 5000  [ESC] Salir",
        True, COLOR_HINT
    )
    screen.blit(hint, (10, screen.get_height() - 20))


def handle_entity_count_key(key: int, state: GameState) -> GameState:
    key_map = {
        pygame.K_1: 1000,
        pygame.K_3: 3000,
        pygame.K_5: 5000,
    }
    n = key_map.get(key)
    if n is None:
        return state

    return crear_estado_inicial(
        n_hormigas=n,
        width=state.width,
        height=state.height,
        mode=state.mode,
    )
