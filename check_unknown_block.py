path = "backend/app/camera_worker.py"
with open(path, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

idx = content.find("def _log_and_alert")
print("Index of _log_and_alert:", idx)

if idx != -1:
    print(content[idx:idx+2500])
else:
    print("FUNCTION NOT FOUND AT ALL - checking whole file length:", len(content))