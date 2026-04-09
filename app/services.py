from __future__ import annotations

import json
import math
import random
import re
from contextlib import closing
from pathlib import Path

from PIL import Image
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .database import get_db, utc_now_iso

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_QUESTION_ASSETS_DIR = BASE_DIR / "static" / "question_assets"
QUESTION_BANK_PATH = DATA_DIR / "question_bank.json"
CONTEXTS_PATH = DATA_DIR / "contexts.json"
OFFICIAL_CONFIG_PATH = DATA_DIR / "official_exam_config.json"

MAX_WHATSAPP_TEXT = 2500
MIN_VALID_ASSET_HEIGHT = 500
MIN_VALID_ASSET_RATIO = 0.45

SUBJECT_ALIASES = {
    "LENGUAJE": "lectora",
    "LECTORA": "lectora",
    "COMPETENCIA LECTORA": "lectora",
    "M1": "m1",
    "MATEMATICA 1": "m1",
    "MATEMÁTICA 1": "m1",
    "M2": "m2",
    "MATEMATICA 2": "m2",
    "MATEMÁTICA 2": "m2",
    "HISTORIA": "historia",
    "CIENCIAS BIOLOGIA": "ciencias_biologia",
    "CIENCIAS BIOLOGÍA": "ciencias_biologia",
    "BIOLOGIA": "ciencias_biologia",
    "BIOLOGÍA": "ciencias_biologia",
    "CIENCIAS FISICA": "ciencias_fisica",
    "CIENCIAS FÍSICA": "ciencias_fisica",
    "FISICA": "ciencias_fisica",
    "FÍSICA": "ciencias_fisica",
    "CIENCIAS QUIMICA": "ciencias_quimica",
    "CIENCIAS QUÍMICA": "ciencias_quimica",
    "QUIMICA": "ciencias_quimica",
    "QUÍMICA": "ciencias_quimica",
    "CIENCIAS TP": "ciencias_tp",
    "TP": "ciencias_tp",
    "TECNICO PROFESIONAL": "ciencias_tp",
    "TÉCNICO PROFESIONAL": "ciencias_tp",
}

SUBJECT_SHORTCUTS = {
    "lectora": "LECTORA",
    "m1": "M1",
    "m2": "M2",
    "historia": "HISTORIA",
    "ciencias_biologia": "CIENCIAS BIOLOGIA",
    "ciencias_fisica": "CIENCIAS FISICA",
    "ciencias_quimica": "CIENCIAS QUIMICA",
    "ciencias_tp": "CIENCIAS TP",
}

MAIN_MENU_ORDER = [
    "lectora",
    "m1",
    "m2",
    "historia",
    "ciencias_biologia",
    "ciencias_fisica",
    "ciencias_quimica",
    "ciencias_tp",
]
DEFAULT_PRACTICE_SIZE = 10
LONG_PRACTICE_SIZE = 30
MIN_PRACTICE_SIZE = 5
MAX_PRACTICE_SIZE = 30


def normalize_text(text: str) -> str:
    text = text.strip().upper()
    text = re.sub(r"\s+", " ", text)
    return text


def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_question_bank() -> List[Dict[str, Any]]:
    return load_json(QUESTION_BANK_PATH) or []


def load_contexts() -> Dict[str, Dict[str, Any]]:
    return load_json(CONTEXTS_PATH) or {}


def load_official_config() -> Dict[str, Dict[str, Any]]:
    return load_json(OFFICIAL_CONFIG_PATH) or {}


def subject_catalog() -> Dict[str, str]:
    cfg = load_official_config()
    return {k: cfg[k]["label"] for k in cfg}


def parse_subject_code(raw_text: str) -> Optional[str]:
    norm = normalize_text(raw_text)
    for alias, code in SUBJECT_ALIASES.items():
        if alias in norm:
            return code
    return None


def parse_mode_and_size(raw_text: str) -> Tuple[str, Optional[int]]:
    norm = normalize_text(raw_text)
    mode = "practice"
    if norm.startswith("ENSAYO"):
        mode = "ensayo"
    elif norm.startswith("SIMULACRO") or norm.startswith("PRACTICA30") or norm.startswith("PRACTICA 30"):
        mode = "simulacro"
    elif norm.startswith("REPASO"):
        mode = "repaso"

    size_match = re.search(r"\b(10|20|30)\b", norm)
    size = int(size_match.group(1)) if size_match else None
    if size is not None:
        size = max(MIN_PRACTICE_SIZE, min(MAX_PRACTICE_SIZE, size))
    if mode == "practice" and size is None:
        size = DEFAULT_PRACTICE_SIZE
    if mode == "simulacro":
        size = LONG_PRACTICE_SIZE
    if mode == "repaso" and size is None:
        size = DEFAULT_PRACTICE_SIZE
    return mode, size


def intro_message() -> str:
    return (
        "🎓 Bot PAES v2.5\n\n"
        "Responde con un número:\n"
        "1. M1\n"
        "2. Competencia Lectora\n"
        "3. Historia y Cs. Sociales\n"
        "4. M2\n"
        "5. Ciencias\n"
        "6. Mi progreso\n"
        "7. Ayuda\n\n"
        "Puedes escribir MENU en cualquier momento."
    )


def build_numeric_main_menu() -> str:
    return intro_message()


def build_numeric_sciences_menu() -> str:
    return (
        "🔬 Ciencias disponibles\n\n"
        "1. Biología\n"
        "2. Física\n"
        "3. Química\n"
        "4. Técnico Profesional\n"
        "0. Volver al menú principal"
    )


def build_numeric_subject_menu(subject_code: str) -> str:
    cfg = load_official_config().get(subject_code, {})
    label = cfg.get("label", subject_code)
    back_label = "Volver a Ciencias" if subject_code.startswith("ciencias_") else "Volver al menú principal"
    return (
        f"📚 {label}\n\n"
        "1. Práctica rápida (10)\n"
        "2. Simulacro (30)\n"
        "3. Ensayo oficial\n"
        "4. Repaso inteligente\n"
        f"0. {back_label}\n\n"
        "Responde con un número."
    )


def build_subject_help() -> str:
    cfg = load_official_config()
    lines = ["Ayuda rápida", "", "Materias disponibles:"]
    for code in MAIN_MENU_ORDER:
        meta = cfg[code]
        suffix = f" - {meta['track']}" if meta.get("track") else ""
        lines.append(f"• {meta['label']} (forma {meta['form']}{suffix})")
    lines.extend([
        "",
        "Comandos útiles:",
        "• MENU",
        "• PROGRESO",
        "• SALIR",
        "• RESULTADO",
        "• OMITIR",
        "",
        "Ejemplos:",
        "• PRACTICA M1",
        "• SIMULACRO HISTORIA",
        "• ENSAYO LECTORA",
        "• REPASO M2",
    ])
    return "\n".join(lines)


def build_main_menu_rows() -> List[Dict[str, str]]:
    cfg = load_official_config()
    rows = []
    for code in MAIN_MENU_ORDER:
        rows.append(
            {
                "id": f"MENU:{code}",
                "title": cfg[code]["label"][:24],
                "description": "Elegir modo de práctica",
            }
        )
    return rows


def build_subject_mode_rows(subject_code: str) -> List[Dict[str, str]]:
    cfg = load_official_config().get(subject_code, {})
    label = cfg.get("label", subject_code)
    shortcut = SUBJECT_SHORTCUTS.get(subject_code, label.upper())
    return [
        {"id": f"PRACTICA {shortcut}", "title": "Práctica 10", "description": f"10 preguntas aleatorias de {label}"[:72]},
        {"id": f"SIMULACRO {shortcut}", "title": "Simulacro 30", "description": "30 preguntas aleatorias, más parecido a la prueba"[:72]},
        {"id": f"ENSAYO {shortcut}", "title": "Ensayo", "description": "Usa toda la forma disponible en el banco"[:72]},
        {"id": "MENU", "title": "Volver al menú", "description": "Elegir otra materia"},
    ]


def find_questions(subject_code: str, only_active: bool = True, require_exact_form: Optional[str] = None) -> List[Dict[str, Any]]:
    bank = load_question_bank()
    questions = [q for q in bank if q["subject_code"] == subject_code]
    if only_active:
        questions = [q for q in questions if q.get("active", True)]
    if require_exact_form:
        questions = [q for q in questions if q.get("exam_form") == require_exact_form]
    return sorted(questions, key=lambda q: q["question_number"])


def get_previously_seen_question_ids(phone: str, subject_code: str) -> set[str]:
    with closing(get_db()) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT sq.question_id
            FROM session_questions sq
            JOIN sessions s ON s.id = sq.session_id
            WHERE s.phone = ? AND s.subject_code = ?
            """,
            (phone, subject_code),
        ).fetchall()
        return {str(r[0]) for r in rows}


def choose_random_without_repeats(phone: str, subject_code: str, pool: Sequence[Dict[str, Any]], size: int) -> List[Dict[str, Any]]:
    if len(pool) <= size:
        shuffled = list(pool)
        random.shuffle(shuffled)
        return shuffled

    seen_ids = get_previously_seen_question_ids(phone, subject_code)
    unseen = [q for q in pool if q["id"] not in seen_ids]
    selected: List[Dict[str, Any]] = []
    if len(unseen) >= size:
        selected = random.sample(unseen, size)
    else:
        selected.extend(unseen)
        remaining = [q for q in pool if q["id"] not in {x["id"] for x in selected}]
        need = size - len(selected)
        if need > 0:
            selected.extend(random.sample(remaining, need))
    random.shuffle(selected)
    return selected


def get_review_pool(phone: str, subject_code: str) -> List[Dict[str, Any]]:
    with closing(get_db()) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT sq.question_id
            FROM session_questions sq
            JOIN sessions s ON s.id = sq.session_id
            WHERE s.phone = ?
              AND s.subject_code = ?
              AND (sq.response_option IS NULL OR sq.is_correct = 0)
            ORDER BY sq.id DESC
            """,
            (phone, subject_code),
        ).fetchall()
    review_ids = [str(r[0]) for r in rows]
    bank_by_id = {q["id"]: q for q in find_questions(subject_code, only_active=True)}
    return [bank_by_id[qid] for qid in review_ids if qid in bank_by_id]


def select_questions_for_session(phone: str, subject_code: str, mode: str, requested_size: Optional[int]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    cfg = load_official_config().get(subject_code)
    if not cfg:
        return [], {}
    pool = find_questions(subject_code, only_active=True, require_exact_form=cfg["form"])
    pool = [q for q in pool if not (question_needs_visual_support(q) and _local_question_asset_url(q["id"]) is None and _question_text_quality(q) == "poor")]
    if mode == "ensayo":
        selected = sorted(pool, key=lambda q: q["question_number"])
    elif mode == "repaso":
        size = requested_size or DEFAULT_PRACTICE_SIZE
        selected = get_review_pool(phone, subject_code)[:size]
    else:
        size = requested_size or (LONG_PRACTICE_SIZE if mode == "simulacro" else DEFAULT_PRACTICE_SIZE)
        selected = choose_random_without_repeats(phone, subject_code, pool, size)
    return selected, cfg


def create_session(phone: str, subject_code: str, mode: str, selected_questions: Sequence[Dict[str, Any]], exam_config: Dict[str, Any]) -> int:
    if not selected_questions:
        raise ValueError("No hay preguntas disponibles para esa materia.")
    with closing(get_db()) as conn:
        now = utc_now_iso()
        cur = conn.cursor()
        cur.execute(
            "UPDATE sessions SET status = 'abandoned', finished_at = ?, notes = COALESCE(notes, '') || '\nSesión cerrada por nueva sesión.' WHERE phone = ? AND status = 'active'",
            (now, phone),
        )
        exam_form = exam_config.get("form")
        valid_in_session = sum(1 for q in selected_questions if q.get("is_scored"))
        cur.execute(
            """
            INSERT INTO sessions(
                phone, subject_code, mode, status, exam_form, official_scoring_mode,
                valid_questions_total, current_sequence, started_at
            ) VALUES (?, ?, ?, 'active', ?, 'none', ?, 1, ?)
            """,
            (phone, subject_code, mode, exam_form, valid_in_session, now),
        )
        session_id = cur.lastrowid
        rows = []
        for seq, q in enumerate(selected_questions, start=1):
            rows.append(
                (
                    session_id,
                    seq,
                    q["id"],
                    q.get("question_number"),
                    q.get("context_id"),
                    int(bool(q.get("is_scored", True))),
                    int(bool(q.get("is_deleted", False))),
                    len(q.get("options", {})),
                )
            )
        cur.executemany(
            """
            INSERT INTO session_questions(session_id, sequence, question_id, question_number, context_id, is_scored, is_deleted, max_options)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()
        return int(session_id)


def get_active_session(phone: str):
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT * FROM sessions WHERE phone = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (phone,),
        ).fetchone()


def get_session(session_id: int):
    with closing(get_db()) as conn:
        return conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()


def get_session_questions(session_id: int):
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT * FROM session_questions WHERE session_id = ? ORDER BY sequence",
            (session_id,),
        ).fetchall()


def get_question_by_id(question_id: str) -> Optional[Dict[str, Any]]:
    for q in load_question_bank():
        if q["id"] == question_id:
            return q
    return None


def get_current_session_question(session_id: int):
    session = get_session(session_id)
    if session is None:
        return None
    with closing(get_db()) as conn:
        row = conn.execute(
            """
            SELECT sq.* FROM session_questions sq
            WHERE sq.session_id = ? AND sq.sequence = ?
            """,
            (session_id, session["current_sequence"]),
        ).fetchone()
        return row


def allowed_options(question: Dict[str, Any]) -> List[str]:
    return list(question.get("options", {}).keys())



def _cleanup_common_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "")
    text = text.replace("\u00a0", " ")
    text = text.replace("“ ", "“").replace(" ”", "”")
    text = text.replace("‘ ", "‘").replace(" ’", "’")
    text = text.replace("( ", "(").replace(" )", ")")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:%!?])", r"\1", text)
    text = re.sub(r"([¿¡(])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]])", r"\1", text)
    text = re.sub(r"([0-9])([A-Za-zÁÉÍÓÚáéíóú])", r"\1 \2", text)
    text = re.sub(r"([A-Za-zÁÉÍÓÚáéíóú])([0-9])", r"\1 \2", text)
    text = re.sub(r"([)\]])([A-Za-zÁÉÍÓÚáéíóú])", r"\1 \2", text)
    return text.strip()


def _looks_like_table_or_math(lines: List[str]) -> bool:
    if not lines:
        return False
    short_lines = sum(1 for ln in lines if len(ln) <= 8)
    symbol_lines = sum(1 for ln in lines if re.fullmatch(r"[0-9A-Za-zÁÉÍÓÚáéíóú∞°%+\-*/<>=()\[\],.: ]+", ln))
    keywords = {"tabla", "gráfico", "grafico", "figura", "diagrama"}
    has_visual_label = any(any(k in ln.lower() for k in keywords) for ln in lines)
    return has_visual_label or (len(lines) >= 4 and short_lines >= 2 and symbol_lines >= 2)


def _join_wrapped_paragraphs(text: str) -> str:
    text = _cleanup_common_text(text)
    paragraphs = re.split(r"\n\s*\n", text)
    cleaned_parts: List[str] = []
    for para in paragraphs:
        lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
        if not lines:
            continue
        if _looks_like_table_or_math(lines):
            cleaned_parts.append("\n".join(lines))
            continue
        cleaned_parts.append(_cleanup_common_text(" ".join(lines)))
    return "\n\n".join(cleaned_parts).strip()


def split_text_for_whatsapp(text: str, limit: int = MAX_WHATSAPP_TEXT) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
            current = ""

    for para in paragraphs:
        units = re.split(r"(?<=[\.!?])\s+", para) if len(para) > limit else [para]
        for unit in units:
            unit = unit.strip()
            if not unit:
                continue
            if len(unit) > limit:
                words = unit.split()
                temp = ""
                for word in words:
                    candidate = f"{temp} {word}".strip()
                    if len(candidate) > limit:
                        if temp:
                            maybe = f"{current}\n\n{temp}".strip() if current else temp
                            if len(maybe) > limit:
                                flush()
                                current = temp
                            else:
                                current = maybe
                        temp = word
                    else:
                        temp = candidate
                if temp:
                    maybe = f"{current}\n\n{temp}".strip() if current else temp
                    if len(maybe) > limit:
                        flush()
                        current = temp
                    else:
                        current = maybe
            else:
                maybe = f"{current}\n\n{unit}".strip() if current else unit
                if len(maybe) > limit:
                    flush()
                    current = unit
                else:
                    current = maybe
    flush()
    return chunks


def _question_text_quality(question: Dict[str, Any]) -> str:
    text = question.get("stem", "") + "\n" + "\n".join(question.get("options", {}).values())
    if any(ch in text for ch in ["ò", "ï", "ð", "Å", "ã"]):
        return "poor"
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    short_lines = sum(1 for ln in lines if len(ln) <= 4)
    mathish_lines = sum(1 for ln in lines if re.fullmatch(r"[0-9∞°%+\-*/<>=()\[\],.: ]+", ln))
    if short_lines >= 3 and len(lines) >= 5:
        return "poor"
    if mathish_lines >= 2 and short_lines >= 2:
        return "poor"
    if _looks_like_table_or_math(lines) and question.get("stem", "").count("\n") >= 4:
        return "regular"
    return "good"


def question_needs_visual_support(question: Dict[str, Any]) -> bool:
    joined = (question.get("stem", "") + "\n" + "\n".join(question.get("options", {}).values())).lower()
    visual_keywords = [
        "gráfico", "grafico", "tabla", "figura", "diagrama", "imagen",
        "se indica a continuación", "como se muestra", "según la figura",
        "según el gráfico", "según la tabla", "en el siguiente gráfico",
        "en la siguiente figura", "en la siguiente tabla", "prisma",
    ]
    if any(keyword in joined for keyword in visual_keywords):
        return True
    return _question_text_quality(question) == "poor"


def render_context(context_id: Optional[str]) -> Optional[str]:
    chunks = render_context_chunks(context_id)
    return "\n\n".join(chunks) if chunks else None


def render_context_chunks(context_id: Optional[str]) -> List[str]:
    if not context_id:
        return []
    context = load_contexts().get(context_id)
    if not context:
        return []
    title = context.get("title", "Contexto")
    body = _join_wrapped_paragraphs(context.get("body", ""))
    full = f"📘 {title}\n\n{body}".strip()
    return split_text_for_whatsapp(full, MAX_WHATSAPP_TEXT)


def get_context_assets(context_id: Optional[str]) -> List[Dict[str, str]]:
    if not context_id:
        return []
    context = load_contexts().get(context_id)
    if not context:
        return []
    assets = []
    for image in context.get("images", []):
        if image.get("url"):
            assets.append({"type": "image", "url": image["url"], "caption": image.get("caption", "")})
    return assets


def _local_question_asset_url(question_id: str) -> Optional[str]:
    candidate = STATIC_QUESTION_ASSETS_DIR / f"{question_id}.jpg"
    if not candidate.exists():
        return None
    try:
        with Image.open(candidate) as img:
            width, height = img.size
        ratio = height / max(width, 1)
        if height < MIN_VALID_ASSET_HEIGHT or ratio < MIN_VALID_ASSET_RATIO:
            return None
    except Exception:
        return None
    return f"/static/question_assets/{question_id}.jpg"


def get_question_assets(question: Dict[str, Any]) -> List[Dict[str, str]]:
    assets = []
    for image in question.get("images", []):
        if image.get("url"):
            assets.append({"type": "image", "url": image["url"], "caption": image.get("caption", "")})
    if not assets and question_needs_visual_support(question):
        local_url = _local_question_asset_url(question["id"])
        if local_url:
            assets.append({"type": "image", "url": local_url, "caption": ""})
    return assets


def _render_clean_options(options: Dict[str, str]) -> str:
    lines: List[str] = []
    for key, value in options.items():
        cleaned = _join_wrapped_paragraphs(value)
        lines.append(f"{key}) {cleaned}")
    return "\n".join(lines)


def render_question(question: Dict[str, Any], sequence: int, total: int) -> str:
    return "\n\n".join(render_question_parts(question, sequence, total))


def render_question_parts(question: Dict[str, Any], sequence: int, total: int) -> List[str]:
    quality = _question_text_quality(question)
    options = question["options"]
    prompt = "/".join(options.keys())
    header = f"📝 Pregunta {sequence}/{total}\n{question['subject_label']} · Oficial {question['question_number']} · Forma {question['exam_form']}"

    if question_needs_visual_support(question):
        local_asset = _local_question_asset_url(question["id"])
        if local_asset:
            body = f"{header}\n\nResponde con {prompt}."
            return split_text_for_whatsapp(body, MAX_WHATSAPP_TEXT)

        if quality == "poor":
            body = f"{header}\n\nEsta pregunta visual no tiene una imagen validada en el banco actual. Escribe OMITIR o SALIR para continuar."
            return split_text_for_whatsapp(body, MAX_WHATSAPP_TEXT)

        stem_summary = _cleanup_common_text(" ".join(ln.strip() for ln in question.get("stem", "").split("\n") if ln.strip()))
        if len(stem_summary) > 700:
            stem_summary = stem_summary[:697].rstrip() + "..."
        body = f"{header}\n\n{stem_summary}\n\n{_render_clean_options(options)}\n\nResponde con {prompt}."
        return split_text_for_whatsapp(body, MAX_WHATSAPP_TEXT)

    stem = _join_wrapped_paragraphs(question.get("stem", ""))
    options_block = _render_clean_options(options)
    body = f"{header}\n\n{stem}\n\n{options_block}\n\nResponde con {prompt}."
    return split_text_for_whatsapp(body, MAX_WHATSAPP_TEXT)


def detect_exact_scoring(session, exam_config: Dict[str, Any], session_questions: Sequence[Any]) -> bool:
    expected_numbers = set(range(1, exam_config["total_questions"] + 1))
    selected_numbers = {int(row["question_number"]) for row in session_questions if row["question_number"] is not None}
    return selected_numbers == expected_numbers


def map_to_paes_score(table: Dict[str, Any], p_value: int) -> Optional[int]:
    key = str(p_value)
    if key in table:
        return int(table[key])
    return None


def calculate_session_scores(session_id: int) -> Dict[str, Any]:
    session = get_session(session_id)
    rows = get_session_questions(session_id)
    cfg = load_official_config().get(session["subject_code"], {})
    valid_rows = [r for r in rows if int(r["is_scored"]) == 1 and int(r["is_deleted"]) == 0]
    answered_rows = [r for r in rows if r["response_option"]]
    raw_correct_valid = sum(1 for r in valid_rows if int(r["is_correct"] or 0) == 1)
    answered_total = len(answered_rows)
    omitted_total = sum(1 for r in rows if (not r["response_option"]))
    valid_questions_total = len(valid_rows)
    score_percent = round((raw_correct_valid / valid_questions_total) * 100, 2) if valid_questions_total else 0.0

    exact_mode = "none"
    official_paes_score = None
    estimated_paes_score = None
    if cfg and cfg.get("paes_table"):
        if detect_exact_scoring(session, cfg, rows):
            exact_mode = "exact"
            official_paes_score = map_to_paes_score(cfg["paes_table"], raw_correct_valid)
        elif valid_questions_total > 0:
            exact_mode = "estimated"
            projected_p = round((raw_correct_valid / valid_questions_total) * int(cfg["valid_question_count"]))
            projected_p = max(0, min(int(cfg["valid_question_count"]), projected_p))
            estimated_paes_score = map_to_paes_score(cfg["paes_table"], projected_p)

    return {
        "raw_correct_valid": raw_correct_valid,
        "valid_questions_total": valid_questions_total,
        "answered_questions_total": answered_total,
        "omitted_questions_total": omitted_total,
        "score_percent": score_percent,
        "official_scoring_mode": exact_mode,
        "official_paes_score": official_paes_score,
        "estimated_paes_score": estimated_paes_score,
    }


def finalize_session(session_id: int, status: str = "finished", notes: Optional[str] = None) -> Dict[str, Any]:
    scores = calculate_session_scores(session_id)
    with closing(get_db()) as conn:
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, finished_at = ?, official_scoring_mode = ?, official_paes_score = ?, estimated_paes_score = ?,
                raw_correct_valid = ?, valid_questions_total = ?, answered_questions_total = ?, omitted_questions_total = ?,
                score_percent = ?, notes = COALESCE(?, notes)
            WHERE id = ?
            """,
            (
                status,
                utc_now_iso(),
                scores["official_scoring_mode"],
                scores["official_paes_score"],
                scores["estimated_paes_score"],
                scores["raw_correct_valid"],
                scores["valid_questions_total"],
                scores["answered_questions_total"],
                scores["omitted_questions_total"],
                scores["score_percent"],
                notes,
                session_id,
            ),
        )
        conn.commit()
    return scores


def advance_session(session_id: int) -> None:
    with closing(get_db()) as conn:
        conn.execute("UPDATE sessions SET current_sequence = current_sequence + 1 WHERE id = ?", (session_id,))
        conn.commit()


def answer_question(session_id: int, response_option: Optional[str]) -> Dict[str, Any]:
    current = get_current_session_question(session_id)
    if current is None:
        raise ValueError("No hay pregunta activa.")
    question = get_question_by_id(current["question_id"])
    is_correct = None
    if response_option:
        is_correct = int(response_option == question["correct_option"])
    with closing(get_db()) as conn:
        conn.execute(
            """
            UPDATE session_questions
            SET response_option = ?, is_correct = ?, answered_at = ?
            WHERE id = ?
            """,
            (response_option, is_correct, utc_now_iso(), current["id"]),
        )
        conn.commit()
    return {"question": question, "current": current, "is_correct": is_correct}



def _short_feedback_stem(question: Dict[str, Any], limit: int = 160) -> str:
    stem = _join_wrapped_paragraphs(question.get("stem", "")) or ""
    stem = _cleanup_common_text(stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    if len(stem) > limit:
        stem = stem[: limit - 3].rstrip() + "..."
    return stem


def build_report_chunks(session_id: int) -> List[str]:
    session = get_session(session_id)
    rows = get_session_questions(session_id)
    cfg = load_official_config().get(session["subject_code"], {})
    score = calculate_session_scores(session_id)

    summary_lines = [
        f"📊 Resultado · {cfg.get('label', session['subject_code'])}",
        f"Modo: {session['mode'].capitalize()}",
        f"Forma oficial: {session['exam_form'] or '-'}",
        f"Correctas válidas: {score['raw_correct_valid']}/{score['valid_questions_total']}",
        f"Respondidas: {score['answered_questions_total']} · Omitidas: {score['omitted_questions_total']}",
        f"Porcentaje válido: {score['score_percent']:.0f}%",
    ]
    if score["official_scoring_mode"] == "exact" and score["official_paes_score"] is not None:
        summary_lines.append(f"Puntaje PAES exacto: {score['official_paes_score']}")
    elif score["official_scoring_mode"] == "estimated" and score["estimated_paes_score"] is not None:
        summary_lines.append(f"Puntaje PAES proyectado: {score['estimated_paes_score']}")
    else:
        summary_lines.append("Puntaje PAES: no disponible para esta combinación de preguntas.")

    mistake_blocks: List[str] = []
    for row in rows:
        question = get_question_by_id(row["question_id"])
        response = row["response_option"] or "-"
        correct = question["correct_option"]
        if response != correct:
            status = "omitida" if not row["response_option"] else "incorrecta"
            stem = _short_feedback_stem(question)
            mistake_blocks.append(
                f"• P{row['question_number']} ({status})\n"
                f"  Tu respuesta: {response}\n"
                f"  Correcta: {correct}\n"
                f"  Enunciado: {stem}"
            )

    chunks: List[str] = ["\n".join(summary_lines)]

    if not mistake_blocks:
        chunks.append("✅ Muy bien. No tuviste preguntas incorrectas ni omitidas en esta sesión.")
        chunks.append("Escribe MENU para seguir practicando.")
        return chunks

    header = "🧠 Retroalimentación\nAquí van tus preguntas incorrectas u omitidas con la respuesta correcta:"
    current = header
    for block in mistake_blocks:
        candidate = current + "\n\n" + block
        if len(candidate) <= MAX_WHATSAPP_TEXT:
            current = candidate
        else:
            chunks.append(current)
            current = block
    if current:
        chunks.append(current)
    chunks.append("Escribe MENU para seguir practicando.")
    return chunks


def build_report(session_id: int) -> str:
    return "\n\n".join(build_report_chunks(session_id))


def build_user_progress(phone: str) -> str:
    cfg = load_official_config()
    with closing(get_db()) as conn:
        rows = conn.execute(
            """
            SELECT subject_code,
                   COUNT(*) as sessions_count,
                   AVG(score_percent) as avg_percent,
                   SUM(raw_correct_valid) as total_correct,
                   SUM(valid_questions_total) as total_valid
            FROM sessions
            WHERE phone = ? AND status = 'finished'
            GROUP BY subject_code
            ORDER BY subject_code
            """,
            (phone,),
        ).fetchall()
    if not rows:
        return "Aún no tienes sesiones terminadas. Escribe MENU para empezar a practicar."

    lines = ["📈 Tu progreso", ""]
    for row in rows:
        label = cfg.get(row["subject_code"], {}).get("label", row["subject_code"])
        avg_percent = round(float(row["avg_percent"] or 0))
        total_correct = int(row["total_correct"] or 0)
        total_valid = int(row["total_valid"] or 0)
        lines.append(f"• {label}: {row['sessions_count']} sesiones · promedio {avg_percent}% · aciertos {total_correct}/{total_valid}")
    lines.extend(["", "Escribe MENU para seguir practicando."])
    return "\n".join(lines)


def list_questions_summary(limit: int = 30) -> List[Dict[str, Any]]:
    bank = load_question_bank()
    return bank[:limit]
