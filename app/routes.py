import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from app import db as D
from app.llm import ask_model
from app.prompts import build_system, trim_history
from app.schemas import ChatOut, Correction, Explication, Exercices

router = APIRouter()
PUB = ("id", "email", "nom", "l1", "niveau", "objectif", "avatar")
TITRES = {"chat": "Conversation", "explain": "Explication", "exercise": "Exercices"}

def pub(u): return {k: u[k] for k in PUB}

def current_user(request: Request):
    t = request.cookies.get("token")
    u = D.user_by_token(t)
    if not u:
        print(f"401 {request.method} {request.url.path} | cookie {'présent' if t else 'ABSENT'}")
        raise HTTPException(401, "Non connecté")
    return u

def _open(resp, uid):
    resp.set_cookie("token", D.new_session(uid), httponly=True, samesite="lax", max_age=30 * 86400)  # secure=True en HTTPS
    return pub(D.user_by_id(uid))

class Cred(BaseModel):
    email: str
    password: str
    nom: str = ""

@router.post("/api/register")
def register(c: Cred, resp: Response):
    email = c.email.strip().lower()
    if "@" not in email or len(c.password) < 8:
        raise HTTPException(400, "E-mail invalide ou mot de passe trop court (8 caractères minimum).")
    try: uid = D.create_user(email, c.password, c.nom.strip())
    except sqlite3.IntegrityError: raise HTTPException(409, "Cet e-mail est déjà utilisé.")
    return _open(resp, uid)

@router.post("/api/login")
def login(c: Cred, resp: Response):
    u = D.user_by_email(c.email.strip().lower())
    if not u or not D.check_pwd(c.password, u["pwd"]):
        raise HTTPException(400, "E-mail ou mot de passe incorrect.")
    return _open(resp, u["id"])

@router.post("/api/logout")
def logout(request: Request, resp: Response):
    D.end_session(request.cookies.get("token", "")); resp.delete_cookie("token"); return {"ok": True}

@router.get("/api/me")
def me(u=Depends(current_user)): return pub(u)

class Prefs(BaseModel):
    l1: str = ""
    niveau: str = "A1"
    objectif: str = ""
    avatar: bool = False

@router.put("/api/prefs")
def prefs(p: Prefs, u=Depends(current_user)):
    D.set_prefs(u["id"], p.l1[:40], p.niveau if p.niveau in ("A1","A2","B1","B2","C1","C2") else "A1", p.objectif[:200], p.avatar)
    return pub(D.user_by_id(u["id"]))

class NewConv(BaseModel):
    mode: str
    theme: str = ""
    niveau: str = "A1"

@router.post("/api/conversations")
def new_conv(c: NewConv, u=Depends(current_user)):
    if c.mode not in TITRES: raise HTTPException(400, "Mode inconnu")
    theme = c.theme.strip()[:200]
    return {"id": D.create_conv(u["id"], c.mode, theme, c.niveau, TITRES[c.mode] + (" : " + theme if theme else ""))}

@router.get("/api/conversations")
def convs(u=Depends(current_user)): return D.list_convs(u["id"])

def own(cid, u):
    c = D.get_conv(cid, u["id"])
    if not c: raise HTTPException(404, "Conversation introuvable")
    return c

@router.get("/api/conversations/{cid}")
def conv(cid: int, u=Depends(current_user)):
    c = own(cid, u); return {**c, "messages": D.get_msgs(cid)}

@router.delete("/api/conversations/{cid}")
def delete(cid: int, u=Depends(current_user)):
    D.del_conv(cid, u["id"]); return {"ok": True}

class Msg(BaseModel):
    text: str = ""

def _contexte(c, u):
    return c["theme"] + (f" (objectif de l'apprenant : {u['objectif']})" if u["objectif"] else "") if c["mode"] == "chat" else ""

@router.post("/api/conversations/{cid}/message")
async def message(cid: int, m: Msg, u=Depends(current_user)):
    c, text, mode = own(cid, u), m.text.strip()[:1000], None
    mode = c["mode"]
    if mode == "explain" and not text: raise HTTPException(400, "Indiquez une notion.")
    system = build_system(mode, c["niveau"], _contexte(c, u) or "la vie quotidienne", u["l1"])
    hist = D.history(cid) if mode == "chat" else []
    if text: D.add_msg(cid, "user", "user", {"text": text})
    if mode == "chat":
        msgs = trim_history(hist) + [{"role": "user", "content": text or "Commence la conversation : présente-toi en une phrase et pose une première question."}]
        out, kind = await ask_model(system, msgs, ChatOut), "chat"
    elif mode == "explain":
        out, kind = await ask_model(system, [{"role": "user", "content": text}], Explication), "explain"
    else:
        cibles = [] if text else D.top_erreurs(u["id"])
        ask = f"Notion : {text or 'libre, adaptée au niveau'}. Nombre : 4. Erreurs fréquentes à cibler : {cibles or 'aucune'}."
        out, kind = await ask_model(system, [{"role": "user", "content": ask}], Exercices), "exercises"
    data = out.model_dump()
    D.add_msg(cid, "tutor", kind, data)
    return {"kind": kind, "data": data}

@router.post("/api/conversations/{cid}/correct")
async def correct(cid: int, m: Msg, u=Depends(current_user)):
    c = own(cid, u)
    k = await ask_model(build_system("correct", c["niveau"], l1=u["l1"]), [{"role": "user", "content": m.text[:500]}], Correction)
    D.add_msg(cid, "tutor", "correction", k.model_dump()); D.log_errors(u["id"], k.erreurs)
    return k.model_dump()