path = "backend/app/camera_worker.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''        if event_type == "unknown_person":
            msg = build_unknown_person_message(
                self.camera_name, datetime.utcnow().strftime("%I:%M %p"), confidence or 0
            )
            if person_name:
                msg = f"{msg}\\nIdentity: {person_name}"
            send_whatsapp_image_alert(snapshot_path, msg)'''

new = '''        if event_type == "unknown_person":
            msg = build_unknown_person_message(
                self.camera_name, datetime.utcnow().strftime("%I:%M %p"), confidence or 0
            )
            if person_name:
                msg = f"{msg}\\nIdentity: {person_name}"
            print(f"[DEBUG-UNKNOWN-WA] sending, snapshot_path={snapshot_path}")
            wa_result = send_whatsapp_image_alert(snapshot_path, msg)
            print(f"[DEBUG-UNKNOWN-WA] result={wa_result}")'''

count = content.count(old)
print("Occurrences found:", count)
if count == 1:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCHED OK")
else:
    print("Not exactly 1 occurrence")