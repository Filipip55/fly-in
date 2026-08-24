"""Fly-in: Main entry point for the drone simulation."""

import argparse
import sys

from fly_in.parser import ParseError, parse_map
from fly_in.simulator import Simulator
from fly_in.visualizer import Visualizer


def main() -> None:
    """Parse a map file and run the drone simulation."""
    arg_parser = argparse.ArgumentParser(
        description="Fly-in: Drone pathfinding simulation"
    )
    arg_parser.add_argument("map_file", help="Path to the map file")
    args = arg_parser.parse_args()

    try:
        map_obj = parse_map(args.map_file)
    except ParseError as e:
        print(f"Parse error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File '{args.map_file}' not found.")
        sys.exit(1)

    simulator = Simulator(map_obj)
    snapshots = simulator.record()

    visualizer = Visualizer(map_obj, snapshots)
    visualizer.run()


if __name__ == "__main__":
    main()
