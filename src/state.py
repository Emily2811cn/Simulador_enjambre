from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Tuple
import math
import random


# Constantes del simulador

VELOCIDAD_HORMIGA  = 1.8    # píxeles por frame
RADIO_VISION       = 40.0   # radio con el que detecta comida/feromonas
RADIO_NIDO         = 20.0   # radio del nido (zona de entrega)
RADIO_COMIDA       = 6.0    # radio de cada fuente de comida
EVAPORACION        = 0.995  # las feromonas se evaporan cada frame (0.995 = lento)
FUERZA_FEROMONA    = 180.0  # intensidad inicial de la feromona al depositarla


# Estados posibles de una hormiga

BUSCANDO   = "buscando"    # hormiga explorando sin comida
REGRESANDO = "regresando"  # hormiga cargando comida, vuelve al nido



# Estructuras de datos inmutables

@dataclass(frozen=True)
class Hormiga:
    x: float
    y: float
    angulo: float
    estado: str = BUSCANDO
    comida_x: float = 0.0
    comida_y: float = 0.0

@dataclass(frozen=True)
class Comida:

    x: float
    y: float
    cantidad: int = 30

@dataclass(frozen=True)
class Feromona:
    x: float
    y: float
    intensidad: float

@dataclass(frozen=True)
class Nido:
    """El nido de la colonia — punto de entrega de comida."""
    x: float
    y: float
    comida_recolectada: int = 0

@dataclass(frozen=True)
class GameState:
    hormigas:   Tuple[Hormiga, ...]
    comidas:    Tuple[Comida, ...]
    feromonas:  Tuple[Feromona, ...]
    nido:       Nido
    frame:      int
    mode:       str    # "sequential" | "parallel"
    width:      int
    height:     int

# Funciones de construcción inicial (puras)

def crear_hormiga(nido: Nido) -> Hormiga:
    return Hormiga(
        x=nido.x + random.uniform(-10, 10),
        y=nido.y + random.uniform(-10, 10),
        angulo=random.uniform(0, 2 * math.pi),
    )

def crear_comida(width: int, height: int, nido: Nido) -> Comida:
    while True:
        x = random.uniform(50, width - 50)
        y = random.uniform(50, height - 50)
        dist = math.hypot(x - nido.x, y - nido.y)
        if dist > 150:   # que no aparezca encima del nido
            return Comida(x=x, y=y, cantidad=30)

def crear_estado_inicial(
    n_hormigas: int,
    width: int,
    height: int,
    mode: str = "sequential"
) -> GameState:
    nido = Nido(x=width / 2, y=height / 2)

    hormigas  = tuple(crear_hormiga(nido) for _ in range(n_hormigas))
    comidas   = tuple(crear_comida(width, height, nido) for _ in range(6))
    feromonas = ()   # empieza sin feromonas

    return GameState(
        hormigas=hormigas,
        comidas=comidas,
        feromonas=feromonas,
        nido=nido,
        frame=0,
        mode=mode,
        width=width,
        height=height,
    )

# Funciones puras de transformación de hormigas

def distancia(x1: float, y1: float, x2: float, y2: float) -> float:
    """Distancia euclidiana entre dos puntos."""
    return math.hypot(x2 - x1, y2 - y1)


def angulo_hacia(x1: float, y1: float, x2: float, y2: float) -> float:
    """Ángulo (radianes) desde el punto (x1,y1) hacia (x2,y2)."""
    return math.atan2(y2 - y1, x2 - x1)


def mover_hormiga(hormiga: Hormiga, width: int, height: int) -> Hormiga:
 
    new_x = hormiga.x + VELOCIDAD_HORMIGA * math.cos(hormiga.angulo)
    new_y = hormiga.y + VELOCIDAD_HORMIGA * math.sin(hormiga.angulo)
    new_angulo = hormiga.angulo

    # Rebote en bordes
    if new_x < 0 or new_x > width:
        new_angulo = math.pi - new_angulo
        new_x = max(0.0, min(float(width), new_x))
    if new_y < 0 or new_y > height:
        new_angulo = -new_angulo
        new_y = max(0.0, min(float(height), new_y))

    return replace(hormiga, x=new_x, y=new_y, angulo=new_angulo)


def actualizar_hormiga_buscando(
    hormiga: Hormiga,
    comidas: Tuple[Comida, ...],
    feromonas: Tuple[Feromona, ...],
    nido: Nido,
    width: int,
    height: int,
) -> Hormiga:

    for comida in comidas:
        if comida.cantidad > 0 and distancia(hormiga.x, hormiga.y, comida.x, comida.y) < RADIO_VISION:
            # ¡Encontró comida! → apuntar hacia ella
            angulo_comida = angulo_hacia(hormiga.x, hormiga.y, comida.x, comida.y)
            hormiga_apuntando = replace(hormiga, angulo=angulo_comida)
            hormiga_movida = mover_hormiga(hormiga_apuntando, width, height)
            # Si llegó a la comida → recogerla
            if distancia(hormiga_movida.x, hormiga_movida.y, comida.x, comida.y) < RADIO_COMIDA + 2:
                angulo_regreso = angulo_hacia(hormiga_movida.x, hormiga_movida.y, nido.x, nido.y)
                return replace(
                    hormiga_movida,
                    estado=REGRESANDO,
                    comida_x=comida.x,
                    comida_y=comida.y,
                    angulo=angulo_regreso,
                )
            return hormiga_movida

    # ¿Hay feromonas cercanas? -> seguirlas
    feromonas_cercanas = [
        f for f in feromonas
        if distancia(hormiga.x, hormiga.y, f.x, f.y) < RADIO_VISION and f.intensidad > 10
    ]
    if feromonas_cercanas:
        # Ir hacia la feromona más intensa
        mejor = max(feromonas_cercanas, key=lambda f: f.intensidad)
        angulo_feromona = angulo_hacia(hormiga.x, hormiga.y, mejor.x, mejor.y)
        # Mezcla: 70% feromona, 30% dirección actual (no giro brusco)
        nuevo_angulo = angulo_feromona * 0.7 + hormiga.angulo * 0.3
        return mover_hormiga(replace(hormiga, angulo=nuevo_angulo), width, height)

    # Exploración aleatoria: pequeño giro aleatorio
    giro = random.uniform(-0.3, 0.3)
    return mover_hormiga(replace(hormiga, angulo=hormiga.angulo + giro), width, height)


def actualizar_hormiga_regresando(
    hormiga: Hormiga,
    nido: Nido,
    width: int,
    height: int,
) -> tuple:

    angulo_nido = angulo_hacia(hormiga.x, hormiga.y, nido.x, nido.y)
    hormiga_apuntando = replace(hormiga, angulo=angulo_nido)
    hormiga_movida = mover_hormiga(hormiga_apuntando, width, height)

    if distancia(hormiga_movida.x, hormiga_movida.y, nido.x, nido.y) < RADIO_NIDO:
        # Llegó al nido → entregar y volver a buscar
        angulo_salida = random.uniform(0, 2 * math.pi)
        return replace(hormiga_movida, estado=BUSCANDO, angulo=angulo_salida), True

    return hormiga_movida, False


def depositar_feromona(hormiga: Hormiga) -> Feromona:
    #Crea una feromona en la posición actual de la hormiga.Solo se llama cuando la hormiga está REGRESANDO.FUNCIÓN PURA.
    return Feromona(x=hormiga.x, y=hormiga.y, intensidad=FUERZA_FEROMONA)


def evaporar_feromona(feromona: Feromona) -> Feromona:
    return replace(feromona, intensidad=feromona.intensidad * EVAPORACION)


# Función que los workers ejecutan en paralelo (un chunk de hormigas)

def actualizar_chunk(args: tuple) -> tuple:

    chunk, comidas, feromonas, nido, width, height = args

    nuevas_hormigas   = []
    nuevas_feromonas  = []
    comida_entregada  = 0

    for hormiga in chunk:
        if hormiga.estado == BUSCANDO:
            nueva = actualizar_hormiga_buscando(
                hormiga, comidas, feromonas, nido, width, height
            )
            nuevas_hormigas.append(nueva)

        else:  # REGRESANDO
            nueva, entrego = actualizar_hormiga_regresando(hormiga, nido, width, height)
            nuevas_hormigas.append(nueva)
            if entrego:
                comida_entregada += 1
            else:
                # Deposita feromona mientras regresa
                nuevas_feromonas.append(depositar_feromona(nueva))

    return tuple(nuevas_hormigas), tuple(nuevas_feromonas), comida_entregada


# Utilidades de estado

def toggle_mode(state: GameState) -> GameState:
    nuevo_modo = "parallel" if state.mode == "sequential" else "sequential"
    return replace(state, mode=nuevo_modo)

def contar_buscando(state: GameState) -> int:
    return sum(1 for h in state.hormigas if h.estado == BUSCANDO)

def contar_regresando(state: GameState) -> int:
    return sum(1 for h in state.hormigas if h.estado == REGRESANDO)
