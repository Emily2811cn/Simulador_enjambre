
from __future__ import annotations
import sys
import math
import pygame
from dataclasses import replace

from state import (
    GameState, crear_estado_inicial, toggle_mode,
    BUSCANDO, REGRESANDO
)
from parallel_engine import update, close_pool
from benchmark import FPSCounter, BenchmarkTable, render_metrics, handle_entity_count_key

WIDTH      = 1100
HEIGHT     = 700
TITLE      = "Colonia de Hormigas — Paralelismo Funcional"
TARGET_FPS = 60

C_BG              = (20, 15, 10)
C_COMIDA          = (255, 210, 0)
C_NIDO            = (139, 90, 43)
C_NIDO_B          = (200, 140, 70)
C_HORMIGA_BUSCA   = (220, 60, 60)
C_HORMIGA_REGRESA = (255, 160, 20)
C_TEXTO_NIDO      = (255, 255, 200)

def render_feromonas(screen, state):
    for f in state.feromonas:
        alpha = min(255, int(f.intensidad * 1.4))
        pygame.draw.circle(
            screen, (0, alpha // 2, alpha // 4),
            (int(f.x), int(f.y)), 3
        )


def render_comidas(screen, state):
    for c in state.comidas:
        if c.cantidad > 0:
            r = max(4, int(c.cantidad / 30 * 18))
            pygame.draw.circle(screen, C_COMIDA, (int(c.x), int(c.y)), r)
            pygame.draw.circle(screen, (255, 255, 255), (int(c.x), int(c.y)), r, 1)


def render_nido(screen, state):
    nido = state.nido
    pygame.draw.circle(screen, C_NIDO,  (int(nido.x), int(nido.y)), 22)
    pygame.draw.circle(screen, C_NIDO_B,(int(nido.x), int(nido.y)), 22, 3)
    font = pygame.font.SysFont("monospace", 11, bold=True)
    screen.blit(font.render("NIDO", True, C_TEXTO_NIDO),
                (int(nido.x) - 14, int(nido.y) - 8))
    screen.blit(font.render(f"+{nido.comida_recolectada}", True, C_COMIDA),
                (int(nido.x) - 10, int(nido.y) + 2))


def render_hormigas(screen, state):
    for h in state.hormigas:
        col = C_HORMIGA_REGRESA if h.estado == REGRESANDO else C_HORMIGA_BUSCA
        pygame.draw.circle(screen, col, (int(h.x), int(h.y)), 3)
        tip_x = h.x + math.cos(h.angulo) * 5
        tip_y = h.y + math.sin(h.angulo) * 5
        pygame.draw.line(screen, col,
                         (int(h.x), int(h.y)),
                         (int(tip_x), int(tip_y)), 1)


def render(screen, state, fps_counter, table):
    screen.fill(C_BG)
    render_feromonas(screen, state)
    render_comidas(screen, state)
    render_nido(screen, state)
    render_hormigas(screen, state)
    render_metrics(screen, state, fps_counter, table)
    pygame.display.flip()


def process_events(state: GameState):
    running   = True
    new_state = state
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_p:
                new_state = toggle_mode(new_state)
            elif event.key in (pygame.K_1, pygame.K_3, pygame.K_5):
                new_state = handle_entity_count_key(event.key, new_state)
    return new_state, running


def run():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen      = pygame.display.set_mode((WIDTH, HEIGHT))
    clock       = pygame.time.Clock()
    state       = crear_estado_inicial(500, WIDTH, HEIGHT, mode="sequential")
    fps_counter = FPSCounter()
    table       = BenchmarkTable()
    running     = True

    while running:
        state, running = process_events(state)
        if not running:
            break
        state = update(state)
        fps_counter.tick()
        render(screen, state, fps_counter, table)
        clock.tick(TARGET_FPS)

    close_pool()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    run()
