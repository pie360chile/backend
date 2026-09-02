import re, unicodedata, requests
from collections import Counter, defaultdict
from app.backend.db.database import SessionLocal
from app.backend.db.models import (
    CourseModel, StudentAcademicInfoModel, StudentModel, StudentPersonalInfoModel, FolderModel,
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
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def toks(s):
    stop={"de","del","la","las","los","y"}
    return [t for t in norm(s).split() if t and t not in stop]

def extract_person(name):
    base = re.sub(r"\.(docx|pdf|doc)$", "", name, flags=re.I)
    m = re.match(r"^InformeFamilia_[^-]+-(.+)$", base)
    if m: return m.group(1).strip()
    m = re.search(r"-\s*Informe(?:\s+a\s+la\s+familia|\s+psicopedag\w*).*$", base, re.I)
    if m:
        left = base[:m.start()].strip(" -_")
        left = re.sub(r"^(?:PK|K)\s*", "", left)
        left = re.sub(r"^\d+[°º]?\s*[A-Za-zÁÉÍÓÚáéíóú]?\s*", "", left)
        left = re.sub(r"\s+B\d+\s*$", "", left)
        return left.strip(" -_")
    if "_" in base and " " not in base:
        return base.replace("_", " ")
    person = re.sub(r"^Informe(?:Familia|Psico\w*)[_\s-]*", "", base, flags=re.I)
    return person.strip(" -_")

def score_name(file_toks, student_toks):
    if not file_toks or not student_toks:
        return 0
    # require first token present
    if file_toks[0] not in student_toks:
        return 0
    # all file tokens must appear in student (Drive usually has fewer names)
    if not set(file_toks).issubset(set(student_toks)):
        # allow missing middle names if first+last match
        if len(file_toks) >= 2 and file_toks[0] in student_toks and file_toks[-1] in student_toks:
            return 80
        return 0
    if file_toks == student_toks:
        return 100
    if len(file_toks) >= 2:
        return 90
    return 50

db = SessionLocal()
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

legacy=[]
for f in res.json().get("files", []):
    if f.get("mimeType") == "application/vnd.google-apps.folder":
        continue
    parent=(f.get("parents") or [None])[0]
    if parent not in ALL_PARENTS: continue
    kind="familia" if parent in FAMILY_PARENTS else "psico"
    person=extract_person(f["name"])
    legacy.append({
        "id":f["id"],"name":f["name"],"school_id":ALL_PARENTS[parent],
        "kind":kind,"doc_id":7 if kind=="familia" else 27,
        "person":person,"toks":toks(person),
    })

st_rows=db.query(StudentModel).filter(StudentModel.deleted_status_id==0, StudentModel.school_id.in_([1,2,3,4,5])).all()
st_ids=[s.id for s in st_rows]
personal={}
for p in db.query(StudentPersonalInfoModel).filter(StudentPersonalInfoModel.student_id.in_(st_ids)).order_by(StudentPersonalInfoModel.id.asc()):
    personal[p.student_id]=p
students=[]
for s in st_rows:
    p=personal.get(s.id)
    name=" ".join(filter(None,[getattr(p,"names",None) if p else None, getattr(p,"father_lastname",None) if p else None, getattr(p,"mother_lastname",None) if p else None]))
    students.append({"id":s.id,"school_id":s.school_id,"name":name,"toks":toks(name)})
by_school=defaultdict(list)
for s in students: by_school[s["school_id"]].append(s)

existing=set((a,b) for a,b in db.query(FolderModel.student_id, FolderModel.document_id).filter(
    FolderModel.student_id.in_(st_ids), FolderModel.document_id.in_([7,27]),
    FolderModel.file.isnot(None), FolderModel.deleted_date.is_(None)).all())

exact=amb=unm=already=0
# also try cross-school if school-scoped fails
cross=0
unm_ex=[]; amb_ex=[]; ok_ex=[]
for item in legacy:
    scored=[]
    for s in by_school[item["school_id"]]:
        sc=score_name(item["toks"], s["toks"])
        if sc>=80: scored.append((sc,s,"school"))
    if not scored:
        for s in students:
            if s["school_id"]==item["school_id"]: continue
            sc=score_name(item["toks"], s["toks"])
            if sc>=90: scored.append((sc,s,"cross"))
    scored.sort(key=lambda x: (-x[0], x[2]!="school"))
    if not scored:
        unm+=1
        if len(unm_ex)<12: unm_ex.append((item["kind"],item["school_id"],item["name"],item["person"],item["toks"]))
        continue
    top=[x for x in scored if x[0]==scored[0][0] and x[2]==scored[0][2]]
    # unique by student id
    uniq={}
    for sc,s,src in top: uniq[s["id"]]=(sc,s,src)
    top=list(uniq.values())
    if len(top)>1:
        amb+=1
        if len(amb_ex)<8: amb_ex.append((item["name"], [(t[1]["id"],t[1]["name"],t[1]["school_id"],t[0],t[2]) for t in top[:4]]))
        continue
    sc,st,src=top[0]
    exact+=1
    if src=="cross": cross+=1
    if (st["id"], item["doc_id"]) in existing: already+=1
    if len(ok_ex)<12: ok_ex.append((item["kind"], item["name"], st["id"], st["name"], st["school_id"], item["school_id"], sc, src, (st["id"], item["doc_id"]) in existing))

print("LEGACY", len(legacy), dict(Counter(x["kind"] for x in legacy)))
print("RESULT exact/amb/unm/already/cross", exact, amb, unm, already, cross)
print("OK"); [print(e) for e in ok_ex]
print("AMB"); [print(e) for e in amb_ex]
print("UNM"); [print(e) for e in unm_ex]

# probe a few unmatched names in DB
print("PROBE")
for q in ["gabriela salinas","matias mena","sebastian rivas","austin martinez"]:
    qt=toks(q)
    hits=[]
    for s in students:
        if score_name(qt,s["toks"])>=80:
            hits.append((s["id"],s["name"],s["school_id"]))
    print(q, hits[:5], "n=",len(hits))
db.close()
