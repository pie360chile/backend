"""Probe: chat Informe a la Familia for Isabella Diaz."""
from __future__ import annotations

import json
import re

from app.backend.classes.agents_chat_class import AgentsChatClass
from app.backend.db.database import get_db
from app.backend.utils.agents_mcp_fields import (
    extract_fields_from_reply,
    is_content_too_thin,
    narrative_fields_filled,
)

db = next(get_db())
chat = AgentsChatClass(db, customer_id=2, school_id=None, user_id=1)
agent_id = "dfcb94838e3f40a48a207ba1ef4ed9d8"
msg = "haz el informe de isabella diaz"

reply = ""
raw_for_fields = ""
warning = None
files = []
for ev in chat.stream_chat(agent_id, msg, history=[]):
    t = ev.get("type")
    if t == "step":
        print("STEP:", ev.get("message"))
    elif t == "text_delta":
        delta = ev.get("delta") or ""
        reply += delta
        raw_for_fields += delta
    elif t == "error":
        print("ERROR:", ev.get("message"))
    elif t == "done":
        data = ev.get("data") or {}
        reply = data.get("reply") or reply
        warning = data.get("warning")
        files = data.get("responseFiles") or []

fields = extract_fields_from_reply(raw_for_fields)
filled, total = narrative_fields_filled(fields)
print("\n=== SUMMARY ===")
print("warning:", warning)
print("files:", len(files))
print("narrative filled/total:", filled, "/", total)
print("too_thin:", is_content_too_thin(fields))
print("reply_len:", len(reply))

NARR = [
    "diagnostic",
    "applied_instruments",
    "supports",
    "agreements",
    "collaborative_work",
    "enter_evaluation",
    "revaluation",
    "pedagogical_field_1",
    "pedagogical_field_2",
    "social_field_1",
    "social_field_2",
]
print("\n=== NARRATIVE FIELD LENGTHS ===")
if fields:
    for k in NARR:
        v = str(fields.get(k) or "").strip()
        print(f"{k}: {len(v)} chars | {v[:180]!r}{'…' if len(v) > 180 else ''}")
else:
    print("NO FIELDS PARSED")
    print(raw_for_fields[:2000])

print("\n=== CHAT REPLY (visible) ===")
print(reply[:2500])
