"""Turn-by-turn drone simulation engine."""

from typing import (
    Dict, FrozenSet, List, NamedTuple, Optional, Set, Tuple,
)

from fly_in.drone import Drone
from fly_in.parser import Connection, Map, Zone
from fly_in.pathfinder import PathFinder


class DroneSnapshot(NamedTuple):
    """Immutable snapshot of a single drone's state at a turn."""

    drone_id: int
    zone: Optional[str]
    in_flight: bool
    flight_from: str
    flight_to: str
    delivered: bool


class Simulator:
    """Turn-by-turn drone simulation engine.

    Manages drone movement through the zone network, enforcing
    capacity constraints and movement rules at each turn.

    The simulation proceeds in two phases per turn:
    1. Forced landings: drones in flight MUST arrive at their
       restricted-zone destination.
    2. Voluntary moves: remaining drones try to advance along
       their path, prioritized by proximity to the goal.
    """

    UNLIMITED_CAPACITY: int = 999999
    MAX_TURNS: int = 10000

    def __init__(self, map_obj: Map) -> None:
        """Initialize the simulator with a parsed map.

        Args:
            map_obj: Parsed map with zones, connections, drone count.
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
        """Get the canonical connection name as defined in the map.

        Args:
            z1: First zone name.
            z2: Second zone name.

        Returns:
            Connection name in 'zone1-zone2' format.
        """
        key = frozenset({z1, z2})
        conn = self._conn_map.get(key)
        if conn:
            return f"{conn.zone1}-{conn.zone2}"
        return f"{z1}-{z2}"

    def _zone_capacity(self, zone: Zone) -> int:
        """Get the effective capacity of a zone.

        Args:
            zone: The zone object.

        Returns:
            Maximum drones allowed, or UNLIMITED for start/end.
        """
        if zone.max_drones == -1:
            return self.UNLIMITED_CAPACITY
        return zone.max_drones

    def _assign_paths(self) -> None:
        """Find paths and assign them to drones.

        Uses round-robin assignment across discovered paths
        that have similar cost to the shortest path.
        """
        finder = PathFinder(self.map)
        paths = finder.find_paths()

        if not paths:
            raise RuntimeError("No path found from start to end!")

        best_cost = finder.path_cost(paths[0])

        # Keep paths within 2x the best cost
        good_paths = [
            p for p in paths
            if finder.path_cost(p) <= best_cost * 2.0
        ]
        if not good_paths:
            good_paths = [paths[0]]

        # Assign drones round-robin
        for i in range(self.map.nb_drones):
            path = good_paths[i % len(good_paths)]
            drone = Drone(i + 1, list(path))
            # Edge case: start == end
            if len(path) <= 1:
                drone.delivered = True
            self.drones.append(drone)

    def run(self) -> int:
        """Run the full simulation.

        Returns:
            Total number of turns to deliver all drones.
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
                    f"aborting."
                )
                break

        print(f"\nSimulation complete: {self.turn} turns.")
        return self.turn

    def record(self) -> List[List[DroneSnapshot]]:
        """Pre-compute all turns and return state snapshots.

        Returns:
            List of snapshots, index 0 is the initial state.
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
                    f"aborting."
                )
                break

        print(f"\nSimulation complete: {self.turn} turns.")
        return snapshots

    def _capture_snapshot(self) -> List[DroneSnapshot]:
        """Capture the current state of every drone.

        Returns:
            List of DroneSnapshot for each drone.
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
        """Execute one simulation turn.

        Phase 1: Forced landings for in-flight drones.
        Phase 2: Voluntary moves for grounded drones.

        Returns:
            List of (drone, destination_string) pairs.
        """
        moves: List[Tuple[Drone, str]] = []
        landed_ids: Set[int] = set()

        # --- Initialize capacity tracking ---

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

        # --- Phase 1: Forced landings ---

        for drone in self.drones:
            if not drone.in_flight:
                continue

            dest = drone.flight_to
            conn_key = frozenset(
                {drone.flight_from, drone.flight_to}
            )

            # Land the drone
            drone.path_index += 1
            drone.in_flight = False
            landed_ids.add(drone.id)

            # Update capacities
            conn_avail[conn_key] += 1
            zone_avail[dest] -= 1

            if dest == self.map.end_zone:
                drone.delivered = True

            moves.append((drone, dest))

        # --- Phase 2: Voluntary moves ---

        movable = [
            d for d in self.drones
            if not d.delivered
            and not d.in_flight
            and d.id not in landed_ids
            and d.path_index < len(d.path) - 1
        ]
        # Drones closer to goal move first
        movable.sort(key=lambda d: d.steps_remaining)

        for drone in movable:
            curr = drone.current_zone
            if curr is None:
                continue

            next_z = drone.path[drone.path_index + 1]
            zone_obj = self.map.zones[next_z]
            conn_key = frozenset({curr, next_z})

            # Check connection capacity
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
        """Try to move a drone to a normal or priority zone.

        Args:
            drone: The drone attempting to move.
            curr: Current zone name.
            next_z: Destination zone name.
            conn_key: Connection key (frozenset of zone names).
            zone_avail: Mutable zone availability tracker.
            conn_avail: Mutable connection availability tracker.
            moves: Mutable list of moves to append to.
        """
        if zone_avail.get(next_z, 0) <= 0:
            return

        # Execute move
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
        """Try to start a 2-turn flight toward a restricted zone.

        The drone enters the connection this turn and MUST arrive
        next turn. We reserve destination capacity to prevent
        deadlocks.

        Args:
            drone: The drone attempting to fly.
            curr: Current zone name.
            next_z: Destination restricted zone name.
            conn_key: Connection key (frozenset of zone names).
            zone_avail: Mutable zone availability tracker.
            conn_avail: Mutable connection availability tracker.
            moves: Mutable list of moves to append to.
        """
        # Reserve destination capacity for next turn's landing
        if zone_avail.get(next_z, 0) <= 0:
            return

        # Execute flight
        zone_avail[curr] += 1
        zone_avail[next_z] -= 1
        conn_avail[conn_key] -= 1

        drone.in_flight = True
        drone.flight_from = curr
        drone.flight_to = next_z

        conn_name = self._get_connection_name(curr, next_z)
        moves.append((drone, conn_name))
