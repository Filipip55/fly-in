"""Shortest-path finder using Dijkstra's algorithm."""

import heapq
from typing import Dict, List, Optional, Set, Tuple

from fly_in.parser import Map, Zone


class PathFinder:
    """Finds shortest paths using Dijkstra's algorithm.

    Edge weights reflect movement cost to the destination zone:
    - normal: 1.0 turn
    - priority: 0.9 (preferred, same real cost but favored)
    - restricted: 2.0 turns
    - blocked: excluded from the graph

    Alternative paths are discovered by temporarily excluding
    intermediate nodes from the shortest path.
    """

    def __init__(self, map_obj: Map) -> None:
        """Initialize the pathfinder with a parsed map.

        Args:
            map_obj: Parsed map with zones and connections.
        """
        self.map: Map = map_obj
        self.adj: Dict[str, List[Tuple[str, float]]] = (
            self._build_adjacency()
        )

    def _build_adjacency(
        self,
    ) -> Dict[str, List[Tuple[str, float]]]:
        """Build adjacency list from zones and connections.

        Returns:
            Dict mapping zone names to (neighbor, weight) pairs.
        """
        adj: Dict[str, List[Tuple[str, float]]] = {
            name: [] for name in self.map.zones
        }
        for conn in self.map.connections:
            z1_obj = self.map.zones[conn.zone1]
            z2_obj = self.map.zones[conn.zone2]

            w_to_z2 = self._zone_weight(z2_obj)
            w_to_z1 = self._zone_weight(z1_obj)

            if w_to_z2 is not None:
                adj[conn.zone1].append((conn.zone2, w_to_z2))
            if w_to_z1 is not None:
                adj[conn.zone2].append((conn.zone1, w_to_z1))

        return adj

    @staticmethod
    def _zone_weight(zone: Zone) -> Optional[float]:
        """Get the movement weight for entering a zone.

        Args:
            zone: The destination zone.

        Returns:
            The weight, or None if the zone is blocked.
        """
        if zone.zone_type == "blocked":
            return None
        if zone.zone_type == "restricted":
            return 2.0
        if zone.zone_type == "priority":
            return 0.9
        return 1.0

    def dijkstra(
        self,
        start: str,
        end: str,
        excluded: Optional[Set[str]] = None,
    ) -> Optional[List[str]]:
        """Find the shortest path using Dijkstra's algorithm.

        Args:
            start: Name of the starting zone.
            end: Name of the destination zone.
            excluded: Zone names to exclude from pathfinding.

        Returns:
            List of zone names forming the path, or None.
        """
        if excluded is None:
            excluded = set()
        if start in excluded or end in excluded:
            return None

        dist: Dict[str, float] = {start: 0.0}
        prev: Dict[str, Optional[str]] = {start: None}
        heap: List[Tuple[float, int, str]] = [(0.0, 0, start)]
        counter: int = 0

        while heap:
            d, _, u = heapq.heappop(heap)
            if u == end:
                break
            if d > dist.get(u, float("inf")):
                continue
            for neighbor, weight in self.adj.get(u, []):
                if neighbor in excluded:
                    continue
                new_dist = d + weight
                if new_dist < dist.get(neighbor, float("inf")):
                    dist[neighbor] = new_dist
                    prev[neighbor] = u
                    counter += 1
                    heapq.heappush(
                        heap, (new_dist, counter, neighbor)
                    )

        if end not in prev:
            return None

        # Reconstruct path
        path: List[str] = []
        node: Optional[str] = end
        while node is not None:
            path.append(node)
            node = prev.get(node)
        path.reverse()
        return path

    def find_paths(self, max_paths: int = 10) -> List[List[str]]:
        """Find multiple shortest paths from start to end.

        Discovers alternative routes by excluding each intermediate
        node of the shortest path and re-running Dijkstra.

        Args:
            max_paths: Maximum number of paths to find.

        Returns:
            List of paths sorted by cost.
        """
        start = self.map.start_zone
        end = self.map.end_zone
        if not start or not end:
            return []

        paths: List[List[str]] = []

        shortest = self.dijkstra(start, end)
        if shortest is None:
            return []
        paths.append(shortest)

        # Find alternatives by excluding intermediate nodes
        for node in shortest[1:-1]:
            alt = self.dijkstra(start, end, excluded={node})
            if alt is not None and alt not in paths:
                paths.append(alt)
            if len(paths) >= max_paths:
                break

        paths.sort(key=lambda p: self.path_cost(p))
        return paths[:max_paths]

    def path_cost(self, path: List[str]) -> float:
        """Calculate the total weighted cost of a path.

        Args:
            path: List of zone names.

        Returns:
            Sum of edge weights along the path.
        """
        cost: float = 0.0
        for zone_name in path[1:]:
            zone = self.map.zones[zone_name]
            w = self._zone_weight(zone)
            cost += w if w is not None else float("inf")
        return cost
