from mesa import Model, Agent
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer

class ShoppingCenterCell(Agent):
    def __init__(self, unique_id, model, cell_type):
        super().__init__(unique_id, model)
        self.type = cell_type
    
    def step(self):
        pass

class Person(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
    
    def step(self):
        possible_steps = self.model.grid.get_neighborhood(
            self.pos,
            moore=True,
            include_center=False
        )
        new_position = self.random.choice(possible_steps)
        self.model.grid.move_agent(self, new_position)

class ShoppingCenterModel(Model):
    def __init__(self, width=20, height=20):
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        
        # Mapa del centro comercial
        map_2d = [
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
        
        # Crear celdas
        for y, row in enumerate(map_2d):
            for x, cell in enumerate(row):
                uid = x * 100 + y  # ID único
                cell_agent = ShoppingCenterCell(uid, self, cell)
                self.grid.place_agent(cell_agent, (x, y))
                self.schedule.add(cell_agent)
        
        # Añadir personas
        for i in range(10):
            person = Person(i + 1000, self)
            self.grid.place_agent(person, (1, 1))
            self.schedule.add(person)
    
    def step(self):
        self.schedule.step()

def agent_portrayal(agent):
    portrayal = {"Shape": "rect", "Filled": "true", "Layer": 0, "w": 1, "h": 1}
    
    if isinstance(agent, ShoppingCenterCell):
        colors = {
            '#': "brown",   # Pared
            '.': "white",   # Pasillo
            'F': "red",     # Fuego
            'D': "black",   # Derrumbe
            'S': "green",   # Salida
            'L': "blue"     # Local
        }
        portrayal["Color"] = colors.get(agent.type, "white")
    elif isinstance(agent, Person):
        portrayal["Shape"] = "circle"
        portrayal["Color"] = "purple"
        portrayal["r"] = 0.5
    
    return portrayal

grid = CanvasGrid(agent_portrayal, 20, 20, 500, 500)
server = ModularServer(
    ShoppingCenterModel,
    [grid],
    "entorno, mapa",     
    {"width": 20, "height": 20}
)
server.port = 8521
server.launch()