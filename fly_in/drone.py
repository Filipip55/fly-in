from typing import List, Optional


class Drone:
    """Rappresenta un drone.

    Attributi:
        id: ID unico per ogni drone (indice).
        path: Lista di nomi di zone da start a end.
        path_index: Posizione corrente nel percorso.
        in_flight: True se il drone è in volo verso una
                   zona restricted.
        flight_from: Zona di partenza per lo spostamento corrente.
        flight_to: Zona di arrivo per lo spostamento corrente.
        delivered: True se il drone ha raggiunto end.
    """

    def __init__(self, drone_id: int, path: List[str]) -> None:
        """Inizializza un drone con il percorso assegnato.

        Args:
            drone_id: ID unico per ogni drone (indice).
            path: Lista dei nomi delle zone che rappresentano il percorso.
        """
        self.id: int = drone_id
        self.path: List[str] = path
        self.path_index: int = 0
        self.in_flight: bool = False
        self.flight_from: str = ""
        self.flight_to: str = ""
        self.delivered: bool = False

    @property
    def current_zone(self) -> Optional[str]:
        """Zona corrente, oppure None se in volo o consegnato."""
        if self.in_flight or self.delivered:
            return None
        return self.path[self.path_index]

    @property
    def next_zone(self) -> Optional[str]:
        """Prossima zona nel percorso, oppure None se alla fine."""
        if self.path_index + 1 >= len(self.path):
            return None
        return self.path[self.path_index + 1]

    @property
    def steps_remaining(self) -> int:
        """Numero di passi rimanenti per raggiungere la zona finale."""
        return len(self.path) - 1 - self.path_index
