"""Usage: python checker.py PACK_FOLDER. Outputs are written in the working directory."""
import argparse
from pathlib import Path
import sys
from ridgeline.io import atomic_write, csv_text, load_pack


def main():
    parser = argparse.ArgumentParser(description='Offline deterministic weather-network checker')
    parser.add_argument('pack_folder', type=Path)
    args = parser.parse_args()
    try:
        pack = load_pack(args.pack_folder)
        atomic_write(Path.cwd() / 'flags.csv', csv_text([]))
        print(f'Loaded {len(pack.weather)} stations; flags.csv written.')
        return 0
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
