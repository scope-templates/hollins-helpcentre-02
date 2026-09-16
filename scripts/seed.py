"""Loads data/hollins.json into the database by hand.

The app does this on its own the first time it opens an empty database. This is for when you want
it over with before the first request, or you want to put a database back to how it started.

    python scripts/seed.py
    python scripts/seed.py --drop
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hollins.db import COLLECTIONS, connect, name, prepare, uri  # noqa: E402
from hollins.seed_load import load_seed  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Load the bundled history.")
    parser.add_argument(
        "--drop", action="store_true", help="empty the collections first and load again"
    )
    args = parser.parse_args(argv)

    database = prepare(connect())
    print(f"{uri()} -> {name()}")
    if args.drop:
        for collection in COLLECTIONS:
            database[collection].delete_many({})
        print("emptied " + ", ".join(COLLECTIONS))

    written = load_seed(database)
    for collection in COLLECTIONS:
        count = written.get(collection, 0)
        if count:
            print(f"{collection}: {count} in")
        else:
            print(f"{collection}: already had rows, left alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
