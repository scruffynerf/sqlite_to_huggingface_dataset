#!/usr/bin/env python3
"""
sqlite_to_hf.py — Convert a SQLite table to a HuggingFace dataset and upload it.

Usage:
    python sqlite_to_hf.py <db_path> <table_name> <hf_repo_id> [options]

Examples:
    python sqlite_to_hf.py mydata.db users my-username/my-dataset
    python sqlite_to_hf.py mydata.db users my-username/my-dataset --private
    python sqlite_to_hf.py mydata.db users my-username/my-dataset --split train --token hf_xxx
    python sqlite_to_hf.py mydata.db users my-username/my-dataset --query "SELECT * FROM users WHERE active=1"
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert a SQLite table to a HuggingFace dataset and upload it.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("db_path", help="Path to the SQLite database file")
    parser.add_argument("table", help="Table name to export")
    parser.add_argument(
        "repo_id",
        help="HuggingFace repo ID to create/push to (e.g. username/dataset-name)",
    )
    parser.add_argument(
        "--split",
        default="train",
        help="Dataset split name (default: train)",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create the HuggingFace dataset as private",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="HuggingFace API token. Falls back to HF_TOKEN env var or cached login.",
    )
    parser.add_argument(
        "--query",
        default=None,
        help=(
            "Custom SQL query to run instead of SELECT * FROM <table>. "
            "The --table argument is still used for display/logging."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10_000,
        help="Number of rows to fetch per batch (default: 10000). Lower if you hit memory limits.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and preview the data without uploading anything.",
    )
    return parser.parse_args()


def check_imports():
    missing = []
    for pkg in ("datasets", "huggingface_hub"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[ERROR] Missing required packages: {', '.join(missing)}")
        print(f"        Install with:  pip install {' '.join(missing)}")
        sys.exit(1)


def load_sqlite_table_generator(db_path: str, table: str, query: str | None, batch_size: int):
    """Generator that yields rows from the table in batches."""
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"[ERROR] Database file not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # column-name access
    cursor = conn.cursor()

    # Validate table exists when not using a custom query
    if query is None:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if not cursor.fetchone():
            available = [
                r[0]
                for r in cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            print(f"[ERROR] Table '{table}' not found in {db_path}")
            print(f"        Available tables: {available or '(none)'}")
            conn.close()
            sys.exit(1)

    sql = query if query else f"SELECT * FROM [{table}]"
    print(f"[INFO] Running query: {sql[:120]}{'...' if len(sql) > 120 else ''}")

    total_rows = 0
    cursor.execute(sql)
    while True:
        batch = cursor.fetchmany(batch_size)
        if not batch:
            break
        for row in batch:
            yield dict(row)
            total_rows += 1
        print(f"[INFO] Processed {total_rows:,} rows...", end="\r")

    conn.close()
    print(f"\n[INFO] Total rows processed: {total_rows:,}")


def infer_and_print_schema_from_generator(generator):
    """Peek at the first row of a generator to infer and print schema."""
    try:
        first_row = next(generator)
    except StopIteration:
        print("[WARN] Table is empty — nothing to infer.")
        return None, None

    print(f"\n[INFO] Columns ({len(first_row)}):")
    for col, val in first_row.items():
        print(f"       {col!r:30s} → {type(val).__name__} (sample: {repr(val)[:60]})")
    print()

    # Create a new generator that includes the first row
    def new_generator():
        yield first_row
        yield from generator

    return new_generator(), first_row


def upload_to_huggingface(
    db_path: str,
    table: str,
    query: str | None,
    batch_size: int,
    repo_id: str,
    split: str,
    private: bool,
    token: str | None,
):
    from datasets import Dataset
    from huggingface_hub import HfApi

    print(f"[INFO] Building HuggingFace Dataset using generator...")
    
    # Use gen_kwargs to avoid pickling issues with closures
    dataset = Dataset.from_generator(
        load_sqlite_table_generator,
        gen_kwargs={
            "db_path": db_path,
            "table": table,
            "query": query,
            "batch_size": batch_size,
        }
    )

    print(f"[INFO] Dataset features: {dataset.features}")

    api = HfApi(token=token)

    # Create the repo if it doesn't exist yet
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=private,
            exist_ok=True,
        )
        visibility = "private" if private else "public"
        print(f"[INFO] Dataset repo ready: https://huggingface.co/datasets/{repo_id} ({visibility})")
    except Exception as e:
        print(f"[ERROR] Could not create repo '{repo_id}': {e}")
        sys.exit(1)

    # push_to_hub handles sharding automatically.

    print(f"[INFO] Pushing to Hub as split='{split}'...")
    dataset.push_to_hub(
        repo_id=repo_id,
        split=split,
        private=private,
        token=token,
    )

    print(f"\n[OK] Upload complete!")
    print(f"     View at: https://huggingface.co/datasets/{repo_id}")


def main():
    args = parse_args()
    check_imports()

    # Pre-check/Schema inference (consumes one item from a fresh generator)
    gen = load_sqlite_table_generator(args.db_path, args.table, args.query, args.batch_size)
    _, first_row = infer_and_print_schema_from_generator(gen)

    if first_row is None:
        print("[WARN] No rows found. Nothing to upload.")
        sys.exit(0)

    if args.dry_run:
        print("[DRY RUN] Skipping upload. First 3 rows:")
        # We need a fresh generator for the dry run to show the first row again
        gen_dry = load_sqlite_table_generator(args.db_path, args.table, args.query, args.batch_size)
        try:
            for _ in range(3):
                print(f"  {dict(next(gen_dry))}")
        except StopIteration:
            pass
        sys.exit(0)

    upload_to_huggingface(
        db_path=args.db_path,
        table=args.table,
        query=args.query,
        batch_size=args.batch_size,
        repo_id=args.repo_id,
        split=args.split,
        private=args.private,
        token=args.token,
    )


if __name__ == "__main__":
    main()
