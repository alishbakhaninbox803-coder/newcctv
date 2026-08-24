"""
Sends WhatsApp alerts using Meta's free-tier WhatsApp Cloud API.
Setup: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
"""
import os
import requests
from app.config import settings


def _configured() -> bool:
    return bool(settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)


def send_whatsapp_text(message: str) -> dict:
    if not _configured():
        print("[whatsapp] Skipped: WHATSAPP_TOKEN / PHONE_NUMBER_ID not configured.")
        return {"skipped": True}

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": settings.WHATSAPP_ADMIN_NUMBER,
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return resp.json()
    except Exception as exc:
        print(f"[whatsapp] Failed to send alert: {exc}")
        return {"error": str(exc)}


def send_whatsapp_image(image_path: str, caption: str = "") -> dict:
    """
    Uploads a local snapshot file to WhatsApp's media endpoint, then sends
    it as an image message with the given caption. Returns the final
    /messages response dict, or {"error": ...} / {"skipped": True}.
    """
    if not _configured():
        print("[whatsapp] Skipped: WHATSAPP_TOKEN / PHONE_NUMBER_ID not configured.")
        return {"skipped": True}

    if not image_path or not os.path.exists(image_path):
        print(f"[whatsapp] Skipped image send: snapshot not found at {image_path}")
        return {"error": "snapshot_not_found"}

    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}

    try:
        # Step 1: upload the media, get back a media_id
        upload_url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
            data = {"messaging_product": "whatsapp", "type": "image/jpeg"}
            upload_resp = requests.post(upload_url, headers=headers, data=data, files=files, timeout=15)
        upload_json = upload_resp.json()
        media_id = upload_json.get("id")
        if not media_id:
            print(f"[whatsapp] Media upload failed: {upload_json}")
            return {"error": "media_upload_failed", "detail": upload_json}

        # Step 2: send the image message referencing that media_id
        send_url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": settings.WHATSAPP_ADMIN_NUMBER,
            "type": "image",
            "image": {"id": media_id, "caption": caption[:1024]},
        }
        send_headers = {**headers, "Content-Type": "application/json"}
        send_resp = requests.post(send_url, headers=send_headers, json=payload, timeout=10)
        return send_resp.json()
    except Exception as exc:
        print(f"[whatsapp] Failed to send image alert: {exc}")
        return {"error": str(exc)}


def send_whatsapp_image_alert(snapshot_path: str, caption: str) -> dict:
    """
    Preferred entry point for alerts: sends the snapshot as an image with
    the alert text as its caption. Falls back to a plain text message if
    there's no snapshot to attach, or if the image send fails/errors out
    (so an alert still goes out even when the photo can't be delivered).
    """
    if not snapshot_path:
        return send_whatsapp_text(caption)

    result = send_whatsapp_image(snapshot_path, caption)
    if "error" in result:
        print(f"[whatsapp] Image alert failed ({result['error']}), falling back to text.")
        return send_whatsapp_text(caption)
    return result


def build_unknown_person_message(camera_name, timestamp, confidence):
    return (
        "🚨 Unknown Person Detected\n"
        f"Camera: {camera_name}\n"
        f"Time: {timestamp}\n"
        f"Confidence: {confidence:.0%}\n"
        "Status: Face not found in registered members."
    )


def build_restricted_object_message(camera_name, object_name, timestamp, confidence):
    return (
        "🚨 Restricted Object Detected\n"
        f"Camera: {camera_name}\n"
        f"Object: {object_name}\n"
        f"Time: {timestamp}\n"
        f"Confidence: {confidence:.0%}"
    )