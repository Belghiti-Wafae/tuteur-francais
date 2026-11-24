
import json
import os
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

PROVIDER = os.getenv("PROVIDER", "groq")
MODEL = os.getenv("MODEL", "openai/gpt-oss-120b")


async def ask(system: str, messages: list[dict], max_tokens: int = 900) -> str:
    """Envoie un prompt au LLM et renvoie le texte brut."""

    async with httpx.AsyncClient(timeout=60) as c:

        # 1. OLLAMA LOCAL
        if PROVIDER == "ollama":
            r = await c.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system}
                    ] + messages,
                    "options": {"num_predict": max_tokens}
                }
            )
            r.raise_for_status()
            return r.json()["message"]["content"]

        
        # 2. GROQ API
        elif PROVIDER == "groq":
            api_key = os.getenv("GROQ_API_KEY")

            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail="GROQ_API_KEY manquante dans le fichier .env"
                )

            groq_messages = [
                {"role": "system", "content": system}
            ] + messages

            r = await c.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": groq_messages,
                    "max_completion_tokens": max_tokens,
                    "temperature": 0.3
                }
            )

            if r.status_code != 200:
                raise HTTPException(
                    status_code=r.status_code,
                    detail=f"Erreur Groq : {r.text}"
                )

            data = r.json()
            return data["choices"][0]["message"]["content"]

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Provider non supporté : {PROVIDER}"
            )



async def ask_model(system: str, messages: list[dict], model):
    """Demande un JSON, le valide avec un modèle Pydantic, réessaie une fois."""

    last = None

    for _ in range(2):
        try:
            txt = await ask(system, messages)
            data = json.loads(
                txt[txt.index("{"): txt.rindex("}") + 1]
            )
            return model(**data)

        except (ValueError, KeyError) as e:
            last = e

    raise HTTPException(
        502,
        f"Réponse invalide du modèle : {last}"
    )
