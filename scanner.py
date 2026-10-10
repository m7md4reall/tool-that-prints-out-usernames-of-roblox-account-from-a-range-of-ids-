
import csv
import os
import time
from pathlib import Path

import requests

START_ID = int(os.getenv("START_ID", "261167905"))
END_ID = int(os.getenv("END_ID", "261963978"))
BATCH_SIZE = 100
PAUSE_SECONDS = 0.8
OUT = Path("results")
OUT.mkdir(exist_ok=True)

CSV_FILE = OUT / "all_users.csv"
TXT_FILE = OUT / "results.txt"
CHECKPOINT = OUT / "checkpoint.txt"

URL = "https://users.roblox.com/v1/users"
session = requests.Session()
session.headers.update({
    "User-Agent": "RobloxAccountRecoveryResearch/1.0",
    "Content-Type": "application/json",
})

def get_batch(ids):
    for attempt in range(8):
        try:
            response = session.post(
                URL,
                json={
                    "userIds": ids,
                    "excludeBannedUsers": False,
                },
                timeout=30,
            )

            if response.status_code == 429:
                delay = min(30 * (2 ** attempt), 300)
                print(f"Rate limited. Waiting {delay}s.")
                time.sleep(delay)
                continue

            if response.status_code >= 500:
                time.sleep(min(5 * (2 ** attempt), 120))
                continue

            response.raise_for_status()
            return response.json().get("data", [])

        except requests.RequestException as exc:
            if attempt == 7:
                raise RuntimeError(
                    f"Could not retrieve batch starting at {ids[0]}"
                ) from exc
            time.sleep(min(5 * (2 ** attempt), 120))

    raise RuntimeError("Retries exhausted; scan stopped safely.")

def main():
    total = END_ID - START_ID + 1
    print(f"Scanning {total:,} possible IDs.")
    print(f"Range: {START_ID:,}–{END_ID:,}")

    # Save each successful batch immediately.
    # If the run stops, previously saved rows remain available.
    mode = "a" if CSV_FILE.exists() else "w"

    with CSV_FILE.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if mode == "w":
            writer.writerow(["user_id", "username"])

        for offset in range(0, total, BATCH_SIZE):
            ids = list(range(
                START_ID + offset,
                min(START_ID + offset + BATCH_SIZE, END_ID + 1),
            ))

            users = get_batch(ids)

            for user in sorted(users, key=lambda u: u["id"]):
                writer.writerow([user["id"], user["name"]])

            f.flush()

            next_id = ids[-1] + 1
            CHECKPOINT.write_text(
                f"Last completed batch ends at {ids[-1]}\n"
                f"Next ID: {next_id}\n",
                encoding="utf-8",
            )

            done = min(offset + len(ids), total)
            if offset % (BATCH_SIZE * 25) == 0:
                print(f"Progress: {done:,}/{total:,} IDs processed")

            time.sleep(PAUSE_SECONDS)

    # Read every recovered username and group the results.
    users = []
    with CSV_FILE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            users.append((int(row["user_id"]), row["username"]))

    users.sort()
    mohamed = [
        u for u in users if "mohamed" in u[1].lower()
    ]
    mohamad = [
        u for u in users
        if "mohamad" in u[1].lower()
        and "mohamed" not in u[1].lower()
    ]

    # Write a readable report with matches first.
    with TXT_FILE.open("w", encoding="utf-8") as f:
        f.write(f"MOHAMED MATCHES: {len(mohamed)}\n")
        for uid, name in mohamed:
            f.write(f"{uid}\t{name}\n")

        f.write(f"\nMOHAMAD MATCHES: {len(mohamad)}\n")
        for uid, name in mohamad:
            f.write(f"{uid}\t{name}\n")

        f.write(f"\nTOTAL ACCOUNTS RETURNED: {len(users)}\n")
        f.write("\nALL USERNAMES (ID ORDER)\n")
        for uid, name in users:
            f.write(f"{uid}\t{name}\n")

    print("\n" + "=" * 45)
    print(f"MOHAMED MATCHES: {len(mohamed)}")
    for uid, name in mohamed:
        print(f"{uid}\t{name}")

    print(f"\nMOHAMAD MATCHES: {len(mohamad)}")
    for uid, name in mohamad:
        print(f"{uid}\t{name}")

    print(f"\nTOTAL ACCOUNTS RETURNED: {len(users)}")
    print(f"Full report: {TXT_FILE}")
    print(f"CSV file: {CSV_FILE}")

if __name__ == "__main__":
    main()
