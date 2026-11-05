"""Enforce SurfaceFeeding behavior on git-koi snapshot."""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    runner_temp = os.environ.get("RUNNER_TEMP", "/tmp")
    snapshot_path = Path(runner_temp) / "koi-snapshot.json"
    if not snapshot_path.exists():
        print(f"Snapshot not found at {snapshot_path}")
        return

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    history = data.get("contribution_history")
    if not history or not history.get("days"):
        return

    days = history["days"]
    obs_str = history["observed_on"]
    obs = datetime.strptime(obs_str, "%Y-%m-%d").date()
    monday = obs - timedelta(days=obs.weekday())

    # Ensure last day has at least 1 contribution so quiet_day_count < 14
    if days[-1]["contribution_count"] == 0:
        days[-1]["contribution_count"] = 1

    # Zero out days in the current Monday-Sunday week before observed_on
    # so is_first_contribution_of_week is True (triggering SurfaceFeeding)
    for d in days[:-1]:
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        if monday <= dt < obs:
            d["contribution_count"] = 0

    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Re-render with git-koi
    subprocess.run(
        ["git-koi", "render", str(snapshot_path), "--output-dir", "koi", "--body", "white"],
        check=True,
    )
    print("Re-rendered koi with surface feeding behavior.")


if __name__ == "__main__":
    main()
