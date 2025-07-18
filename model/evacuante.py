# evacuante.py

from typing import Tuple, List
from mesa import Agent

from model.brigadista import Brigadista


class Evacuante(Agent):
    """
    Agente que representa a una persona que debe evacuar el edificio.
    Su comportamiento depende del estado global (alarma activa) y su
    percepción local (visión). Puede moverse aleatoriamente o buscar salidas.
    """

    # ---------- ESTADOS POSIBLES DEL AGENTE ----------
    IDLE         = "idle"        # Estado inicial: camina sin alarma
    EVACUATING   = "evacuating"  # Alarma activa: busca una salida
    BLOCKED      = "blocked"     # No puede avanzar (bloqueado)
    EVACUATED    = "evacuated"   # Llegó a una salida
    MUERTO       = "muerto"      # El agente ha muerto por fuego

    def __init__(self, unique_id: str, model, vision: int = 3):
        """
        Inicializa el evacuante.
        :param unique_id: ID único del agente
        :param model: Referencia al modelo global (ShoppingModel)
        :param vision: Rango de percepción (distancia Manhattan)
        """
        super().__init__(unique_id, model)
        self.state         = Evacuante.IDLE                  # Estado inicial
        self.vision        = vision                          # Rango de visión
        self.path: List[Tuple[int, int]] = []                # Ruta hacia salida (cuando la tiene)
        self.ticks_waiting = 0                               # Cuántos ticks ha estado bloqueado

    # ================================
    # PERCEPCIÓN
    # ================================

    def _get_neighborhood(self) -> List[Tuple[int, int]]:
        """
        Devuelve una lista de coordenadas dentro del rango de visión del agente.
        La distancia utilizada es la de Manhattan.
        """
        x, y = self.pos
        cells = []
        for dx in range(-self.vision, self.vision + 1):
            for dy in range(-self.vision, self.vision + 1):
                if abs(dx) + abs(dy) <= self.vision:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.model.width and 0 <= ny < self.model.height:
                        cells.append((nx, ny))
        return cells

    def _see_exit(self, neighborhood: List[Tuple[int, int]]) -> Tuple[int, int] | None:
        """
        Recorre su vecindario y retorna la posición de la primera salida visible ('S').
        Si no ve ninguna, devuelve None.
        """
        for pos in neighborhood:
            for obj in self.model.grid.get_cell_list_contents(pos):
                if getattr(obj, "cell_type", None) == "S":
                    print("📗 Evacuante", self.unique_id, "ve salida en:", pos)
                    return pos
        return None

    # ================================
    # MOVIMIENTO
    # ================================

    def _find_path(self, target: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Encuentra una ruta hacia la celda objetivo (target), usando BFS (anchura).
        Evita celdas bloqueadas como fuego ('F'), derrumbe ('D') y muros ('#').
        Devuelve una lista de coordenadas con el camino o lista vacía si no hay.
        """
        from collections import deque

        visited = {self.pos}
        queue   = deque([(self.pos, [])])  # tupla: (posición actual, camino hasta aquí)

        while queue:
            current, path = queue.popleft()
            if current == target:
                return path  # ruta encontrada

            x, y = current
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:  # vecinos cardinales
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.model.width and 0 <= ny < self.model.height):
                    continue
                if (nx, ny) in visited:
                    continue

                # Verifica que la celda no sea peligrosa o muro
                cell_safe = True
                for obj in self.model.grid.get_cell_list_contents((nx, ny)):
                    cell_type = getattr(obj, "cell_type", None)
                    if cell_type in ("#", "F", "D", "L"):
                        cell_safe = False
                        break
                    if cell_type == "S" and (nx, ny) != target:
                        cell_safe = False
                        break

                if cell_safe:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))

        return []  # No se encontró camino

    def _move_along_path(self):
        """
        Avanza una casilla siguiendo su ruta calculada.
        Si no tiene ruta, no se mueve.
        """
        if self.path:
            next_pos = self.path.pop(0)
            self.model.grid.move_agent(self, next_pos)

    # ================================
    # INTERACCIÓN (Ejemplo básico)
    # ================================

    def _communicate(self):
        """
        Comunicación mínima: si queda bloqueado, informa al modelo
        la posición para que otros agentes puedan evitarla.
        (Requiere que el modelo implemente report_blocked).
        """
        if self.state == Evacuante.BLOCKED:
            self.model.report_blocked(self.pos)

    # ================================
    # CICLO DE VIDA (STEP)
    # ================================

    def step(self):
        """
        Define el comportamiento del agente en cada tick:
        - Si se activa la alarma y está IDLE, cambia a EVACUATING.
        - Si está evacuando, sigue su ruta o recalcula.
        - Si está bloqueado o evacuado, se queda quieto.
        - Si está IDLE, se mueve aleatoriamente por el entorno.
        """
        if self.state in (Evacuante.EVACUATED, Evacuante.MUERTO):
            return

        # 1. Transición a estado de evacuación si se activa la alarma
        if self.model.alarma_activa and self.state == Evacuante.IDLE:
            self.state = Evacuante.EVACUATING
            #salida = self.model.salida_mas_cercana(self.pos) #TODO: descomentar si se quiere calcular salida al inicio
            #if salida:
            #    self.path = self._find_path(salida)

        # 2. Escanear su entorno
        neighborhood = self._get_neighborhood()
        salida_visible = self._see_exit(neighborhood)
        self._compartir_ruta_con_evacuantes(neighborhood)

        # 3. Comportamiento según el estado actual
        if self.state == Evacuante.EVACUATING:
            # Si ve una salida, intenta recalcular la ruta hacia ella
            if salida_visible:
                if not self.path or self.path[-1] != salida_visible:
                    self.path = self._find_path(salida_visible)

            # Si su ruta quedó vacía o no es válida, busca nueva salida
            #if not self.path: TODO: descomentar si se quiere recalcular ruta al no tener salida
            #    salida = self.model.salida_mas_cercana(self.pos)
            #    if salida:
            #        self.path = self._find_path(salida)
            #    else:
            #        self.state = Evacuante.BLOCKED  # no hay ruta posible
            else:
                brigadista = self._see_brigadista(neighborhood)
                if brigadista:
                    destino_recomendado = brigadista._get_help() 
                    print(f"➡️ Destino recomendado por brigadista {brigadista.unique_id}: {destino_recomendado}")
                    if not self.path or self.path[-1] != destino_recomendado:
                        self.path = self._find_path(destino_recomendado)
            # Avanza un paso
            if self.path:
                self._move_along_path()
            else:
                self.random_move()

            # Revisa si ya llegó a una salida
            for obj in self.model.grid.get_cell_list_contents(self.pos):
                if getattr(obj, "cell_type", None) == "S":
                    self.state = Evacuante.EVACUATED
                    self.path = []
                    return

        elif self.state == Evacuante.IDLE:
            # Si no hay alarma, se mueve aleatoriamente por los pasillos
            self.random_move()

        # 4. Comunicación básica
        self._communicate()
        for obj in self.model.grid.get_cell_list_contents(self.pos):
            if getattr(obj, "cell_type", None) == "F":
                self.state = Evacuante.MUERTO
                self.path = []
                print(f"🔥 {self.unique_id} murió en {self.pos} por fuego")
                return
        #self.random_move() # TODO se coloca provisionalmente para evitar que se quede parado

    # ================================
    # MOVIMIENTO ALEATORIO (IDLE)
    # ================================

    def random_move(self):
        """
        Se mueve a una de las celdas vecinas que sean pasillos ('.'),
        siempre que no estén ocupadas por otro evacuante.
        Imprime el movimiento en consola para depuración.
        """
        from random import shuffle
        x0, y0 = self.pos
        vecinos = [(x0+dx, y0+dy) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]
        shuffle(vecinos)

        for nx, ny in vecinos:
            if 0 <= nx < self.model.width and 0 <= ny < self.model.height:
                # Revisa si hay una ShoppingCell con tipo '.'
                celda = next(
                    (a for a in self.model.grid.get_cell_list_contents((nx, ny))
                     if a.__class__.__name__ == "ShoppingCell"),  # evita import circular
                    None
                )
                if celda is None or celda.cell_type != ".":
                    continue

                # Evita moverse a una celda ya ocupada por otro evacuante
                if any(isinstance(a, Evacuante)
                       for a in self.model.grid.get_cell_list_contents((nx, ny))):
                    continue

                # Movimiento válido: se mueve y reporta
                self.model.grid.move_agent(self, (nx, ny))
                print(f"{self.unique_id}: ({x0},{y0}) → ({nx},{ny})")
                break

    def _see_brigadista(self, neighborhood: List[Tuple[int, int]]) -> Brigadista | None:
        """
        Recorre el vecindario buscando un brigadista visible.
        Si encuentra alguno, retorna su posición. Si no, None.
        """
        for pos in neighborhood:
            for obj in self.model.grid.get_cell_list_contents(pos):
                if isinstance(obj, Brigadista):
                    print(f"🧡 {self.unique_id} ve a un brigadista en {pos}")
                    return obj
        return None

    def _compartir_ruta_con_evacuantes(self, neighborhood: List[Tuple[int, int]]):
        """
        Si este agente tiene una ruta, la comparte con evacuantes cercanos que no tengan una.
        """
        if not self.path:
            return  # No hay nada que compartir

        for pos in neighborhood:
            for obj in self.model.grid.get_cell_list_contents(pos):
                if isinstance(obj, Evacuante) and obj != self:
                    if obj.state == Evacuante.EVACUATING and not obj.path:
                        # Copia la ruta desde la posición actual del otro agente
                        index_actual = next((i for i, p in enumerate(self.path) if p == obj.pos), None)
                        if index_actual is not None:
                            nueva_ruta = self.path[index_actual + 1:]  # Saltearse su propia posición
                        else:
                            nueva_ruta = list(self.path)  # Copia completa si no está en el camino

                        obj.path = nueva_ruta
                        print(f"🔁 {self.unique_id} compartió ruta con {obj.unique_id}")
