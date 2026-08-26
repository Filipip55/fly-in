*This project has been created as part of the 42 curriculum by icoman.*

# Fly-In

Fly-In is a turn-based simulation of multiple drones navigating a network of zones from a starting hub to an ending hub. The program computes valid paths, coordinates drone movements to respect zone and connection capacities, and renders the result in a 2D graphical visualizer.

---

## Description

The goal of the project is to route a fleet of drones through a graph while adhering to movement rules and capacity limits:
- Start all drones at `start_hub` and deliver them to `end_hub`.
- Zones have a maximum occupancy (`max_drones`, default 1; unlimited for start/end).
- Connections have a maximum throughput (`max_link_capacity`, default 1).
- Zone types dictate movement cost:
  - `normal`: standard 1-turn move.
  - `priority`: 1-turn move, favored during pathfinding.
  - `restricted`: 2-turn move (the drone spends 1 turn in flight across the connection and lands on the next turn).
  - `blocked`: impassable zone.

The graph and routing logic are written from scratch without external graph libraries.

---

## Instructions

### Requirements
- Python 3.10 or higher
- `uv` package manager (or standard `pip`)

### Setup
Install dependencies with:
```bash
make install
```

### Running the simulation
To run the simulation with a map file:
```bash
make run MAP=maps/easy/01_linear_path.txt
```
Or directly with Python/uv:
```bash
uv run python -m fly_in maps/easy/01_linear_path.txt
```

### Debugging
Run the program with `pdb`:
```bash
make debug MAP=maps/medium/01_dead_end_trap.txt
```

### Code quality
Run flake8 linter and mypy type checks in strict mode:
```bash
make lint
```

---

## Algorithm and Implementation Strategy

### 1. Custom Graph Representation
The network is stored as an adjacency list using built-in Python dictionaries:
- `Dict[str, List[Tuple[str, float]]]`, mapping each zone name to a list of `(neighbor_name, edge_weight)`.
- Edge weights are assigned based on destination zone properties:
  - `normal` -> 1.0
  - `priority` -> 0.9 (preferred by the shortest path algorithm)
  - `restricted` -> 2.0 (reflects the 2-turn travel cost)
  - `blocked` -> excluded from the graph

### 2. Pathfinding and Alternative Routes
1. **Dijkstra's Algorithm**: We use Dijkstra with a min-heap (`heapq`) to compute the lowest-cost path between `start_hub` and `end_hub`.
2. **Alternative Paths**: To route multiple drones simultaneously without bottlenecks, we discover alternative routes by temporarily excluding each intermediate node from the primary path and re-running Dijkstra.
3. **Path Assignment**: Discovered paths within twice the best cost are kept. Paths are assigned to drones in round-robin order `drone i → path[i % len(paths)]`.

### 3. Simulation Loop and Conflict Resolution
Each turn executes in two steps:
1. **Landings**: Drones currently in flight toward a restricted zone must land first. This frees connection capacity and occupies the destination zone.
2. **Moves**: Remaining drones ready to move are sorted by remaining distance to goal (`steps_remaining`), giving priority to drones closest to the destination.
   - For normal/priority zones: moves occur immediately if both the connection and destination zone have free capacity.
   - For restricted zones: the drone enters the connection (`in_flight = True`), consumes link capacity, and reserves a slot in the destination zone for the next turn.

---

## Visual Representation

The visualization is implemented using Pygame:
- **Coordinate Scaling**: Zone coordinates are automatically scaled and centered to fit within a 1280x720 window while preserving aspect ratio.
- **Metadata Colors**: Zones use colors specified in the map file (e.g., `[color=green]`, `[color=blue]`) or default to pastel colors.
- **Smooth Animation**: The simulation pre-records state snapshots and interpolates drone positions at 60 FPS between turns.
- **Occupancy Counts**: Zones with multiple stationary drones display the numeric count inside the zone marker.
- **HUD**: Displays the current turn number or completion status.

---

## Example Input and Output

###  Simple_fork.txt
```txt
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

### Output
```txt
Turn 1: D1-junction D2-junction
Turn 2: D1-path_a D2-path_b D3-junction D4-junction
Turn 3: D1-goal D2-goal D3-path_a D4-path_b
Turn 4: D3-goal D4-goal

Simulation complete: 4 turns.
```

---

## Resources and AI Usage

### References
- Dijkstra's Algorithm - Computerphile: https://www.youtube.com/watch?v=bZkzH5x0SKU&list=WL&index=11&pp=iAQBsAgC
- Graph Data Structure and Algorithms: https://www.youtube.com/watch?v=t5B064eGMMU&list=WL&index=9&pp=iAQBsAgC
- Graph Theory Introduction: https://www.youtube.com/watch?v=LFKZLXVO-Dg&pp=ygUMZ3JhcGggdGhlb3J5

### AI Usage
Artificial intelligence tools were used during development for:
1. Drafting regular expressions used in `fly_in/parser.py` to parse map files, coordinates, and optional metadata.
2. Outlining the structure of the `fly_in/visualizer.py` script.