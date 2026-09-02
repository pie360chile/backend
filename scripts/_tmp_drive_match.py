import re, unicodedata, requests
from collections import Counter
from sqlalchemy import or_
from app.backend.db.database import SessionLocal
from app.backend.db.models import (
    CourseModel, DocumentModel, StudentAcademicInfoModel,
    StudentModel, StudentPersonalInfoModel, FolderModel,
)
from app.backend.utils.customer_drive_config import load_customer_drive_config

FAMILY_PARENTS = {
    "1k2MwsdX2-MjNwjDASX9mwb1SsgM5WC9O": 3,
    "1rs92LrZnN5FS1nNiXOTpKOruCTp_WLxX": 1,
    "1g7lHmmwxLOm_qYSeg1vo3YoQ-VoYl99b": 2,
    "11URPFs25izdElEDDQKrAxPm69QtVxqkd": 5,
    "1Uk6DIBmfXSXAq0FppQ4jaCZoQ7W-2wNS": 4,
}
PSYCHO_PARENTS = {
    "1Obr5n9NVaUdTB1wZvPN9S3tHV8yi_wfJ": 1,
    "1MJFngmDX3-skxuMDnlbgxWE27oQMW6cj": 2,
    "1D6JeT9sy837J2iErJ8LeExL8ys0CDUF1": 3,
    "1fD1UvReuWxj8OyX7rtjVb_C-Ud_8SRJ3": 5,
    "1f5p6jgwks8-VRWGDdQ5O2Aq3MQOZIeHr": 4,
}
ALL_PARENTS = {**FAMILY_PARENTS, **PSYCHO_PARENTS}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def toks(s):
    return set(t for t in norm(s).split() if t)

def extract_person(name):
    base = re.sub(r"\.(docx|pdf|doc)$", "", name, flags=re.I)
    m = re.match(r"^InformeFamilia_[^-]+-(.+)$", base)
    if m:
        return m.group(1).strip()
    m = re.search(r"Informe(?:\s+a\s+la\s+familia|\s+psicopedag\w+).*$", base, re.I)
    if m:
        left = base[:m.start()].strip(" -_")
        left = re.sub(r"^(?:PK|K)\s*", "", left)
        left = re.sub(r"^\d+[°º]?\s*[A-Za-zÁÉÍÓÚáéíóú]?\s*", "", left)
        left = re.sub(r"\s+B\d+\s*$", "", left)
        return left.strip(" -_")
    person = re.sub(r"^Informe(?:Familia|Psico\w*)[_\s-]*", "", base, flags=re.I)
    person = re.sub(r"^[^-]+-", person, person, count=1) if "-" in person[:20] else person
    return person.strip(" -_")

db = SessionLocal()
print("DOCS", [(d.id, d.document) for d in db.query(DocumentModel).filter(DocumentModel.id.in_([7,27])).all()])

cfg = load_customer_drive_config(db, 2)
o = cfg.oauth_info
tok = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": o["client_id"], "client_secret": o["client_secret"],
    "refresh_token": o["refresh_token"], "grant_type": "refresh_token",
}, timeout=30)
tok.raise_for_status()
h = {"Authorization": "Bearer " + tok.json()["access_token"]}
res = requests.get("https://www.googleapis.com/drive/v3/files", headers=h, params={
    "q": "trashed = false", "spaces": "drive",
    "fields": "files(id,name,mimeType,size,parents)", "pageSize": 1000,
}, timeout=30)
res.raise_for_status()
drive_files = [f for f in res.json().get("files", []) if f.get("mimeType") != "application/vnd.google-apps.folder"]

legacy = []
for f in drive_files:
    parent = (f.get("parents") or [None])[0]
    if parent not in ALL_PARENTS:
        continue
    school_id = ALL_PARENTS[parent]
    kind = "familia" if parent in FAMILY_PARENTS else "psico"
    person = extract_person(f["name"])
    legacy.append({
        "id": f["id"], "name": f["name"], "school_id": school_id,
        "kind": kind, "doc_id": 7 if kind == "familia" else 27,
        "person": person, "norm": norm(person), "toks": toks(person), "size": f.get("size"),
    })
print("LEGACY", len(legacy), dict(Counter(x["kind"] for x in legacy)))
print("BY_SCHOOL", dict(Counter((x["school_id"], x["kind"]) for x in legacy)))

# bulk students customer 2 schools 1-5
st_rows = db.query(StudentModel).filter(
    StudentModel.deleted_status_id == 0,
    StudentModel.school_id.in_([1,2,3,4,5]),
).all()
st_ids = [s.id for s in st_rows]
personal = {
    p.student_id: p
    for p in db.query(StudentPersonalInfoModel)
    .filter(StudentPersonalInfoModel.student_id.in_(st_ids))
    .order_by(StudentPersonalInfoModel.id.asc())
    .all()
}
academic = {}
for a in db.query(StudentAcademicInfoModel).filter(StudentAcademicInfoModel.student_id.in_(st_ids)).order_by(StudentAcademicInfoModel.id.asc()).all():
    academic[a.student_id] = a
courses = {c.id: c for c in db.query(CourseModel).all()}

students = []
for s in st_rows:
    p = personal.get(s.id)
    a = academic.get(s.id)
    c = courses.get(a.course_id) if a and a.course_id else None
    name = " ".join(filter(None, [
        getattr(p, "names", None) if p else None,
        getattr(p, "father_lastname", None) if p else None,
        getattr(p, "mother_lastname", None) if p else None,
    ]))
    students.append({
        "id": s.id, "school_id": s.school_id,
        "course_id": a.course_id if a else None,
        "course_name": c.course_name if c else None,
        "name": name, "norm": norm(name), "toks": toks(name),
    })
print("STUDENTS", len(students), "named", sum(1 for s in students if s["name"]))

by_school = defaultdict = {}
from collections import defaultdict
by_school = defaultdict(list)
for s in students:
    by_school[s["school_id"]].append(s)

existing = set(
    (f.student_id, f.document_id)
    for f in db.query(FolderModel.student_id, FolderModel.document_id)
    .filter(
        FolderModel.student_id.in_(st_ids),
        FolderModel.document_id.in_([7,27]),
        FolderModel.file.isnot(None),
        FolderModel.deleted_date.is_(None),
    ).all()
)

exact=amb=unm=already=0
unm_ex=[]; amb_ex=[]; ok_ex=[]
for item in legacy:
    scored=[]
    for s in by_school[item["school_id"]]:
        if not s["norm"]:
            continue
        if s["norm"] == item["norm"]:
            score=100.0
        else:
            inter=len(s["toks"] & item["toks"])
            if inter < 2:
                continue
            score = 100.0 * inter / max(len(s["toks"] | item["toks"]), 1)
            if score < 55:
                continue
        scored.append((score,s))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        unm += 1
        if len(unm_ex) < 15:
            unm_ex.append((item["kind"], item["school_id"], item["name"], item["person"]))
        continue
    if len(scored) > 1 and (scored[0][0] < 100) and (scored[0][0] - scored[1][0] < 8):
        amb += 1
        if len(amb_ex) < 8:
            amb_ex.append((item["name"], [(t[1]["id"], t[1]["name"], round(t[0],1)) for t in scored[:3]]))
        continue
    st = scored[0][1]
    exact += 1
    if (st["id"], item["doc_id"]) in existing:
        already += 1
    if len(ok_ex) < 10:
        ok_ex.append((item["kind"], item["name"], st["id"], st["name"], round(scored[0][0],1), (st["id"], item["doc_id"]) in existing))

print("RESULT exact/amb/unm/already", exact, amb, unm, already)
print("OK")
for e in ok_ex: print(e)
print("AMB")
for e in amb_ex: print(e)
print("UNM")
for e in unm_ex: print(e)
db.close()
