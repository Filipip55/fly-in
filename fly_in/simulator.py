from typing import (
    Dict, FrozenSet, List, NamedTuple, Optional, Set, Tuple,
)

from fly_in.drone import Drone
from fly_in.parser import Connection, Map, Zone
from fly_in.pathfinder import PathFinder


class DroneSnapshot(NamedTuple):
    """Istantanea immutabile dello stato di un singolo drone in un turno."""

    drone_id: int
    zone: Optional[str]
    in_flight: bool
    flight_from: str
    flight_to: str
    delivered: bool


class Simulator:
    """Motore di simulazione dei droni turno per turno.

    Gestisce il movimento dei droni attraverso la rete di zone, applicando
    i vincoli di capacità e le regole di movimento a ogni turno.

    La simulazione procede in due fasi per turno:
    1. Atterraggi forzati: i droni in volo DEVONO arrivare alla loro
       destinazione in zona restricted.
    2. Movimenti volontari: i droni rimanenti cercano di avanzare lungo
       il loro percorso, con priorità in base alla vicinanza all'obiettivo.
    """

    UNLIMITED_CAPACITY: int = 999999
    MAX_TURNS: int = 10000

    def __init__(self, map_obj: Map) -> None:
        """Inizializza il simulatore con una mappa analizzata.

        Args:
            map_obj: Mappa analizzata con zone, connessioni, conteggio droni.
        """
        self.map: Map = map_obj
        self.drones: List[Drone] = []
        self.turn: int = 0

        # Connection lookup by zone-pair
        self._conn_map: Dict[FrozenSet[str], Connection] = {}
        for conn in map_obj.connections:
            key = frozenset({conn.zone1, conn.zone2})
            self._conn_map[key] = conn

    def _get_connection_name(self, z1: str, z2: str) -> str:
        """Ottiene il nome canonico del collegamento definito nella mappa.

        Args:
            z1: Nome della prima zona.
            z2: Nome della seconda zona.

        Returns:
            Nome del collegamento nel formato 'zona1-zona2'.
        """
        key = frozenset({z1, z2})
        conn = self._conn_map.get(key)
        if conn:
            return f"{conn.zone1}-{conn.zone2}"
        return f"{z1}-{z2}"

    def _zone_capacity(self, zone: Zone) -> int:
        """Ottiene la capacità effettiva di una zona.

        Args:
            zone: L'oggetto zona.

        Returns:
            Numero massimo di droni consentiti, o UNLIMITED per start/end.
        """
        if zone.max_drones == -1:
            return self.UNLIMITED_CAPACITY
        return zone.max_drones

    def _assign_paths(self) -> None:
        """Trova i percorsi e li assegna ai droni.

        Utilizza un'assegnazione round-robin tra i percorsi individuati
        che hanno un costo simile al percorso più breve.
        """
        finder = PathFinder(self.map)
        paths = finder.find_paths()

        if not paths:
            raise RuntimeError("No path found from start to end!")

        best_cost = finder.path_cost(paths[0])

        good_paths = [
            p for p in paths
            if finder.path_cost(p) <= best_cost * 2.0
        ]
        if not good_paths:
            good_paths = [paths[0]]

        for i in range(self.map.nb_drones):
            path = good_paths[i % len(good_paths)]
            drone = Drone(i + 1, list(path))
            # Edge case: start == end
            if len(path) <= 1:
                drone.delivered = True
            self.drones.append(drone)

    def run(self) -> int:
        """Esegue la simulazione completa.

        Returns:
            Numero totale di turni per consegnare tutti i droni.
        """
        self._assign_paths()

        while not all(d.delivered for d in self.drones):
            self.turn += 1
            moves = self._execute_turn()

            if moves:
                parts = [
                    f"D{drone.id}-{dest}" for drone, dest in moves
                ]
                print(f"Turn {self.turn}: {' '.join(parts)}")
            else:
                print(f"Turn {self.turn}: (no movements)")

            if self.turn > self.MAX_TURNS:
                print(
                    f"ERROR: Exceeded {self.MAX_TURNS} turns, "
                    f"it's too much for me!."
                )
                break

        print(f"\nSimulation complete: {self.turn} turns.")
        return self.turn

    def record(self) -> List[List[DroneSnapshot]]:
        """Precalcola tutti i turni e restituisce le istantanee di stato.

        Returns:
            Lista di istantanee, l'indice 0 è lo stato iniziale.
        """
        self._assign_paths()
        snapshots: List[List[DroneSnapshot]] = [
            self._capture_snapshot(),
        ]

        while not all(d.delivered for d in self.drones):
            self.turn += 1
            moves = self._execute_turn()

            if moves:
                parts = [
                    f"D{drone.id}-{dest}" for drone, dest in moves
                ]
                print(f"Turn {self.turn}: {' '.join(parts)}")
            else:
                print(f"Turn {self.turn}: (no movements)")

            snapshots.append(self._capture_snapshot())
            if self.turn > self.MAX_TURNS:
                print(
                    f"ERROR: Exceeded {self.MAX_TURNS} turns, "
                    f"it's too much for me!."
                )
                break

        print(f"\nSimulation complete: {self.turn} turns.")
        return snapshots

    def _capture_snapshot(self) -> List[DroneSnapshot]:
        """Cattura lo stato corrente di ogni drone.

        Returns:
            Lista di DroneSnapshot per ciascun drone.
        """
        result: List[DroneSnapshot] = []
        for d in self.drones:
            if d.in_flight:
                zone: Optional[str] = None
            else:
                zone = d.path[d.path_index]
            result.append(DroneSnapshot(
                drone_id=d.id,
                zone=zone,
                in_flight=d.in_flight,
                flight_from=d.flight_from,
                flight_to=d.flight_to,
                delivered=d.delivered,
            ))
        return result

    def _execute_turn(self) -> List[Tuple[Drone, str]]:
        """Esegue un turno di simulazione.

        Fase 1: Atterraggi forzati per i droni in volo.
        Fase 2: Movimenti volontari per i droni a terra.

        Returns:
            Lista di coppie (drone, stringa_destinazione).
        """
        moves: List[Tuple[Drone, str]] = []
        landed_ids: Set[int] = set()

        # capacity tracking for zones and connections
        zone_avail: Dict[str, int] = {}
        for name, zone in self.map.zones.items():
            current = sum(
                1 for d in self.drones
                if d.current_zone == name
            )
            zone_avail[name] = self._zone_capacity(zone) - current

        conn_avail: Dict[FrozenSet[str], int] = {}
        for conn in self.map.connections:
            key = frozenset({conn.zone1, conn.zone2})
            in_flight = sum(
                1 for d in self.drones
                if d.in_flight
                and frozenset({d.flight_from, d.flight_to}) == key
            )
            conn_avail[key] = conn.max_link_capacity - in_flight

        # Fase 1
        for drone in self.drones:
            if not drone.in_flight:
                continue

            dest = drone.flight_to
            conn_key = frozenset(
                {drone.flight_from, drone.flight_to}
            )

            # atterraggio
            drone.path_index += 1
            drone.in_flight = False
            landed_ids.add(drone.id)

            # Update capacity
            conn_avail[conn_key] += 1
            zone_avail[dest] -= 1

            if dest == self.map.end_zone:
                drone.delivered = True

            moves.append((drone, dest))

        # Fase 2

        movable = [
            d for d in self.drones
            if not d.delivered
            and not d.in_flight
            and d.id not in landed_ids
            and d.path_index < len(d.path) - 1
        ]
        # Droni più vicini a end si muovono prima
        movable.sort(key=lambda d: d.steps_remaining)

        for drone in movable:
            curr = drone.current_zone
            if curr is None:
                continue

            next_z = drone.path[drone.path_index + 1]
            zone_obj = self.map.zones[next_z]
            conn_key = frozenset({curr, next_z})

            if conn_avail.get(conn_key, 0) <= 0:
                continue

            if zone_obj.zone_type == "restricted":
                self._try_restricted_move(
                    drone, curr, next_z, conn_key,
                    zone_avail, conn_avail, moves,
                )
            else:
                self._try_normal_move(
                    drone, curr, next_z, conn_key,
                    zone_avail, conn_avail, moves,
                )

        return moves

    def _try_normal_move(
        self,
        drone: Drone,
        curr: str,
        next_z: str,
        conn_key: FrozenSet[str],
        zone_avail: Dict[str, int],
        conn_avail: Dict[FrozenSet[str], int],
        moves: List[Tuple[Drone, str]],
    ) -> None:
        """Tenta di spostare un drone in una zona normal o priority.

        Args:
            drone: Il drone che tenta di muoversi.
            curr: Nome della zona corrente.
            next_z: Nome della zona di destinazione.
            conn_key: Chiave del collegamento (frozenset con nomi di zone).
            zone_avail: Traccia la disponibilità zone.
            conn_avail: Traccia la disponibilità collegamenti.
            moves: Lista di movimenti a cui aggiungere il nuovo spostamento.
        """
        if zone_avail.get(next_z, 0) <= 0:
            return

        zone_avail[curr] += 1
        zone_avail[next_z] -= 1
        conn_avail[conn_key] -= 1

        drone.path_index += 1
        if next_z == self.map.end_zone:
            drone.delivered = True

        moves.append((drone, next_z))

    def _try_restricted_move(
        self,
        drone: Drone,
        curr: str,
        next_z: str,
        conn_key: FrozenSet[str],
        zone_avail: Dict[str, int],
        conn_avail: Dict[FrozenSet[str], int],
        moves: List[Tuple[Drone, str]],
    ) -> None:
        """Tenta di avviare un volo di 2 turni verso una zona restricted.

        Il drone entra nel collegamento in questo turno e arriva
        al turno successivo. Riserviamo la capacità di destinazione per
        prevenire situazioni di deadlock.

        Args:
            drone: Il drone che tenta di volare.
            curr: Nome della zona corrente.
            next_z: Nome della zona restricted di destinazione.
            conn_key: Chiave del collegamento (frozenset di nomi di zona).
            zone_avail: Tracciatore disponibilità zone.
            conn_avail: Tracciatore disponibilità collegamenti.
            moves: Lista di movimenti a cui aggiungere il nuovo spostamento.
        """
        if zone_avail.get(next_z, 0) <= 0:
            return

        zone_avail[curr] += 1
        zone_avail[next_z] -= 1
        conn_avail[conn_key] -= 1

        drone.in_flight = True
        drone.flight_from = curr
        drone.flight_to = next_z

        conn_name = self._get_connection_name(curr, next_z)
        moves.append((drone, conn_name))
