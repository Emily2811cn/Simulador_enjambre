from __future__ import annotations
import os
import multiprocessing as mp
from dataclasses import replace
from typing import Tuple

from state import (
    GameState, Hormiga, Feromona,
    actualizar_chunk, evaporar_feromona
)

# ---------------------------------------------------------------------------
# Configuración del sistema
# ---------------------------------------------------------------------------

N_CORES:   int = os.cpu_count() or 1
N_WORKERS: int = max(1, N_CORES - 1)

_POOL: mp.Pool = None


def get_pool() -> mp.Pool:
    """
    Retorna el Pool global, creándolo si no existe todavía.
    Al crearlo una sola vez, el costo de arrancar los workers
    se paga solo al inicio, no en cada frame.
    """
    global _POOL
    if _POOL is None:
        _POOL = mp.Pool(processes=N_WORKERS)
    return _POOL


def close_pool() -> None:
    """Cierra el Pool al terminar el programa."""
    global _POOL
    if _POOL is not None:
        _POOL.close()
        _POOL.join()
        _POOL = None


def get_system_info() -> dict:
    return {"total_cores": N_CORES, "active_workers": N_WORKERS}


# ---------------------------------------------------------------------------
# Segmentación de hormigas (función pura)
# ---------------------------------------------------------------------------

def segmentar_hormigas(
    hormigas: Tuple[Hormiga, ...],
    n_workers: int
) -> Tuple[Tuple[Hormiga, ...], ...]:
    """
    Divide la tupla de hormigas en n_workers segmentos proporcionales.
    FUNCIÓN PURA.
    """
    total = len(hormigas)
    if total == 0:
        return ((),)
    chunk_size = max(1, total // n_workers)
    return tuple(
        hormigas[i: i + chunk_size]
        for i in range(0, total, chunk_size)
    )


# ---------------------------------------------------------------------------
# Actualización de feromonas (función pura)
# ---------------------------------------------------------------------------

def actualizar_feromonas(
    feromonas_existentes: Tuple[Feromona, ...],
    nuevas_feromonas: Tuple[Feromona, ...],
) -> Tuple[Feromona, ...]:
    """
    Evapora feromonas existentes, añade nuevas y limita a 2000.
    Límite reducido de 5000 a 2000 para evitar saturación del CPU.
    FUNCIÓN PURA.
    """
    evaporadas = tuple(
        replace(f, intensidad=f.intensidad * 0.995)
        for f in feromonas_existentes
        if f.intensidad * 0.995 > 1.0
    )
    combinadas = evaporadas + nuevas_feromonas

    if len(combinadas) > 2000:
        combinadas = tuple(
            sorted(combinadas, key=lambda f: f.intensidad, reverse=True)[:2000]
        )
    return combinadas


# ---------------------------------------------------------------------------
# Actualización PARALELA — Pool reutilizado
# ---------------------------------------------------------------------------

def parallel_update(state: GameState) -> GameState:
    """
    Actualiza todas las hormigas usando múltiples procesos en paralelo.

    CORRECCIÓN: usa get_pool() en vez de crear un Pool nuevo cada frame.
    Antes:  with mp.Pool() as pool:  ← creaba/destruía 7 procesos por frame
    Ahora:  pool = get_pool()        ← reutiliza el mismo Pool siempre
    """
    chunks = segmentar_hormigas(state.hormigas, N_WORKERS)

    args_list = tuple(
        (chunk, state.comidas, state.feromonas, state.nido, state.width, state.height)
        for chunk in chunks
    )

    pool = get_pool()
    resultados = pool.map(actualizar_chunk, args_list)

    todas_hormigas   = tuple(h for r in resultados for h in r[0])
    nuevas_feromonas = tuple(f for r in resultados for f in r[1])
    total_entregada  = sum(r[2] for r in resultados)

    feromonas_mundo = actualizar_feromonas(state.feromonas, nuevas_feromonas)
    nuevo_nido = replace(
        state.nido,
        comida_recolectada=state.nido.comida_recolectada + total_entregada
    )

    return replace(
        state,
        hormigas=todas_hormigas,
        feromonas=feromonas_mundo,
        nido=nuevo_nido,
        frame=state.frame + 1,
    )


# ---------------------------------------------------------------------------
# Actualización SECUENCIAL — un solo núcleo
# ---------------------------------------------------------------------------

def sequential_update(state: GameState) -> GameState:
    """
    Actualiza todas las hormigas en un solo proceso.
    Usado para comparativa de rendimiento vs modo paralelo.
    """
    args = (
        state.hormigas,
        state.comidas,
        state.feromonas,
        state.nido,
        state.width,
        state.height,
    )
    hormigas_nuevas, nuevas_feromonas, total_entregada = actualizar_chunk(args)
    feromonas_mundo = actualizar_feromonas(state.feromonas, nuevas_feromonas)
    nuevo_nido = replace(
        state.nido,
        comida_recolectada=state.nido.comida_recolectada + total_entregada
    )
    return replace(
        state,
        hormigas=hormigas_nuevas,
        feromonas=feromonas_mundo,
        nido=nuevo_nido,
        frame=state.frame + 1,
    )


# ---------------------------------------------------------------------------
# Punto de entrada unificado
# ---------------------------------------------------------------------------

def update(state: GameState) -> GameState:
    """Decide qué motor usar según state.mode."""
    if state.mode == "parallel":
        return parallel_update(state)
    return sequential_update(state)
