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
        print(f"\033[91mParse error: {e}\033[0m")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\033[91mError: File '{args.map_file}' not found.\033[0m")
        sys.exit(1)
    except (PermissionError, IsADirectoryError) as e:
        print(f"\033[91mError: Cannot read '{args.map_file}': {e}\033[0m")
        sys.exit(1)

    try:
        simulator = Simulator(map_obj)
        snapshots = simulator.record()
    except RuntimeError as e:
        print(f"\033[91mSimulation error: {e}\033[0m")
        sys.exit(1)

    visualizer = Visualizer(map_obj, snapshots)
    visualizer.run()


if __name__ == "__main__":
    main()
