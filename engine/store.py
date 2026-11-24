"""Saves cases so people can come back later, and so an accountant can pick them up.

One small database file (out/cases.db) using sqlite3, which comes with Python. Uploaded files are
kept in out/uploads/<return code>/. The out/ folder is git-ignored. Made-up data only.
"""

import json
import re
import secrets
import shutil
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "out"

# Where a sent case is. Each has a short label for the accountant and a sentence for the person.
STATUSES = {
    "new": ("New", "Your pack is waiting for an accountant."),
    "in_review": ("In review", "An accountant is looking at your pack."),
    "waiting": ("Waiting for documents", "Your accountant has asked for something more."),
    "updated": ("New documents received", "Your new documents have reached your accountant."),
    "done": ("Done", "Your accountant has finished checking your pack and will be in touch."),
}

CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I or O, which look like 1 and 0

TABLE = """
CREATE TABLE IF NOT EXISTS cases (
    code       TEXT PRIMARY KEY,   -- the return code, like KTRM-4729
    case_type  TEXT NOT NULL,
    email      TEXT,
    screen     INTEGER NOT NULL,   -- the screen the person was on
    answers    TEXT NOT NULL,      -- JSON
    extracted  TEXT NOT NULL,      -- JSON: what was read from each document
    requests   TEXT NOT NULL,      -- JSON: documents the accountant has asked for
    status     TEXT,               -- empty until the pack is sent
    pack       TEXT,               -- JSON: the handover pack as it was sent
    created    TEXT NOT NULL,
    updated    TEXT NOT NULL,
    sent       TEXT
)
"""


def connect():
    OUT_DIR.mkdir(exist_ok=True)
    db = sqlite3.connect(OUT_DIR / "cases.db")
    db.row_factory = sqlite3.Row
    db.execute(TABLE)
    return db


def now():
    return datetime.now().isoformat(timespec="seconds")


def to_json(value):
    return json.dumps(value, ensure_ascii=False, default=lambda v: v.isoformat() if isinstance(v, date) else str(v))


def normalise_code(text):
    """'ktrm 4729' and 'KTRM4729' both become 'KTRM-4729'."""
    text = re.sub(r"[^A-Za-z0-9]", "", text or "").upper()
    return f"{text[:4]}-{text[4:]}" if len(text) == 8 else text


def create(case_type):
    """Start a new case and return its return code."""
    with closing(connect()) as db, db:
        while True:
            code = "".join(secrets.choice(CODE_LETTERS) for _ in range(4)) + "-" + \
                   "".join(secrets.choice("23456789") for _ in range(4))
            if not db.execute("SELECT 1 FROM cases WHERE code = ?", (code,)).fetchone():
                break
        db.execute("INSERT INTO cases (code, case_type, screen, answers, extracted, requests, created, updated) "
                   "VALUES (?, ?, 0, '{}', '{}', '[]', ?, ?)", (code, case_type, now(), now()))
    return code


def save(code, screen, answers, extracted, email=None):
    """Save where the person is. Called on every step, so nothing is lost on refresh."""
    with closing(connect()) as db, db:
        db.execute("UPDATE cases SET screen = ?, answers = ?, extracted = ?, email = ?, updated = ? WHERE code = ?",
                   (screen, to_json(answers), to_json(extracted), email, now(), code))


def _as_dict(row):
    case = dict(row)
    for key in ("answers", "extracted", "requests", "pack"):
        case[key] = json.loads(case[key]) if case[key] else None
    return case


def load(code):
    """The saved case, or None if there is no case with that code. Dates in answers come back as text."""
    with closing(connect()) as db:
        row = db.execute("SELECT * FROM cases WHERE code = ?", (code,)).fetchone()
    return _as_dict(row) if row else None


def send(code, pack):
    """Send the pack to the accountant inbox. Sending again updates the pack that is there."""
    case = load(code)
    added = {d["id"]: d.get("added", "") for d in pack["documents"] if d["status"] != "missing"}
    requests = case["requests"]
    for request in requests:  # a request is done once the document was added after it was asked for
        if added.get(request["doc_id"], "") >= request["asked"]:
            request["done"] = True
    status = "updated" if case["status"] else "new"
    with closing(connect()) as db, db:
        db.execute("UPDATE cases SET pack = ?, requests = ?, status = ?, sent = ?, updated = ? WHERE code = ?",
                   (to_json(pack), to_json(requests), status, now(), now(), code))


def sent_cases():
    """Every case that has been sent, newest first. This is the accountant's inbox."""
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM cases WHERE status IS NOT NULL ORDER BY sent DESC").fetchall()
    return [_as_dict(row) for row in rows]


def set_status(code, status):
    with closing(connect()) as db, db:
        db.execute("UPDATE cases SET status = ?, updated = ? WHERE code = ?", (status, now(), code))


def ask_for(code, doc_id, label, message):
    """The accountant asks the person for a document. The person sees this when they come back."""
    requests = load(code)["requests"]
    requests.append({"doc_id": doc_id, "label": label, "message": message.strip(), "asked": now(), "done": False})
    with closing(connect()) as db, db:
        db.execute("UPDATE cases SET requests = ?, status = 'waiting', updated = ? WHERE code = ?",
                   (to_json(requests), now(), code))


def open_requests(code):
    case = load(code)
    return [r for r in case["requests"] if not r["done"]] if case else []


# ---------- uploaded files ----------

def uploads_dir(code):
    return OUT_DIR / "uploads" / code


def save_file(code, doc_id, file_name, data):
    """Keep an uploaded file. Returns the name it is stored under."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", Path(file_name).name)[-80:]
    stored = f"{doc_id}__{safe}"
    folder = uploads_dir(code)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / stored).write_bytes(data)
    return stored


def read_file(code, stored):
    """The bytes of a stored file, or None if it is not there."""
    path = uploads_dir(code) / Path(stored).name
    return path.read_bytes() if path.is_file() else None


def delete_file(code, stored):
    (uploads_dir(code) / Path(stored).name).unlink(missing_ok=True)


def delete(code):
    """Remove a case and its uploaded files for good."""
    with closing(connect()) as db, db:
        db.execute("DELETE FROM cases WHERE code = ?", (code,))
    shutil.rmtree(uploads_dir(code), ignore_errors=True)
