# brigadista.py
from mesa import Agent
from typing import Tuple, List
from collections import deque
from .blackboard import Blackboard     

class Brigadista(Agent):
    """
    Agente brigadista: se mueve hacia una casilla objetivo y se queda quieto al llegar.
    """
    IDLE = "idle"
    ARRIVED = "arrived"

    def __init__(self, unique_id: str, model, objetivo: Tuple[int, int]):
        super().__init__(unique_id, model)
        self.objetivo = objetivo
        self.state = Brigadista.IDLE
        self.path: List[Tuple[int, int]] = []
        self.blackboard = model.blackboard

        # Blackboard compartido por todos los brigadistas
        if not hasattr(model, 'blackboard'):
            model.blackboard = Blackboard()
        self.blackboard = model.blackboard

    def _find_path(self, target: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Encuentra una ruta hacia la celda objetivo usando BFS, solo por casillas vacías ('.'), evitando muros, fuego y derrumbes.
        """
        visited = {self.pos}
        queue = deque([(self.pos, [])])
        while queue:
            current, path = queue.popleft()
            if current == target:
                return path
            x, y = current
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.model.width and 0 <= ny < self.model.height):
                    continue
                if (nx, ny) in visited:
                    continue
                cell_safe = False
                for obj in self.model.grid.get_cell_list_contents((nx, ny)):
                    cell_type = getattr(obj, "cell_type", None)
                    if cell_type == ".":
                        cell_safe = True
                    elif cell_type in ("#", "F", "D"):
                        cell_safe = False
                        break
                if cell_safe:
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [(nx, ny)]))
        return []
    
    def _get_help(self) -> Tuple[int, int]:
        """
        Consulta la posición más cercana entre los otros brigadistas (usando el blackboard)
        y una lista de posiciones extra (tuplas). Retorna la posición más cercana.
        """
        # Posiciones de las salidas
        salidas : List[Tuple[int, int]] = [(4,0), (5,0), (46,0), (47,0), (20, 39), (21,39), (0, 31), (0, 32), (0, 33), (0, 34), (48, 23), (48, 24), (48, 25)]
        
        # Posiciones de otros brigadistas
        posiciones_otros = [v for k, v in self.blackboard.read_all_positions().items() if k != self.unique_id]
        todas = posiciones_otros + list(salidas)
        
        if not todas:
            return self.pos
        
        # Buscar la posición más cercana
        x0, y0 = self.pos
        def distancia(p):
            return abs(x0 - p[0]) + abs(y0 - p[1])
        return min(todas, key=distancia)

    def step(self):
        # Registrar posición propia en el blackboard
        self.blackboard.write_position(self.unique_id, self.pos)
        if self.state == Brigadista.ARRIVED:
            return

        # Consultar posiciones de otros brigadistas (ejemplo de uso)
        # posiciones_otros = {k: v for k, v in self.blackboard.read_all_positions().items() if k != self.unique_id}

        # Si no tiene ruta, la calcula
        if not self.path:
            self.path = self._find_path(self.objetivo)
        # Si tiene ruta, avanza
        if self.path:
            next_pos = self.path.pop(0)
            self.model.grid.move_agent(self, next_pos)
            if next_pos == self.objetivo:
                self.state = Brigadista.ARRIVED
