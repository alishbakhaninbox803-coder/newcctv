import os

path = "backend/app/camera_worker.py"
with open(path, "rb") as f:
    data = f.read().decode("utf-8", errors="replace")

def show_all(keyword, before=0, after=2000):
    start = 0
    n = 0
    while True:
        idx = data.find(keyword, start)
        if idx == -1:
            break
        n += 1
        print(f"\n===== '{keyword}' occurrence #{n} =====")
        print(data[max(0, idx-before):idx+after])
        start = idx + len(keyword)
    if n == 0:
        print(f"\n'{keyword}' NOT FOUND")

show_all("def _log_and_alert")
show_all("register_detection(")

wpath = "backend/app/weapon_engine.py"
if os.path.exists(wpath):
    with open(wpath, "rb") as f:
        wdata = f.read().decode("utf-8", errors="replace")
    print("\n\n===== weapon_engine.py (FULL FILE) =====\n")
    print(wdata)
else:
    print("weapon_engine.py NOT FOUND at", wpath)