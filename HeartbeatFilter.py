import json, csv
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

# Standalone data_path helper (mimics data_loader)
def data_path(filename: str) -> Path:
    data_dir = Path(__file__).parent / "Data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / filename

json_filename = input("Enter JSON filename (in Data/): ").strip()
p = data_path(json_filename)
print(f"Full path: {p}")
print(f"Exists: {p.exists()}")
data = json.loads(p.read_text(encoding="utf-8"))
print(f"Full path: {p}")
print(f"Exists: {p.exists()}")
fmt = "%m/%d/%y %H:%M:%S"; tz_gmt = ZoneInfo("UTC"); tz_berlin = ZoneInfo("Europe/Berlin")
first_dt_utc = datetime.strptime(data[0]["dateTime"], fmt).replace(tzinfo=tz_gmt)
first_dt_berlin = first_dt_utc.astimezone(tz_berlin)
date_str = first_dt_berlin.strftime("%m/%d/%y")


start_hm = input("Enter start time (HH:MM): ")
end_hm = input("Enter end time (HH:MM): ")
only_bpm = input("Only export bpm column? (y/N): ").strip().lower() == 'y'
start_time = f"{date_str} {start_hm}:00"
end_time = f"{date_str} {end_hm}:59"
start_dt = datetime.strptime(start_time, fmt).replace(tzinfo=tz_berlin)
end_dt   = datetime.strptime(end_time, fmt).replace(tzinfo=tz_berlin)

filtered_datetimes = [
    (dt := datetime.strptime(r["dateTime"], fmt).replace(tzinfo=tz_gmt).astimezone(tz_berlin), r["value"]["bpm"])
    for r in data
    if start_dt <= (dt := datetime.strptime(r["dateTime"], fmt).replace(tzinfo=tz_gmt).astimezone(tz_berlin)) <= end_dt
]


from datetime import timedelta

if filtered_datetimes:
    base_dt = filtered_datetimes[0][0]
    rounded = {}
    for dt, bpm in filtered_datetimes:
        delta = dt - base_dt
        total_sec = int(delta.total_seconds())
        rem = total_sec % 5
        # round to nearest 5s (down if rem < 3, up if rem >= 3)
        if rem < 3:
            rounded_sec = total_sec - rem
        else:
            rounded_sec = total_sec - rem + 5
        if rounded_sec < 0:
            rounded_sec = 0
        rounded[rounded_sec] = bpm  # keep last bpm for duplicate times
    # Fill missing intervals with average
    all_secs = list(sorted(rounded.keys()))
    filled = {}
    for idx, sec in enumerate(all_secs):
        filled[sec] = rounded[sec]
        if idx < len(all_secs) - 1:
            next_sec = all_secs[idx + 1]
            gap = next_sec - sec
            if gap > 5:
                bpm1 = float(rounded[sec])
                bpm2 = float(rounded[next_sec])
                for missing_sec in range(sec + 5, next_sec, 5):
                    avg_bpm = round((bpm1 + bpm2) / 2)
                    filled[missing_sec] = int(avg_bpm)
    filtered_data = [
        {"dateTime": str(timedelta(seconds=s)).rjust(8, "0"), "bpm": filled[s]} for s in sorted(filled)
    ]
else:
    filtered_data = []

print(f"Filtered records: {len(filtered_data)}")
out_path = data_path(f"{Path(p).stem}_filtered.tsv")
if only_bpm:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        for row in filtered_data:
            f.write(f"{row['bpm']}\n")
else:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["dateTime", "bpm"], delimiter="\t")
        w.writeheader()
        w.writerows(filtered_data)