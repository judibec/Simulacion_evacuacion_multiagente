# blackboard.py

class Blackboard:
    """
    Implementación del patrón Blackboard para comunicación entre brigadistas.
    Permite registrar y consultar posiciones de todos los brigadistas.
    """
    def __init__(self):
        self.positions = {}  # {brigadista_id: (x, y)}

    def write_position(self, brigadista_id, pos):
        """
        Guarda la posición actual de un brigadista.
        """
        self.positions[brigadista_id] = pos

    def read_position(self, brigadista_id):
        """
        Consulta la posición de un brigadista específico.
        """
        return self.positions.get(brigadista_id)

    def read_all_positions(self):
        """
        Devuelve las posiciones de todos los brigadistas.
        """
        return dict(self.positions)
