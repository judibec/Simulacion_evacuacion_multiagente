# === LIBRERÍAS DE MESA ===
from mesa import Agent, Model                          # Agente base y modelo
from mesa.space import MultiGrid                       # Espacio tipo grilla con múltiples agentes por celda
from mesa.time import SimultaneousActivation           # Activador para que todos los agentes actúen simultáneamente
from mesa.visualization.modules import CanvasGrid      # Visualización de la grilla en HTML
from mesa.visualization.ModularVisualization import ModularServer  # Servidor web para ejecutar la simulación

# === AGENTE MÓVIL: EVACUANTE ===
from .evacuante import Evacuante                       # Importamos el agente Evacuante definido en otro archivo

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
    def __init__(self, num_users=7, seed=None):
        super().__init__(seed=seed)              # Crea el generador aleatorio de Mesa
        self.num_users = num_users               # Número de evacuantes a crear
        self.tick_counter  = 0                   # Contador global de ticks
        self.alarma_activa = False               # Bandera de alarma (fuego activado)

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

        for i in range(min(self.num_users, len(empty_positions))):
            pos   = empty_positions[i]
            agent = Evacuante(f"U{i}", self)     # Crea un evacuante con ID único
            self.grid.place_agent(agent, pos)    # Lo ubica en la posición
            self.schedule.add(agent)             # Lo añade al scheduler

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

        if self.tick_counter == 2:
            self._generar_fuego_inicial()


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

    elif isinstance(agent, Evacuante):
        # Los evacuantes se dibujan como círculos morados
        portrayal["Shape"] = "circle"
        portrayal["r"]     = 0.5
        portrayal["Color"] = "purple"
        portrayal["Layer"] = 1

    return portrayal


# === CONFIGURAR Y LANZAR EL SERVIDOR MESA ===
canvas = CanvasGrid(agent_portrayal, 49, 40, canvas_width, canvas_height)

server = ModularServer(
    ShoppingModel,            # Modelo
    [canvas],                 # Elementos visuales
    "Simulación Centro Comercial (Mesa)",  # Título
    {}                        # Parámetros del modelo
)

server.port = 8521
server.launch()