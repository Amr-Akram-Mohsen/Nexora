# scripts/maintenance/run_content_item_matching.py
import argparse
import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )
)

from dotenv import load_dotenv
load_dotenv()

from main import app
from app.application.linking.content_item_matching import run_content_item_matching


def main():
    parser = argparse.ArgumentParser(
        description="Run Content ↔ Item cross-domain matching and linking workflow."
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=None,
        help="Only check contents ingested or items created within this many days. If omitted, check all.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=4.0,
        help="Minimum matching score threshold to establish a link (default: 4.0).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for loading Content records (default: 100).",
    )

    args = parser.parse_args()

    print("\n==================================================")
    print("  Nexora Content <-> Item Matching & Linking Runner  ")
    print("==================================================")
    print(f"Parameters: since-days={args.since_days}, threshold={args.threshold}, batch-size={args.batch_size}")
    print("--------------------------------------------------")

    with app.app_context():
        import logging
        # Ensure log output is visible
        logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        
        summary = run_content_item_matching(
            batch_size=args.batch_size,
            score_threshold=args.threshold,
            since_days=args.since_days,
        )

        print("\n--------------------------------------------------")
        print("Run Summary:")
        print(f" - Processed Contents: {summary['processed_contents']}")
        print(f" - Processed Items:    {summary['processed_items']}")
        print(f" - Links Created:      {summary['links_created']}")
        print("==================================================\n")


if __name__ == "__main__":
    main()
