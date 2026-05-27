import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.storage.database import DatabaseLogger
from datetime import datetime


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/traffic.db"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "data/reports/daily_report.txt"

    db = DatabaseLogger(db_path)

    events = db.query_events(limit=1000)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        f.write("=" * 60 + "\n")
        f.write(f"Vehicle Tracker Pro++ - Traffic Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"Total Events Logged: {len(events)}\n\n")

        f.write("Recent Events:\n")
        f.write("-" * 40 + "\n")
        event_types = {}
        for e in events[-50:]:
            eid, ts, etype, vid, details = e
            event_types[etype] = event_types.get(etype, 0) + 1
            f.write(f"  [{ts}] {etype} - Vehicle #{vid}\n")

        f.write("\nEvent Summary:\n")
        f.write("-" * 40 + "\n")
        for etype, count in sorted(event_types.items()):
            f.write(f"  {etype}: {count}\n")

    print(f"Report saved to: {output_path}")
    db.close()


if __name__ == "__main__":
    main()
