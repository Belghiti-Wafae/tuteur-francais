import os
import subprocess
import sys
import tempfile

from fastapi import Depends, FastAPI, File, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.routes import current_user, router

app = FastAPI(title="Tuteur de français")
app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def accueil():
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Reconnaissance vocale (STT) ----------
WHISPER = "mlx-community/whisper-small-mlx"


def _transcrire(path: str) -> str:
    import mlx_whisper  # importé ici : le serveur démarre même si le paquet manque
    return mlx_whisper.transcribe(path, path_or_hf_repo=WHISPER, language="fr")["text"].strip()


@app.post("/api/stt", dependencies=[Depends(current_user)])
async def stt(audio: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
        f.write(await audio.read())
        path = f.name
    try:
        texte = await run_in_threadpool(_transcrire, path)
    finally:
        os.remove(path)
    return {"texte": texte}


# ---------- Synthèse vocale (TTS) ----------
VOIX = "data/voix/fr_FR-siwis-medium.onnx"


class TtsIn(BaseModel):
    texte: str


def _piper(texte: str, out: str):
    p = subprocess.run([sys.executable, "-m", "piper", "-m", VOIX, "-f", out],
                       input=texte.encode(), capture_output=True)
    if p.returncode != 0:
        print("PIPER ERREUR :", p.stderr.decode()[-500:])
        raise RuntimeError("piper")


def _say(texte: str, out: str):
    subprocess.run(["say", "-v", "Thomas", "-o", out, "--file-format=WAVE",
                    "--data-format=LEI16@22050", "-f", "-"],
                   input=texte.encode(), check=True)


def _synthese(texte: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out = f.name
    try:
        try:
            _piper(texte, out)
        except Exception:
            _say(texte, out)  # repli sur la voix du Mac
        with open(out, "rb") as fh:
            return fh.read()
    finally:
        os.remove(out)


@app.post("/api/tts", dependencies=[Depends(current_user)])
async def tts(r: TtsIn):
    return Response(await run_in_threadpool(_synthese, r.texte[:500]), media_type="audio/wav")