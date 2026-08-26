import argparse
import sys

from fly_in.parser import ParseError, parse_map
from fly_in.simulator import Simulator
from fly_in.visualizer import Visualizer


def main() -> None:
    """Esegue il parsing di un file mappa e avvia la simulazione."""
    try:
        arg_parser = argparse.ArgumentParser(
            description="Fly-in: Drone pathfinding simulation"
        )
        arg_parser.add_argument("map_file", help="Path to the map file")
        args = arg_parser.parse_args()

        map_obj = parse_map(args.map_file)

        simulator = Simulator(map_obj)
        snapshots = simulator.record()
        visualizer = Visualizer(map_obj, snapshots)
        visualizer.run()

    except argparse.ArgumentError as e:
        print(f"\033[91mMissing argument: {e}\033[0m")
        sys.exit(1)
    except ParseError as e:
        print(f"\033[91mParse error: {e}\033[0m")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\033[91mError: File '{args.map_file}' not found.\033[0m")
        sys.exit(1)
    except (PermissionError, IsADirectoryError) as e:
        print(f"\033[91mError: Cannot read '{args.map_file}': {e}\033[0m")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\033[91mSimulation error: {e}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
