# === LIBRERÍAS DE MESA ===
from random import random
from mesa import Agent, Model                          # Agente base y modelo
from mesa.space import MultiGrid                       # Espacio tipo grilla con múltiples agentes por celda
from mesa.time import SimultaneousActivation           # Activador para que todos los agentes actúen simultáneamente
from mesa.visualization.modules import CanvasGrid      # Visualización de la grilla en HTML
from mesa.visualization.ModularVisualization import ModularServer  # Servidor web para ejecutar la simulación
from mesa.datacollection import DataCollector
from mesa.visualization.modules import TextElement

# === AGENTE MÓVIL: EVACUANTE ===
from .evacuante import Evacuante                       # Importamos el agente Evacuante definido en otro archivo
from .brigadista import Brigadista                     # Importamos el agente Brigadista
from .blackboard import Blackboard                     # Importamos el Blackboard para comunicación entre brigadistas

from random import shuffle
from random import randint, choice

# === PARÁMETROS DE LA VISTA ===
CELL_SIZE = 15                                         # Tamaño de cada celda en píxeles
canvas_width = CELL_SIZE * 49                          # Ancho del canvas en píxeles (49 columnas)
canvas_height = CELL_SIZE * 40                         # Alto del canvas en píxeles (40 filas)

# === AGENTE FIJO: CELDA DEL MAPA ===
class ShoppingCell(Agent):
    """
    Representa una celda del entorno: puede ser un muro, pasillo, local, salida, fuego, etc.
    Es estático, no tiene comportamiento propio.
    """
    def __init__(self, unique_id, model, cell_type):
        super().__init__(unique_id, model)
        self.cell_type = cell_type   # Tipo de celda (carácter del mapa)

    def step(self):
        pass  # No hace nada cada tick (es una celda fija)

# === MODELO PRINCIPAL ===
class ShoppingModel(Model):
    """
    Modelo principal del centro comercial.
    Contiene el mapa, los evacuantes y la lógica general del entorno.
    """
    def __init__(self, num_users=25, seed=None):
        super().__init__(seed=seed)              # Crea el generador aleatorio de Mesa
        self.num_users = num_users               # Número de evacuantes a crear
        self.tick_counter  = 0                   # Contador global de ticks
        self.alarma_activa = False               # Bandera de alarma (fuego activado)
        self.blackboard = Blackboard()  # Blackboard compartido por todos los brigadistas

        # --- MAPA ---
        self.map_2d = [
            "####################SS###########################",
            "#.LLL...LL...LLL........LLLLLLLLLLLLLLLLLLLLLL..#",
            "#.LLL...L..LLLLLL.......LLLLL.......LLLLLLLLLL..#",
            "#.LLL.....LLLLLLLL......LLLL.........LLLLLLLLL..#",
            "#.LLL....LLLLLLLLL......LLL...LL..LL..LLLLLLLL..#",
            "S.LLL...LLLLLLLLLL......LL....LL..LL...LLLLLLL..#",
            "S.......LLLLLLLLLL......L.....LL..LL....LLLLLL..#",
            "S.......LLLLLLLLLL......L.....LL..LL.....LLLLL..#",
            "S.......LLLLLLLLLL..............................#",
            "#LLLLL..LLLLLLLLLLLLL...........................#",
            "#LLLLL..LLLLLLLLLLLLL.....LLLLLLLLLLLLLLLLL..LLL#",
            "#LLLLL..LLL..............LLLLLLLLLLLLLLLLLL..LLL#",
            "#LLLLL..LLL.............LLLLLLLLLLLLLLLLLLL..LLL#",
            "#LLLLL..LLL.....................................#",
            "#LLLLL..LLL.....................................S",
            "#L......LLLLLLLLLLLL.....LL.....................S",
            "#L......LLLLLLLLLLLL...LLLLL....................S",
            "#LLLL...LLLLLLLLLLLL...LLLLL...LLLLLLLL..LLL....#",
            "#LLLL..................LLLLL..LLLLLLLL...LLLL...#",
            "#......................LLLLLLLLLLLLLL...LLLLLL..#",
            "#..........LL..........LLLLLLLLLLLLL...LLLLLLL..#",
            "#..........LL..........LLLLLLLLLLLL...LLLLLLLL..#",
            "#LLLLLLLL..LL..LLLLL...LLLLLLLLLLL...LLLLLLLLL..#",
            "#LLLLLLLL..LL..LLLLL...LLLLLLLLLL...LLLLLLLLLL..#",
            "#LLLLLLLL..LL..LLLLL...LLLLLLLLL...LLLLLLLLLLL..#",
            "#..........LL............LLLLLL...LLLLLLLLLLL...#",
            "#...............LLL......LLLLL...LLLLLLLLLLLL...#",
            "#...............LLL..LL..LLLL...LLLLLLLLLLLLLL..#",
            "#LLLLLLLLLLL....LLL..LL..LLLL..LLLLLLLLLLLLLLL..#",
            "#LLLLLLLLLLL....LLL......LLLL..LLLLLLLLL....LL..#",
            "#LLLLLLLLLLL....LLL......LLL...LLLLLLLLL....LL..#",
            "#........LLL....LLL......LLL...LLLLLLLLL....LL..#",
            "#.........LL....LLL..LL..LLL...LLLLLLLLL....LL..#",
            "#......L...L....LLL..LL.........................#",
            "#LL....LL.......................................#",
            "#LL....LLL...LLLLLLLLLL..........LLLL.....LLL...#",
            "#LL....LLLL..LLLLLLLLLL..LLL..LLLLLLLL..........#",
            "#LL....LLLL..LLLLLLLLLL..LLL..LLLLLLLLLLL.......#",
            "#LL....LLLL..LLLLLLLLLL..LLL..LLLLLLLLLLLLLL....#",
            "####SS########################################SS#"
        ]

        # --- AJUSTAR MAPA Y DIMENSIONES ---
        self.height = len(self.map_2d)
        self.width  = max(len(row) for row in self.map_2d)
        self.map_2d = [row.ljust(self.width, '.') for row in self.map_2d]  # Asegura que todas las filas tengan el mismo largo

        self.grid     = MultiGrid(self.width, self.height, torus=False)    # Grilla sin bordes envolventes
        self.schedule = SimultaneousActivation(self)                       # Activador simultáneo

        # --- CREAR CELDAS FIJAS (MUROS, SALIDAS, ETC.) ---
        for y, row in enumerate(self.map_2d):
            for x, symbol in enumerate(row):
                uid         = y * self.width + x
                inverted_y  = self.height - 1 - y            # Invertimos el eje Y para que la visualización no salga al revés
                cell        = ShoppingCell(uid, self, symbol)
                self.grid.place_agent(cell, (x, inverted_y)) # Coloca la celda en el grid
                self.schedule.add(cell)                      # Agrega la celda al scheduler (aunque no hace nada)

        # --- COLOCAR EVACUANTES EN POSICIONES BLANCAS ('.') ---
        empty_positions = [
            (x, self.height - 1 - y)
            for y, row in enumerate(self.map_2d)
            for x, symbol in enumerate(row)
            if symbol == "."
        ]
        self.random.shuffle(empty_positions)  # Aleatoriza posiciones disponibles

        # Coloca evacuantes
        for i in range(min(self.num_users, len(empty_positions))):
            pos   = empty_positions[i]
            agent = Evacuante(f"U{i}", self)     # Crea un evacuante con ID único
            self.grid.place_agent(agent, pos)    # Lo ubica en la posición
            self.schedule.add(agent)             # Lo añade al scheduler

        # --- COLOCAR BRIGADISTAS EN POSICIONES BLANCAS ('.') ---
        brigadista_positions = [(14, 11), (6, 22), (20, 24), (41, 25), (6,7), (24,5), (39, 5), (33, 31), (6, 35)]
        for i, pos in enumerate(brigadista_positions, start=1):
            # Asegurar que la posición es válida
            while True:
                dx = self.random.randint(-4, 4)
                dy = self.random.randint(-4, 4)
                new_x = max(0, pos[0] + dx)
                new_y = max(0, pos[1] + dy)
                if 0 <= new_x < self.width and 0 <= new_y < self.height:
                    # Verifica si la celda es vacía
                    celda = next((a for a in self.grid.get_cell_list_contents((new_x, new_y)) if isinstance(a, ShoppingCell)), None)
                    if celda and celda.cell_type == ".":
                        break
            agent = Brigadista(f"B{i}", self, pos)
            self.grid.place_agent(agent, (new_x, new_y))
            self.schedule.add(agent)
        
        # --- INICIALIZAR DATACOLLECTOR ---
        # Recolector de datos para estadísticas del modelo
        self.datacollector = DataCollector(
            model_reporters={
                "Evacuados": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Evacuante) and a.state == Evacuante.EVACUATED),
                "Muertos": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Evacuante) and a.state == Evacuante.MUERTO),
                "Vivos": lambda m: sum(1 for a in m.schedule.agents if isinstance(a, Evacuante) and a.state not in [Evacuante.EVACUATED, Evacuante.MUERTO]),
                "Tick": lambda m: m.tick_counter,
            }
        )

    # --- MÉTODO PARA GENERAR FUEGO EN CASILLAS DE LOCALES ---
    def _generar_fuego_inicial(self, n_llamas=5):
        """
        Selecciona aleatoriamente 'n_llamas' celdas tipo 'L' (locales)
        y las convierte en fuego ('F').
        """
        from random import sample
        locales = [
            (x, self.height - 1 - y)
            for y, row in enumerate(self.map_2d)
            for x, symbol in enumerate(row)
            if symbol == "L"
        ]

        for pos in sample(locales, min(n_llamas, len(locales))):
            print("🔥 Fuego en:", pos)
            for obj in self.grid.get_cell_list_contents(pos):
                if isinstance(obj, ShoppingCell):
                    obj.cell_type = "F"
                    print("   ↳ Cambiado a fuego:", obj)
                    break

        self.alarma_activa = True  # Activa la alarma global

    def _propagar_fuego(self):
        """
        Propaga el fuego a UNA celda adyacente (local o pasillo) por cada celda en llamas.
        """

        nuevas_llamas = []
        probabilidad_fuego = 0.3  # Probabilidad de que el fuego se propague a una celda adyacente

        for x in range(self.width):
            for y in range(self.height):
                for obj in self.grid.get_cell_list_contents((x, y)):
                    if isinstance(obj, ShoppingCell) and obj.cell_type == "F":
                        # Busca vecinos candidatos
                        if random() < probabilidad_fuego:
                            vecinos = self.grid.get_neighborhood((x, y), moore=True, include_center=False)
                            candidatos = []
                            for nx, ny in vecinos:
                                for vecino in self.grid.get_cell_list_contents((nx, ny)):
                                    if isinstance(vecino, ShoppingCell) and vecino.cell_type in ("L", "."):
                                        candidatos.append((nx, ny))
                            # Si hay candidatos, elige uno al azar
                            if candidatos:
                                shuffle(candidatos)
                                nuevas_llamas.append(candidatos[0])
        # Cambia las celdas seleccionadas a fuego 
        for pos in nuevas_llamas:
            for obj in self.grid.get_cell_list_contents(pos):
                if isinstance(obj, ShoppingCell):
                    obj.cell_type = "F"
                    break

        for pos in nuevas_llamas:
            for obj in self.grid.get_cell_list_contents(pos):
                if isinstance(obj, ShoppingCell):
                    obj.cell_type = "F"
                # Si hay un evacuante en la celda, lo "mata :("
                self.matar_evacuante(pos[0], pos[1], obj, "fuego")

    def _generar_derrumbe(self):
        """
        Cada 8 ticks, genera un derrumbe (barrera de longitud 4) en posición y dirección aleatoria.
        Si un evacuante está debajo, muere.
        """

        # Direcciones posibles: horizontal (1,0) o vertical (0,1)
        direcciones = [(1, 0), (0, 1)]
        dx, dy = choice(direcciones)
        longitud_derrumbe = 4  # Longitud del derrumbe

        # Buscar una posición inicial válida (que no sea muro ni salida)
        intentos = 0
        while True:
            x = randint(0, self.width - 1)
            y = randint(0, self.height - 1)
            posiciones = [(x + i * dx, y + i * dy) for i in range(longitud_derrumbe)]
            # Verifica que todas las posiciones estén dentro del grid y sean transitables
            if all(
                0 <= px < self.width and 0 <= py < self.height
                for px, py in posiciones
            ):
                # Solo permite derrumbe sobre pasillo o local
                celdas_validas = True
                for px, py in posiciones:
                    for obj in self.grid.get_cell_list_contents((px, py)):
                        if isinstance(obj, ShoppingCell) and obj.cell_type not in (".", "L"):
                            celdas_validas = False
                if celdas_validas:
                    break
            intentos += 1
            if intentos > 100:  # Evita bucle infinito si no hay espacio
                return

        # Aplica el derrumbe
        for px, py in posiciones:
            for obj in self.grid.get_cell_list_contents((px, py)):
                if isinstance(obj, ShoppingCell):
                    obj.cell_type = "D"  # Derrumbe
                # Si hay un evacuante en la celda, lo "mata :("
                self.matar_evacuante(px, py, obj, "derrumbe")

    def matar_evacuante(self, px, py, obj, accion):
        """
        Si hay un evacuante en la posición (px, py), lo marca como muerto.
        """
        if isinstance(obj, Evacuante) and obj.state != Evacuante.MUERTO and obj.state != Evacuante.EVACUATED:
            print(f"💀 Evacuante muerto por {accion} en:", (px, py))
            obj.state = Evacuante.MUERTO

    
    # --- AVANCE GLOBAL DEL MODELO ---
    def step(self):
        """
        Ejecuta un paso (tick) de la simulación:
        1. Avanza todos los agentes.
        2. Incrementa el contador.
        3. Dispara el fuego en el tick 2.
        """
        self.schedule.step()
        self.tick_counter += 1

        # Genera fuego inicial en el primer tick
        if self.tick_counter == 2:
            self._generar_fuego_inicial()
        
        # Propaga el fuego a partir del tick 3
        if self.alarma_activa:
            self._propagar_fuego()

        # Genera un derrumbe aleatorio cada 8 ticks
        if self.tick_counter % 8 == 0:
            self._generar_derrumbe()
        
        # Recolecta datos del modelo
        self.datacollector.collect(self)

# === VISUALIZACIÓN DE LOS AGENTES ===
def agent_portrayal(agent):
    """
    Define cómo se visualiza cada tipo de agente en la grilla.
    """
    portrayal = {"Shape": "rect", "Filled": "true", "w": 1, "h": 1, "Layer": 1}

    if isinstance(agent, ShoppingCell):
        color_map = {
            '#': "saddlebrown",  # Muro
            '.': "white",        # Pasillo
            'F': "red",          # Fuego
            'D': "black",        # Derrumbe
            'S': "green",        # Salida
            'L': "blue",         # Local comercial
            ' ': "white"
        }
        portrayal["Color"] = color_map.get(agent.cell_type, "gray")
        portrayal["Layer"] = 0

    elif isinstance(agent, Brigadista):
        portrayal["Shape"] = "circle"
        portrayal["r"]     = 0.8
        portrayal["Color"] = "orange"  # Color para brigadistas
        portrayal["Layer"] = 2

    elif isinstance(agent, Evacuante):
        # Los evacuantes se dibujan como círculos
        portrayal["Shape"] = "circle"
        portrayal["r"]     = 0.5
        portrayal["Color"] = "purple"
        if agent.state == Evacuante.MUERTO:
            portrayal["Color"] = "gray"
        elif agent.state == Evacuante.EVACUATED:
             portrayal["Color"] = "yellow"
        portrayal["Layer"] = 1

    return portrayal

# === ELEMENTO DE TEXTO PARA INDICADORES DE KPI ===
class KPIElement(TextElement):
    def render(self, model):
        evacuados = model.datacollector.get_model_vars_dataframe()["Evacuados"].iloc[-1] if model.tick_counter > 0 else 0
        muertos   = model.datacollector.get_model_vars_dataframe()["Muertos"].iloc[-1] if model.tick_counter > 0 else 0
        vivos     = model.datacollector.get_model_vars_dataframe()["Vivos"].iloc[-1] if model.tick_counter > 0 else model.num_users
        tick      = model.tick_counter
        return (
            f"<b>Indicadores de la simulación:</b><br>"
            f"Tick actual: {tick}<br>"
            f"Civiles evacuados: {evacuados}<br>"
            f"Civiles muertos: {muertos}<br>"
            f"Civiles vivos dentro: {vivos}<br>"
            f"Tiempo total de evacuación: {str(tick*2) + ' seg.' if vivos == 0 else 'En curso'}<br>"
        )


# === CONFIGURAR Y LANZAR EL SERVIDOR MESA ===
canvas = CanvasGrid(agent_portrayal, 49, 40, canvas_width, canvas_height)
kpi_element = KPIElement()

server = ModularServer(
    ShoppingModel,            # Modelo
    [canvas, kpi_element],    # Elementos visuales
    "Simulación Centro Comercial (Mesa)",  # Título
    {}                        # Parámetros del modelo
)

server.port = 8521
server.launch()