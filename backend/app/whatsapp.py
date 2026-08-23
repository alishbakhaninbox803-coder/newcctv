"""
Sends WhatsApp alerts using Meta's free-tier WhatsApp Cloud API.
Setup: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
"""
import os
import requests
from app.config import settings


def send_whatsapp_text(message: str) -> dict:
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
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


def upload_media(image_path: str) -> str | None:
    """Uploads an image to WhatsApp Cloud API's media endpoint. Returns media_id or None."""
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        print("[whatsapp] Skipped media upload: WHATSAPP_TOKEN / PHONE_NUMBER_ID not configured.")
        return None

    if not image_path or not os.path.exists(image_path):
        print(f"[whatsapp] Media upload skipped: file not found at {image_path}")
        return None

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
    filename = os.path.basename(image_path)
    mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"

    try:
        with open(image_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            data = {"messaging_product": "whatsapp", "type": mime_type}
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=15)
        resp.raise_for_status()
        media_id = resp.json().get("id")
        return media_id
    except Exception as exc:
        print(f"[whatsapp] Media upload failed: {exc}")
        return None


def _upload_media(image_path: str) -> str | None:
    """Alias for backwards compatibility."""
    return upload_media(image_path)


def send_whatsapp_image_alert(image_path: str, caption: str) -> dict:
    """
    Sends an image alert with a caption to WhatsApp Admin Number using WhatsApp Cloud API.
    Uploads the snapshot image first, then sends the image message.
    Falls back to text notification if image upload fails.
    """
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        print("[whatsapp] Skipped: WHATSAPP_TOKEN / PHONE_NUMBER_ID not configured.")
        return {"skipped": True}

    if not image_path:
        return send_whatsapp_text(caption)

    media_id = upload_media(image_path)
    if not media_id:
        # Upload failed (bad path, network, token issue, etc.) — fallback to text alert
        return send_whatsapp_text(caption)

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": settings.WHATSAPP_ADMIN_NUMBER,
        "type": "image",
        "image": {"id": media_id, "caption": caption},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return resp.json()
    except Exception as exc:
        print(f"[whatsapp] Failed to send image alert: {exc}")
        return {"error": str(exc)}


def send_whatsapp_image(image_path: str, caption: str) -> dict:
    """Alias for send_whatsapp_image_alert."""
    return send_whatsapp_image_alert(image_path, caption)