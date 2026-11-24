from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.llm import ask, ask_model
from app.prompts import build_system, trim_history
from app.schemas import ChatOut,Correction,Explication,Exercices,Bilan


import os, tempfile
import mlx_whisper
from fastapi import File, UploadFile
from starlette.concurrency import run_in_threadpool

import subprocess, sys
from fastapi import Response

from app.db import log_correction, top_erreurs, taux_erreur, save_bilan, dernier_resume

app = FastAPI(title="Tuteur de français")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/test-llm")
async def test_llm():
    return {
        "reponse": await ask(
            "Tu es un tuteur de français.",
            [{"role": "user", "content": "Dis bonjour en une phrase."}]
        )
    }

@app.get("/")
def accueil():
    return FileResponse("static/index.html")

class ChatIn(BaseModel):
    message: str
    level: str = "A1"
    theme: str = "la vie quotidienne"
    l1: str = ""
    history: list[dict] = []

@app.post("/api/chat")
async def chat(r: ChatIn):
    system = build_system("chat", r.level, r.theme, r.l1)
    msgs = trim_history(r.history) + [{"role": "user", "content": r.message}]
    return await ask_model(system, msgs, ChatOut)

class CorrectIn(BaseModel):
    phrase: str
    level: str = "A1"
    l1: str = ""

@app.post("/api/correct")
async def correct(r: CorrectIn):
    system = build_system("correct", r.level, l1=r.l1)
    return await ask_model(system, [{"role": "user", "content": r.phrase}], Correction)
class ExplainIn(BaseModel):
    notion: str = "la différence entre passé composé et imparfait"
    level: str = "c1"
    l1: str = ""

@app.post("/api/explain")
async def explain(r: ExplainIn):
    system = build_system("explain", r.level, l1=r.l1)
    return await ask_model(system, [{"role": "user", "content": r.notion}], Explication)

class ExoIn(BaseModel):
    notion: str = "les articles"
    level: str = "A2"
    n: int = 4
    cibles: list[str] = []   # types d'erreurs fréquentes (rempli à l'étape 11)

@app.post("/api/exercises")
async def exercises(r: ExoIn):
    system = build_system("exercise", r.level)
    demande = f"Notion : {r.notion or 'libre, adaptée au niveau'}. Nombre : {r.n}. Erreurs fréquentes à cibler : {r.cibles or 'aucune'}."
    return await ask_model(system, [{"role": "user", "content": demande}], Exercices)




WHISPER = "mlx-community/whisper-small-mlx"

def _transcrire(path: str) -> str:
    return mlx_whisper.transcribe(path, path_or_hf_repo=WHISPER, language="fr")["text"].strip()

@app.post("/api/stt")
async def stt(audio: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
        f.write(await audio.read()); path = f.name
    try:
        texte = await run_in_threadpool(_transcrire, path)  # calcul lourd hors de la boucle serveur
    finally:
        os.remove(path)
    return {"texte": texte}




VOIX = "data/voix/fr_FR-siwis-medium.onnx"

class TtsIn(BaseModel):
    texte: str

def _synthese(texte: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    try:
        subprocess.run([sys.executable, "-m", "piper", "-m", VOIX, "-f", out],
                       input=texte.encode(), check=True, capture_output=True)
        with open(out, "rb") as fh:
            return fh.read()
    finally:
        os.remove(out)

@app.post("/api/tts")
async def tts(r: TtsIn):
    return Response(await run_in_threadpool(_synthese, r.texte[:500]), media_type="audio/wav")



class BilanIn(BaseModel):
    history: list[dict]
    level: str = "A1"

@app.post("/api/bilan")
async def bilan(r: BilanIn):
    conv = "\n".join(f"{m['role']}: {m['content']}" for m in r.history)
    demande = f"Conversation :\n{conv}\nErreurs fréquentes : {top_erreurs() or 'aucune'}"
    b = await ask_model(build_system("bilan", r.level), [{"role": "user", "content": demande}], Bilan)
    save_bilan(b.resume)
    return b

@app.get("/api/progress")
def progress():
    t = taux_erreur()
    sugg = None if t is None else ("monter" if t < 0.08 else "descendre" if t > 0.25 else "garder")
    return {"erreurs_frequentes": top_erreurs(5), "taux_erreur": t, "suggestion_niveau": sugg}
