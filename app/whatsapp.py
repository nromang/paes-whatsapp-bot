
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests
from fastapi import HTTPException

GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v23.0")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://paes-whatsapp-bot.onrender.com").rstrip("/")


def is_live_mode() -> bool:
    return bool(PHONE_NUMBER_ID and ACCESS_TOKEN)


def _post_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not is_live_mode():
        return {"mock": True, "payload": payload}
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"WhatsApp API error: {response.text[:500]}")
    return response.json()


def send_text(to_phone: str, body: str) -> Dict[str, Any]:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": body,
        },
    }
    return _post_payload(payload)


def send_list_menu(to_phone: str, body: str) -> Dict[str, Any]:
    # Lista compacta para el menú principal.
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Bot PAES"},
            "body": {"text": body},
            "footer": {"text": "Selecciona una materia"},
            "action": {
                "button": "Ver materias",
                "sections": [
                    {
                        "title": "Prácticas disponibles",
                        "rows": [
                            {"id": "PRACTICA LECTORA 8", "title": "Competencia Lectora", "description": "Práctica corta"},
                            {"id": "PRACTICA M1 8", "title": "Matemática 1 (M1)", "description": "Práctica corta"},
                            {"id": "PRACTICA M2 8", "title": "Matemática 2 (M2)", "description": "Práctica corta"},
                            {"id": "PRACTICA HISTORIA 8", "title": "Historia y Ciencias Sociales", "description": "Práctica corta"},
                            {"id": "PRACTICA CIENCIAS BIOLOGIA 8", "title": "Ciencias - Biología", "description": "Práctica corta"},
                            {"id": "PRACTICA CIENCIAS FISICA 8", "title": "Ciencias - Física", "description": "Práctica corta"},
                            {"id": "PRACTICA CIENCIAS QUIMICA 8", "title": "Ciencias - Química", "description": "Práctica corta"},
                            {"id": "PRACTICA CIENCIAS TP 8", "title": "Ciencias - Técnico Profesional", "description": "Práctica corta"},
                        ],
                    }
                ],
            },
        },
    }
    return _post_payload(payload)


def extract_incoming_text(message: Dict[str, Any]) -> Optional[str]:
    msg_type = message.get("type")
    if msg_type == "text":
        return message.get("text", {}).get("body")
    if msg_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return interactive.get("button_reply", {}).get("title") or interactive.get("button_reply", {}).get("id")
        if interactive.get("type") == "list_reply":
            return interactive.get("list_reply", {}).get("id") or interactive.get("list_reply", {}).get("title")
    return None


def send_buttons(to_phone: str, body: str, buttons: List[Dict[str, str]], header: Optional[str] = None, footer: Optional[str] = None) -> Dict[str, Any]:
    interactive = {
        "type": "button",
        "body": {"text": body},
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {"id": btn["id"], "title": btn["title"]}
                } for btn in buttons[:3]
            ]
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "interactive",
        "interactive": interactive,
    }
    return _post_payload(payload)


def send_list(to_phone: str, header: str, body: str, button_text: str, rows: List[Dict[str, str]], footer: Optional[str] = None, section_title: str = "Opciones") -> Dict[str, Any]:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "action": {
                "button": button_text,
                "sections": [
                    {
                        "title": section_title,
                        "rows": rows[:10],
                    }
                ],
            },
        },
    }
    if footer:
        payload["interactive"]["footer"] = {"text": footer}
    return _post_payload(payload)


def send_image(to_phone: str, image_link: str, caption: Optional[str] = None) -> Dict[str, Any]:
    if image_link.startswith("/"):
        image_link = f"{PUBLIC_BASE_URL}{image_link}"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "image",
        "image": {"link": image_link},
    }
    if caption:
        payload["image"]["caption"] = caption
    return _post_payload(payload)
