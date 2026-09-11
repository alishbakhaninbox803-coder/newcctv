"""
Unified Multi-Channel Alert Dispatcher with Automated Fallback.

Supported Providers:
1. Meta WhatsApp Cloud API
2. Telegram Bot API

Behavior:
- In 'fallback' mode (default):
  Tries primary provider first (e.g. WhatsApp). If unconfigured, connection fails,
  or provider returns an error, automatically routes the alert to the secondary
  provider (e.g. Telegram).
- In 'broadcast' mode:
  Sends alerts concurrently/sequentially to both providers.
"""
import logging
from app.config import settings
from app.whatsapp import send_whatsapp_text, send_whatsapp_image_alert, _is_meta_configured
from app.telegram import send_telegram_text, send_telegram_image_alert, is_telegram_configured

logger = logging.getLogger(__name__)


def _is_whatsapp_successful(res: dict) -> bool:
    """Evaluates if Meta WhatsApp response indicates successful delivery."""
    if not isinstance(res, dict):
        return False
    if res.get("skipped") or res.get("error"):
        return False
    # Meta Cloud API success has 'messages' list with message ID
    if "messages" in res and isinstance(res["messages"], list) and len(res["messages"]) > 0:
        return True
    return False


def _is_telegram_successful(res: dict) -> bool:
    """Evaluates if Telegram response indicates successful delivery."""
    if not isinstance(res, dict):
        return False
    if res.get("skipped") or res.get("error"):
        return False
    # Telegram Bot API returns ok: True on success
    return bool(res.get("ok"))


def dispatch_image_alert(snapshot_path: str, caption: str) -> dict:
    """
    Dispatches a snapshot photo alert with fallback between WhatsApp and Telegram.
    """
    mode = getattr(settings, "ALERT_MODE", "fallback").lower()
    primary = getattr(settings, "PRIMARY_ALERT_PROVIDER", "whatsapp").lower()

    if mode == "broadcast":
        wa_res = send_whatsapp_image_alert(snapshot_path, caption)
        tg_res = send_telegram_image_alert(snapshot_path, caption)
        return {
            "mode": "broadcast",
            "whatsapp": wa_res,
            "telegram": tg_res,
            "delivered": _is_whatsapp_successful(wa_res) or _is_telegram_successful(tg_res),
        }

    # Fallback Mode
    if primary == "telegram":
        first_name, first_fn, first_check = "telegram", send_telegram_image_alert, _is_telegram_successful
        second_name, second_fn, second_check = "whatsapp", send_whatsapp_image_alert, _is_whatsapp_successful
    else:
        first_name, first_fn, first_check = "whatsapp", send_whatsapp_image_alert, _is_whatsapp_successful
        second_name, second_fn, second_check = "telegram", send_telegram_image_alert, _is_telegram_successful

    logger.info(f"[AlertDispatcher] Attempting primary provider: {first_name}...")
    first_res = first_fn(snapshot_path, caption)

    if first_check(first_res):
        logger.info(f"[AlertDispatcher] Alert delivered successfully via primary ({first_name}).")
        return {
            "delivered": True,
            "provider": first_name,
            "fallback_used": False,
            "response": first_res,
        }

    # Primary failed or was skipped -> execute fallback
    reason = first_res.get("error") or first_res.get("reason") or "API error / unconfigured"
    logger.warning(
        f"[AlertDispatcher] Primary provider '{first_name}' did not succeed ({reason}). "
        f"Switching to fallback provider: '{second_name}'..."
    )
    print(f"\033[93m[AlertDispatcher] Primary '{first_name}' failed -> Fallback to '{second_name}'\033[0m")

    second_res = second_fn(snapshot_path, caption)
    if second_check(second_res):
        logger.info(f"[AlertDispatcher] Alert delivered successfully via fallback ({second_name}).")
        return {
            "delivered": True,
            "provider": second_name,
            "fallback_used": True,
            "primary_error": reason,
            "response": second_res,
        }

    logger.error(
        f"[AlertDispatcher] Both providers failed. Primary ({first_name}): {first_res}, Fallback ({second_name}): {second_res}"
    )
    return {
        "delivered": False,
        "fallback_used": True,
        "primary": first_res,
        "fallback": second_res,
    }


def dispatch_text_alert(message: str) -> dict:
    """
    Dispatches a text alert with fallback between WhatsApp and Telegram.
    """
    mode = getattr(settings, "ALERT_MODE", "fallback").lower()
    primary = getattr(settings, "PRIMARY_ALERT_PROVIDER", "whatsapp").lower()

    if mode == "broadcast":
        wa_res = send_whatsapp_text(message)
        tg_res = send_telegram_text(message)
        return {
            "mode": "broadcast",
            "whatsapp": wa_res,
            "telegram": tg_res,
            "delivered": _is_whatsapp_successful(wa_res) or _is_telegram_successful(tg_res),
        }

    if primary == "telegram":
        first_name, first_fn, first_check = "telegram", send_telegram_text, _is_telegram_successful
        second_name, second_fn, second_check = "whatsapp", send_whatsapp_text, _is_whatsapp_successful
    else:
        first_name, first_fn, first_check = "whatsapp", send_whatsapp_text, _is_whatsapp_successful
        second_name, second_fn, second_check = "telegram", send_telegram_text, _is_telegram_successful

    first_res = first_fn(message)
    if first_check(first_res):
        return {
            "delivered": True,
            "provider": first_name,
            "fallback_used": False,
            "response": first_res,
        }

    second_res = second_fn(message)
    return {
        "delivered": second_check(second_res),
        "provider": second_name,
        "fallback_used": True,
        "response": second_res,
    }
