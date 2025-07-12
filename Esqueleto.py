from mesa import Model, Agent
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer
import random

# ---------- CELDAS (sean pared, fuego, salida, etc.) ----------
class MapaCell(Agent):
    def __init__(self, unique_id, model, cell_type):
        super().__init__(unique_id, model)
        self.type = cell_type   # '#', '.', 'F', 'D', 'S', 'L'

    def step(self):
        # Las celdas no hacen nada (son obstáculo/terreno)
        pass


# ---------- AGENTE BRIGADISTA (FIJO) ----------
class Brigadista(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        # lista global de salidas (tu modelo la rellenará)
        self.salidas = model.salidas  

    def step(self):
        # 1. mirar si hay evacuantes en Moore de radio 1
        vecinos = self.model.grid.get_neighbors(self.pos, moore=True, include_center=False, radius=1)
        evacuantes_cercanos = [a for a in vecinos if isinstance(a, Evacuante)]

        if not evacuantes_cercanos:
            return   # nada que hacer este tick

        # 2. escoger la salida más cercana a cada evacuante
        for evac in evacuantes_cercanos:
            # mandarles un "mensaje" sencillo: vector dirección a la salida
            dx, dy = self.vector_hacia_salida_mas_cercana(evac.pos)
            evac.recibir_instruccion((dx, dy))

    # --- utilidades ---
    def vector_hacia_salida_mas_cercana(self, origen):
        # calcula diferencia x,y hacia la salida más cercana
        salx, saly = min(self.salidas,
                         key=lambda s: abs(s[0]-origen[0]) + abs(s[1]-origen[1]))
        return (salx - origen[0], saly - origen[1])


# ---------- AGENTE EVACUANTE (MÓVIL) ----------
class Evacuante(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.instruccion = None  # recibe (dx,dy) del brigadista

    # ------- percepción y decisión principal -------
    def step(self):
        # 1. si ya estoy en salida => me retiro del scheduler
        if self.esta_en_salida():
            self.model.grid.remove_agent(self)
            self.model.schedule.remove(self)
            return

        # 2. priorizar instrucción de brigadista
        if self.instruccion:
            self.mover_por_vector(self.instruccion)
            self.instruccion = None
            return

        # 3. ¿veo salida en rango 4?
        dir_a_salida = self.buscar_salida_visible(rango=4)
        if dir_a_salida:
            self.mover_por_vector(dir_a_salida)
            return

        # 4. por defecto: movimiento aleatorio, evitando obstáculos
        self.mover_aleatorio_seguro()

    # ------- helpers -------
    def recibir_instruccion(self, vector):
        self.instruccion = vector

    def esta_en_salida(self):
        celda = [a for a in self.model.grid.get_cell_list_contents([self.pos])
                 if isinstance(a, MapaCell)][0]
        return celda.type == 'S'

    def mover_por_vector(self, vector):
        dx = 1 if vector[0] > 0 else -1 if vector[0] < 0 else 0
        dy = 1 if vector[1] > 0 else -1 if vector[1] < 0 else 0
        nueva = (self.pos[0]+dx, self.pos[1]+dy)
        if self.celda_es_transitable(nueva):
            self.model.grid.move_agent(self, nueva)
        else:
            self.mover_aleatorio_seguro()

    def buscar_salida_visible(self, rango):
        x0, y0 = self.pos
        for dx in range(-rango, rango+1):
            for dy in range(-rango, rango+1):
                x, y = x0+dx, y0+dy
                if not self.model.grid.out_of_bounds((x, y)):
                    contenido = self.model.grid.get_cell_list_contents([(x, y)])
                    for obj in contenido:
                        if isinstance(obj, MapaCell) and obj.type == 'S':
                            return (dx, dy)
        return None

    def mover_aleatorio_seguro(self):
        opciones = self.model.grid.get_neighborhood(self.pos, moore=True,
                                                    include_center=False)
        random.shuffle(opciones)
        for dest in opciones:
            if self.celda_es_transitable(dest):
                self.model.grid.move_agent(self, dest)
                break

    def celda_es_transitable(self, pos):
        if self.model.grid.out_of_bounds(pos):
            return False
        for obj in self.model.grid.get_cell_list_contents([pos]):
            if isinstance(obj, MapaCell) and obj.type in {'#', 'F', 'D'}:
                return False
        return True


# ---------- MODELO PRINCIPAL ----------
class EvacuacionModel(Model):
    def __init__(self, width=20, height=20, n_evacuantes=15):
        super().__init__()
        self.grid    = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.salidas = []         # se rellenará al construir el mapa

        # 1. ---- Crear mapa fijo ----
        mapa_txt = [
            "####S####S#####S####",
            "#LL...DF..LLLLL..LL#",
            "#LL.F.D...LDFDL..LL#",
            "#LL..FD...LDFFL..FL#",
            "#FF...D...LFFFL..DF#",
            "#FFLLFDD...FFF...DD#",
            "#FDLLLLL...........#",
            "#LDFLLLL..LLL..L...#",
            "#....LLL..LLL..L...#",
            "S....LLL.......L...S",
            "#....LFL.......L...#",
            "#....LLF...LLLLL...#",
            "#..........DDDLL...#",
            "#.........DD.D...LL#",
            "#LL....FFFDD.....LL#",
            "#LL...LFFFDDLL...LL#",
            "#LL...LLLLLFFL...LL#",
            "#LL...LLLLLFFL..LLL#",
            "#LL...LLLLLFLL..LLL#",
            "####S##########S####"
        ]
        uid = 0
        for y, row in enumerate(mapa_txt):
            for x, ch in enumerate(row):
                cell = MapaCell(uid, self, ch)
                self.grid.place_agent(cell, (x, y))
                self.schedule.add(cell)
                if ch == 'S':
                    self.salidas.append((x, y))
                uid += 1

        # 2. ---- Brigadistas fijos ----
        pos_brigadistas = [(4, 1), (10, 9), (15, 15)]
        for i, pos in enumerate(pos_brigadistas):
            brig = Brigadista(f"B{i}", self)
            self.grid.place_agent(brig, pos)
            self.schedule.add(brig)

        # 3. ---- Evacuantes móviles ----
        for i in range(n_evacuantes):
            evac = Evacuante(f"E{i}", self)
            # buscamos celda transitable aleatoria
            while True:
                x, y = random.randrange(width), random.randrange(height)
                if self.celda_transitable_para_inicial((x, y)):
                    self.grid.place_agent(evac, (x, y))
                    self.schedule.add(evac)
                    break

    def celda_transitable_para_inicial(self, pos):
        for obj in self.grid.get_cell_list_contents([pos]):
            if isinstance(obj, MapaCell) and obj.type in {'.', 'L'}:
                return True
        return False

    def step(self):
        self.schedule.step()


# ---------- VISUALIZACIÓN ----------
def agent_portrayal(agent):
    portrayal = {"Shape": "rect", "w": 1, "h": 1, "Layer": 0, "Filled": "true"}

    if isinstance(agent, MapaCell):
        colors = {'#': "brown", '.': "white", 'F': "red",
                  'D': "black", 'S': "green", 'L': "lightblue"}
        portrayal["Color"] = colors.get(agent.type, "white")

    elif isinstance(agent, Brigadista):
        portrayal.update({"Shape": "circle", "Color": "orange",
                          "Layer": 1, "r": 0.6})

    elif isinstance(agent, Evacuante):
        portrayal.update({"Shape": "circle", "Color": "purple",
                          "Layer": 2, "r": 0.4})

    return portrayal


grid = CanvasGrid(agent_portrayal, 20, 20, 500, 500)
server = ModularServer(EvacuacionModel,
                       [grid],
                       "Simulación de Evacuación",
                       {"width": 20, "height": 20, "n_evacuantes": 15})
server.port = 8521
# server.launch()   # Descomenta para ejecutar
