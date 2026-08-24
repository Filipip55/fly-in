"""Drone entity for the fly-in simulation."""

from typing import List, Optional


class Drone:
    """A drone navigating through the zone network.

    Attributes:
        id: Unique drone identifier (1-indexed).
        path: Ordered list of zone names from start to end.
        path_index: Current position index in the path.
        in_flight: Whether the drone is on a connection
                   toward a restricted zone.
        flight_from: Source zone of the current flight.
        flight_to: Destination zone of the current flight.
        delivered: Whether the drone has reached the end zone.
    """

    def __init__(self, drone_id: int, path: List[str]) -> None:
        """Initialize a drone with its assigned path.

        Args:
            drone_id: Unique identifier for the drone.
            path: List of zone names representing the route.
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
        """Current zone, or None if in flight or delivered."""
        if self.in_flight or self.delivered:
            return None
        return self.path[self.path_index]

    @property
    def next_zone(self) -> Optional[str]:
        """Next zone in path, or None if at the end."""
        if self.path_index + 1 >= len(self.path):
            return None
        return self.path[self.path_index + 1]

    @property
    def steps_remaining(self) -> int:
        """Number of steps remaining to reach the end zone."""
        return len(self.path) - 1 - self.path_index
