import re, unicodedata, requests
from collections import Counter, defaultdict
from app.backend.db.database import SessionLocal
from app.backend.db.models import StudentModel, StudentPersonalInfoModel, FolderModel
from app.backend.utils.customer_drive_config import load_customer_drive_config

FAMILY_PARENTS = {"1k2MwsdX2-MjNwjDASX9mwb1SsgM5WC9O":3,"1rs92LrZnN5FS1nNiXOTpKOruCTp_WLxX":1,"1g7lHmmwxLOm_qYSeg1vo3YoQ-VoYl99b":2,"11URPFs25izdElEDDQKrAxPm69QtVxqkd":5,"1Uk6DIBmfXSXAq0FppQ4jaCZoQ7W-2wNS":4}
PSYCHO_PARENTS = {"1Obr5n9NVaUdTB1wZvPN9S3tHV8yi_wfJ":1,"1MJFngmDX3-skxuMDnlbgxWE27oQMW6cj":2,"1D6JeT9sy837J2iErJ8LeExL8ys0CDUF1":3,"1fD1UvReuWxj8OyX7rtjVb_C-Ud_8SRJ3":5,"1f5p6jgwks8-VRWGDdQ5O2Aq3MQOZIeHr":4}
ALL={**FAMILY_PARENTS,**PSYCHO_PARENTS}

def norm(s):
    s=unicodedata.normalize("NFKD", s or "")
    s="".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+"," ", re.sub(r"[^a-z0-9\s]"," ",s)).strip()

def toks(s):
    stop={"de","del","la","las","los","y","b","a","medio","basica","pk","k"}
    return [t for t in norm(s).split() if t and t not in stop and not t.isdigit()]

def extract_person(name):
    base=re.sub(r"\.(docx|pdf|doc)$","", name, flags=re.I)
    m=re.match(r"^InformeFamilia_.+?-(.+)$", base)
    if m: return m.group(1).strip()
    m=re.match(r"^InformeFamilia_.+?_(.+)$", base)
    if m and "medio" in base.lower():
        return re.sub(r"\s*\(\d+\)\s*$","", m.group(1)).strip()
    m=re.search(r"-\s*Informe.*$", base, re.I)
    if m:
        left=base[:m.start()].strip(" -_")
        left=re.sub(r"^(?:PK|K|Prekinder|Kinder)?[^\wÁÉÍÓÚáéíóúÑñ]*","", left, flags=re.I)
        left=re.sub(r"^\d+[°ºo]?\s*[A-Za-zÁÉÍÓÚáéíóú]?\s*","", left)
        left=re.sub(r"\s+B\d+\s*$","", left)
        return left.strip(" -_")
    if "_" in base and " " not in base:
        return base.replace("_"," ")
    return re.sub(r"^Informe(?:Familia|Psico\w*)[_\s-]*","", base, flags=re.I).strip(" -_")

def score_name(ft, st):
    if not ft or not st: return 0
    if ft[0] not in st: return 0
    if set(ft).issubset(set(st)):
        return 100 if ft==st else 90
    if len(ft)>=2 and ft[0] in st and ft[-1] in st: return 80
    return 0

db=SessionLocal(); cfg=load_customer_drive_config(db,2); o=cfg.oauth_info
tok=requests.post("https://oauth2.googleapis.com/token",data={"client_id":o["client_id"],"client_secret":o["client_secret"],"refresh_token":o["refresh_token"],"grant_type":"refresh_token"},timeout=30); tok.raise_for_status()
h={"Authorization":"Bearer "+tok.json()["access_token"]}
res=requests.get("https://www.googleapis.com/drive/v3/files",headers=h,params={"q":"trashed = false","spaces":"drive","fields":"files(id,name,mimeType,parents)","pageSize":1000},timeout=30); res.raise_for_status()
legacy=[]
for f in res.json().get("files",[]):
    if f.get("mimeType")=="application/vnd.google-apps.folder": continue
    p=(f.get("parents") or [None])[0]
    if p not in ALL: continue
    kind="familia" if p in FAMILY_PARENTS else "psico"
    person=extract_person(f["name"])
    legacy.append({"name":f["name"],"school_id":ALL[p],"kind":kind,"doc_id":7 if kind=="familia" else 27,"person":person,"toks":toks(person),"id":f["id"]})

st_rows=db.query(StudentModel).filter(StudentModel.deleted_status_id==0,StudentModel.school_id.in_([1,2,3,4,5])).all()
st_ids=[s.id for s in st_rows]
personal={p.student_id:p for p in db.query(StudentPersonalInfoModel).filter(StudentPersonalInfoModel.student_id.in_(st_ids)).order_by(StudentPersonalInfoModel.id.asc())}
students=[]
for s in st_rows:
    p=personal.get(s.id)
    name=" ".join(filter(None,[getattr(p,"names",None) if p else None, getattr(p,"father_lastname",None) if p else None, getattr(p,"mother_lastname",None) if p else None]))
    students.append({"id":s.id,"school_id":s.school_id,"name":name,"toks":toks(name)})
by=defaultdict(list)
for s in students: by[s["school_id"]].append(s)
existing=set((a,b) for a,b in db.query(FolderModel.student_id,FolderModel.document_id).filter(FolderModel.student_id.in_(st_ids),FolderModel.document_id.in_([7,27]),FolderModel.file.isnot(None),FolderModel.deleted_date.is_(None)))

exact=amb=unm=already=0
byk=Counter(); unmk=Counter()
for item in legacy:
    scored=[]
    for s in by[item["school_id"]]:
        sc=score_name(item["toks"], s["toks"])
        if sc>=80: scored.append((sc,s))
    scored.sort(key=lambda x:-x[0])
    if not scored:
        unm+=1; unmk[item["kind"]]+=1; continue
    top=[x for x in scored if x[0]==scored[0][0]]
    uniq={s["id"]:(sc,s) for sc,s in top}
    if len(uniq)>1:
        amb+=1; continue
    sc,st=list(uniq.values())[0]
    exact+=1; byk[item["kind"]]+=1
    if (st["id"], item["doc_id"]) in existing: already+=1
print("LEGACY", len(legacy), dict(Counter(x["kind"] for x in legacy)))
print("RESULT exact/amb/unm/already", exact,amb,unm,already)
print("exact_by", dict(byk), "unm_by", dict(unmk))
print("sample_unm")
c=0
for item in legacy:
    scored=[(score_name(item["toks"],s["toks"]),s) for s in by[item["school_id"]] if score_name(item["toks"],s["toks"])>=80]
    if scored: continue
    print(item["kind"], item["school_id"], item["name"], "=>", item["person"], item["toks"])
    c+=1
    if c>=15: break
db.close()
