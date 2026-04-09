from __future__ import annotations

from contextlib import closing
from typing import Any, Dict, List

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import clear_menu_state, get_db, get_menu_state, init_db, set_menu_state, upsert_user
from .services import (
    build_numeric_main_menu,
    build_numeric_sciences_menu,
    build_numeric_subject_menu,
    build_report,
    build_report_chunks,
    build_subject_help,
    build_user_progress,
    create_session,
    finalize_session,
    get_active_session,
    get_context_assets,
    get_current_session_question,
    get_question_assets,
    get_question_by_id,
    get_session,
    get_session_questions,
    intro_message,
    list_questions_summary,
    load_official_config,
    normalize_text,
    parse_mode_and_size,
    parse_subject_code,
    render_context_chunks,
    render_question_parts,
    select_questions_for_session,
    answer_question,
    advance_session,
)
from .whatsapp import extract_incoming_text, send_image, send_list, send_text

VERIFY_TOKEN = __import__("os").getenv("WHATSAPP_VERIFY_TOKEN", "paes_verify_token")

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="PAES WhatsApp Bot Pro",
    version="2.5.0",
    description="Bot profesional para práctica y ensayo PAES por WhatsApp.",
)

if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class SendTestMessage(BaseModel):
    to: str
    body: str


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> Dict[str, Any]:
    return {"status": "ok", "service": "PAES WhatsApp Bot Pro", "version": "2.5.0"}


@app.get("/health")
def health() -> Dict[str, Any]:
    cfg = load_official_config()
    return {
        "status": "ok",
        "subjects_loaded": len(cfg),
        "question_sample_count": len(list_questions_summary(limit=1000)),
    }


@app.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


def dispatch_outbound(phone: str, items: List[Dict[str, Any]]) -> None:
    last_error = None
    for item in items:
        kind = item.get("type", "text")
        try:
            if kind == "text":
                body = (item.get("body") or "").strip()
                if body:
                    send_text(phone, body)
            elif kind == "list":
                send_list(
                    phone,
                    header=item.get("header", "Bot PAES"),
                    body=item["body"],
                    button_text=item.get("button_text", "Ver opciones"),
                    rows=item["rows"],
                    footer=item.get("footer"),
                    section_title=item.get("section_title", "Opciones"),
                )
            elif kind == "image":
                if item.get("url"):
                    send_image(phone, image_link=item["url"], caption=item.get("caption") or None)
        except Exception as exc:
            print(f"Outbound item error for {phone} [{kind}]: {exc}")
            last_error = exc
            continue
    if last_error is not None and not items:
        raise last_error


def build_main_menu_payload(phone: str | None = None) -> List[Dict[str, Any]]:
    if phone:
        set_menu_state(phone, "main")
    return [{"type": "text", "body": build_numeric_main_menu()}]


def build_sciences_menu_payload(phone: str) -> List[Dict[str, Any]]:
    set_menu_state(phone, "ciencias")
    return [{"type": "text", "body": build_numeric_sciences_menu()}]


def build_subject_menu_payload(phone: str, subject_code: str) -> List[Dict[str, Any]]:
    set_menu_state(phone, "subject", subject_code=subject_code)
    return [{"type": "text", "body": build_numeric_subject_menu(subject_code)}]


def build_progress_payload(phone: str) -> List[Dict[str, Any]]:
    clear_menu_state(phone)
    return [{"type": "text", "body": build_user_progress(phone)}]


def build_question_payload(question: Dict[str, Any], sequence: int, total: int, include_context: bool = True) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if include_context:
        for chunk in render_context_chunks(question.get("context_id")):
            items.append({"type": "text", "body": chunk})
        for asset in get_context_assets(question.get("context_id")):
            items.append({"type": "image", "url": asset["url"], "caption": asset.get("caption")})
    for asset in get_question_assets(question):
        items.append({"type": "image", "url": asset["url"], "caption": asset.get("caption")})
    for part in render_question_parts(question, sequence, total):
        items.append({"type": "text", "body": part})
    return items


def start_session_payload(phone: str, subject_code: str, mode: str, requested_size: int | None) -> List[Dict[str, Any]]:
    clear_menu_state(phone)
    selected_questions, exam_config = select_questions_for_session(phone, subject_code, mode, requested_size)
    if not selected_questions:
        return [{"type": "text", "body": "No tengo preguntas activas para esa materia en el banco actual. Si ya practicaste antes, prueba Repaso inteligente o cambia de materia."}]
    session_id = create_session(phone, subject_code, mode, selected_questions, exam_config)
    session = get_session(session_id)
    current = get_current_session_question(session_id)
    question = get_question_by_id(current["question_id"])
    preface = [
        f"🚀 Sesión iniciada: {'Ensayo oficial' if mode == 'ensayo' else 'Simulacro (30)' if mode == 'simulacro' else 'Repaso inteligente' if mode == 'repaso' else 'Práctica rápida (10)'}",
        f"Materia: {question['subject_label']}",
        f"Preguntas cargadas: {len(selected_questions)}",
        "",
    ]
    if mode == "ensayo" and len(selected_questions) < exam_config["total_questions"]:
        preface.extend([
            "Aviso: el banco actual no contiene toda la forma oficial.",
            "El puntaje PAES se mostrará como proyección.",
            "",
        ])
    items = [{"type": "text", "body": "\n".join(preface)}]
    items.extend(build_question_payload(question, session["current_sequence"], len(selected_questions), include_context=True))
    return items


def handle_menu_navigation(phone: str, incoming_text: str):
    norm = normalize_text(incoming_text)
    menu_state = get_menu_state(phone)
    state = menu_state["state"] if menu_state else None
    subject_code = menu_state["subject_code"] if menu_state else None

    if state == "main":
        if norm == "1":
            return build_subject_menu_payload(phone, "m1")
        if norm == "2":
            return build_subject_menu_payload(phone, "lectora")
        if norm == "3":
            return build_subject_menu_payload(phone, "historia")
        if norm == "4":
            return build_subject_menu_payload(phone, "m2")
        if norm == "5":
            return build_sciences_menu_payload(phone)
        if norm == "6":
            return build_progress_payload(phone)
        if norm == "7":
            return [{"type": "text", "body": build_subject_help()}]
        if norm == "0":
            return build_main_menu_payload(phone)
        if norm.isdigit():
            return [{"type": "text", "body": "Opción no válida. Escribe un número del menú."}]

    if state == "ciencias":
        mapping = {"1": "ciencias_biologia", "2": "ciencias_fisica", "3": "ciencias_quimica", "4": "ciencias_tp"}
        if norm in mapping:
            return build_subject_menu_payload(phone, mapping[norm])
        if norm == "0":
            return build_main_menu_payload(phone)
        if norm.isdigit():
            return [{"type": "text", "body": "Opción no válida. En Ciencias usa 1, 2, 3, 4 o 0."}]

    if state == "subject" and subject_code:
        if norm == "1":
            return start_session_payload(phone, subject_code, "practice", 10)
        if norm == "2":
            return start_session_payload(phone, subject_code, "simulacro", 30)
        if norm == "3":
            return start_session_payload(phone, subject_code, "ensayo", None)
        if norm == "4":
            return start_session_payload(phone, subject_code, "repaso", 10)
        if norm == "0":
            if subject_code.startswith("ciencias_"):
                return build_sciences_menu_payload(phone)
            return build_main_menu_payload(phone)
        if norm.isdigit():
            return [{"type": "text", "body": "Opción no válida. Usa 1, 2, 3, 4 o 0."}]

    return None


def handle_no_active_session(phone: str, incoming_text: str) -> List[Dict[str, Any]]:
    norm = normalize_text(incoming_text)
    if norm in {"HOLA", "MENU", "MENÚ", "PAES", "INICIO"}:
        return build_main_menu_payload(phone)
    if norm == "PROGRESO":
        return build_progress_payload(phone)
    if norm == "AYUDA":
        return [{"type": "text", "body": build_subject_help()}]

    menu_reply = handle_menu_navigation(phone, incoming_text)
    if menu_reply is not None:
        return menu_reply

    if norm.startswith("MENU:"):
        subject_code = norm.split(":", 1)[1].lower()
        return build_subject_menu_payload(phone, subject_code)

    subject_code = parse_subject_code(incoming_text)
    if not subject_code:
        return [{"type": "text", "body": "No entendí esa opción. Escribe MENU y te mostraré un menú corto por números."}]

    mode, requested_size = parse_mode_and_size(incoming_text)
    return start_session_payload(phone, subject_code, mode, requested_size)


def handle_active_session(phone: str, incoming_text: str, session) -> List[Dict[str, Any]]:
    norm = normalize_text(incoming_text)
    if norm == "MENU" or norm == "MENÚ":
        return [{"type": "text", "body": "Tienes una sesión activa. Responde A/B/C/D/E según corresponda. Comandos: OMITIR, RESULTADO, PROGRESO o SALIR."}]
    if norm == "PROGRESO":
        return [{"type": "text", "body": build_user_progress(phone)}]
    if norm in {"RESULTADO", "SALIR"}:
        finalize_session(session["id"], status="finished" if norm == "RESULTADO" else "abandoned")
        clear_menu_state(phone)
        return [
            *[{"type": "text", "body": chunk} for chunk in build_report_chunks(session["id"])]
        ]

    current_row = get_current_session_question(session["id"])
    if current_row is None:
        finalize_session(session["id"])
        clear_menu_state(phone)
        return [
            *[{"type": "text", "body": chunk} for chunk in build_report_chunks(session["id"])]
        ]

    question = get_question_by_id(current_row["question_id"])
    allowed = set(question["options"].keys())


    if norm == "OMITIR":
        answer_question(session["id"], None)
    elif norm in allowed:
        answer_question(session["id"], norm)
    else:
        return [{"type": "text", "body": "Respuesta no válida. Usa A/B/C/D/E según corresponda, o escribe OMITIR."}]

    all_rows = get_session_questions(session["id"])
    if current_row["sequence"] >= len(all_rows):
        finalize_session(session["id"])
        clear_menu_state(phone)
        return [
            *[{"type": "text", "body": chunk} for chunk in build_report_chunks(session["id"])]
        ]

    advance_session(session["id"])
    updated_session = get_session(session["id"])
    next_row = get_current_session_question(session["id"])
    next_question = get_question_by_id(next_row["question_id"])
    include_context = next_question.get("context_id") != question.get("context_id")
    return build_question_payload(next_question, updated_session["current_sequence"], len(all_rows), include_context=include_context)


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = value.get("contacts", [])
            contact_name = contacts[0].get("profile", {}).get("name") if contacts else None
            for message in value.get("messages", []):
                phone = message.get("from")
                if not phone:
                    continue
                try:
                    upsert_user(phone, contact_name)
                    incoming_text = extract_incoming_text(message)
                    if not incoming_text:
                        dispatch_outbound(phone, [{"type": "text", "body": "Solo proceso texto o interacciones del menú."}])
                        continue
                    session = get_active_session(phone)
                    if session is None:
                        reply_items = handle_no_active_session(phone, incoming_text)
                    else:
                        reply_items = handle_active_session(phone, incoming_text, session)
                    dispatch_outbound(phone, reply_items)
                except Exception as exc:
                    print(f"Webhook processing error for {phone}: {exc}")
                    try:
                        dispatch_outbound(phone, [{"type": "text", "body": "Ocurrió un problema al procesar este bloque. Escribe MENU para reiniciar o intenta nuevamente."}])
                    except Exception as send_exc:
                        print(f"Outbound fallback error for {phone}: {send_exc}")
                    continue
    return JSONResponse({"received": True})


@app.get("/admin/questions")
def admin_questions(limit: int = 50):
    return list_questions_summary(limit=limit)


@app.get("/admin/config")
def admin_config():
    return load_official_config()


@app.get("/admin/sessions")
def admin_sessions(limit: int = 20):
    with closing(get_db()) as conn:
        rows = conn.execute(
            """
            SELECT id, phone, subject_code, mode, status, exam_form, official_scoring_mode,
                   official_paes_score, estimated_paes_score, raw_correct_valid,
                   valid_questions_total, answered_questions_total, omitted_questions_total,
                   score_percent, started_at, finished_at
            FROM sessions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
