import csv, re, unicodedata, requests
from collections import defaultdict
from pathlib import Path
from app.backend.db.database import SessionLocal
from app.backend.db.models import StudentModel, StudentPersonalInfoModel
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
ALL = {**FAMILY_PARENTS, **PSYCHO_PARENTS}
SCHOOL_NAMES = {
    1: "Liceo Mixto Los Andes Basica 1",
    2: "Liceo Mixto Bicentenario Los Andes Basica 2",
    3: "Liceo Mixto Bicentenario Los Andes Media",
    4: "Liceo Particular Mixto San Felipe Basica",
    5: "Liceo Particular Mixto San Felipe Media",
}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", s)).strip()

def toks(s):
    stop = {"de", "del", "la", "las", "los", "y", "b", "a", "medio", "basica", "pk", "k", "informe", "familia", "b1", "b2"}
    return [t for t in norm(s).split() if t and t not in stop and not t.isdigit()]

def extract_person(name):
    base = re.sub(r"\.(docx|pdf|doc)$", "", name, flags=re.I)
    m = re.match(r"^InformeFamilia_.+?-(.+)$", base)
    if m:
        return m.group(1).strip()
    m = re.match(r"^InformeFamilia_.+?_(.+)$", base)
    if m and "medio" in base.lower():
        return re.sub(r"\s*\(\d+\)\s*$", "", m.group(1)).strip()
    m = re.search(r"-\s*Informe.*$", base, re.I)
    if m:
        left = base[:m.start()].strip(" -_")
        left = re.sub(r"^(?:PK|K|Prekinder|Kinder)?[^\wÁÉÍÓÚáéíóúÑñ]*", "", left, flags=re.I)
        left = re.sub(r"^\d+[°ºo]?\s*[A-Za-zÁÉÍÓÚáéíóú]?\s*", "", left)
        left = re.sub(r"\s+B\d+\s*$", "", left)
        return left.strip(" -_")
    # "6A Nombre B1 informe familia 2026"
    m = re.match(r"^(?:PK|K)?\s*\d*[°ºo]?\s*[A-Za-zÁÉÍÓÚáéíóú]?\s*(.+?)\s+B\d+\s+informe.*$", base, re.I)
    if m:
        return m.group(1).strip()
    if "_" in base and " " not in base:
        return base.replace("_", " ")
    return re.sub(r"^Informe(?:Familia|Psico\w*)[_\s-]*", "", base, flags=re.I).strip(" -_")

def score_name(ft, st):
    if not ft or not st:
        return 0
    if ft[0] not in st:
        return 0
    if set(ft).issubset(set(st)):
        return 100 if ft == st else 90
    if len(ft) >= 2 and ft[0] in st and ft[-1] in st:
        return 80
    return 0

db = SessionLocal()
cfg = load_customer_drive_config(db, 2)
o = cfg.oauth_info
tok = requests.post(
    "https://oauth2.googleapis.com/token",
    data={
        "client_id": o["client_id"],
        "client_secret": o["client_secret"],
        "refresh_token": o["refresh_token"],
        "grant_type": "refresh_token",
    },
    timeout=30,
)
tok.raise_for_status()
h = {"Authorization": "Bearer " + tok.json()["access_token"]}
res = requests.get(
    "https://www.googleapis.com/drive/v3/files",
    headers=h,
    params={
        "q": "trashed = false",
        "spaces": "drive",
        "fields": "files(id,name,mimeType,parents,webViewLink)",
        "pageSize": 1000,
    },
    timeout=30,
)
res.raise_for_status()

legacy = []
for f in res.json().get("files", []):
    if f.get("mimeType") == "application/vnd.google-apps.folder":
        continue
    parent = (f.get("parents") or [None])[0]
    if parent not in ALL:
        continue
    kind = "familia" if parent in FAMILY_PARENTS else "psico"
    person = extract_person(f["name"])
    legacy.append(
        {
            "drive_file_id": f["id"],
            "archivo": f["name"],
            "link": f.get("webViewLink") or "",
            "school_id": ALL[parent],
            "liceo": SCHOOL_NAMES.get(ALL[parent], str(ALL[parent])),
            "tipo": "Informe a la Familia" if kind == "familia" else "Informe Psicopedagogico",
            "document_id": 7 if kind == "familia" else 27,
            "nombre_extraido": person,
            "toks": toks(person),
        }
    )

st_rows = (
    db.query(StudentModel)
    .filter(StudentModel.deleted_status_id == 0, StudentModel.school_id.in_([1, 2, 3, 4, 5]))
    .all()
)
st_ids = [s.id for s in st_rows]
personal = {
    p.student_id: p
    for p in db.query(StudentPersonalInfoModel)
    .filter(StudentPersonalInfoModel.student_id.in_(st_ids))
    .order_by(StudentPersonalInfoModel.id.asc())
}
students = []
for s in st_rows:
    p = personal.get(s.id)
    name = " ".join(
        filter(
            None,
            [
                getattr(p, "names", None) if p else None,
                getattr(p, "father_lastname", None) if p else None,
                getattr(p, "mother_lastname", None) if p else None,
            ],
        )
    )
    students.append({"id": s.id, "school_id": s.school_id, "name": name, "toks": toks(name)})
by = defaultdict(list)
for s in students:
    by[s["school_id"]].append(s)

ok_rows, amb_rows, unm_rows = [], [], []
for item in legacy:
    scored = []
    for s in by[item["school_id"]]:
        sc = score_name(item["toks"], s["toks"])
        if sc >= 80:
            scored.append((sc, s))
    scored.sort(key=lambda x: -x[0])
    base = {
        "tipo_informe": item["tipo"],
        "document_id": item["document_id"],
        "school_id": item["school_id"],
        "liceo": item["liceo"],
        "archivo_drive": item["archivo"],
        "nombre_extraido": item["nombre_extraido"],
        "drive_file_id": item["drive_file_id"],
        "link_drive": item["link"],
    }
    if not scored:
        unm_rows.append({**base, "motivo": "sin_match"})
        continue
    top_score = scored[0][0]
    top = [x for x in scored if x[0] == top_score]
    uniq = {s["id"]: (sc, s) for sc, s in top}
    if len(uniq) > 1:
        cand = "; ".join(f"{s['id']}|{s['name']}|score={sc}" for sc, s in uniq.values())
        amb_rows.append({**base, "motivo": "ambiguo", "candidatos": cand})
        continue
    sc, st = list(uniq.values())[0]
    ok_rows.append(
        {
            **base,
            "student_id": st["id"],
            "alumno_pie360": st["name"],
            "score": sc,
            "estado": "listo_para_importar",
        }
    )

out = Path("scripts/output")
out.mkdir(parents=True, exist_ok=True)

def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

write_csv(
    out / "import_ok.csv",
    ok_rows,
    [
        "estado",
        "tipo_informe",
        "document_id",
        "school_id",
        "liceo",
        "archivo_drive",
        "nombre_extraido",
        "student_id",
        "alumno_pie360",
        "score",
        "drive_file_id",
        "link_drive",
    ],
)
write_csv(
    out / "import_ambiguous.csv",
    amb_rows,
    [
        "motivo",
        "tipo_informe",
        "document_id",
        "school_id",
        "liceo",
        "archivo_drive",
        "nombre_extraido",
        "candidatos",
        "drive_file_id",
        "link_drive",
    ],
)
write_csv(
    out / "import_unmatched.csv",
    unm_rows,
    [
        "motivo",
        "tipo_informe",
        "document_id",
        "school_id",
        "liceo",
        "archivo_drive",
        "nombre_extraido",
        "drive_file_id",
        "link_drive",
    ],
)

print("OK", len(ok_rows))
print("AMB", len(amb_rows))
print("UNM", len(unm_rows))
print("PATHS")
print((out / "import_unmatched.csv").resolve())
print((out / "import_ambiguous.csv").resolve())
print((out / "import_ok.csv").resolve())
db.close()
