import argparse
import sys
from parser import parse_map, ParseError


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a map file.")
    parser.add_argument("map_file", help="Path to the map.txt file")
    args = parser.parse_args()

    try:
        parse_map(args.map_file)
        print("MAP OK")
    except ParseError as e:
        print(str(e))
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File '{args.map_file}' not found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
