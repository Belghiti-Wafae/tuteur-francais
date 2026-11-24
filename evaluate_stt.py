
import json
import re
import httpx
from jiwer import wer

def norm(s):
    return re.sub(r"[^\w\s']", "", s.lower()).strip()

with open("data/stt/refs.json", encoding="utf-8") as f:
    refs = json.load(f)

references = []
hypotheses = []

for filename, reference in refs.items():
    with open(f"data/stt/{filename}", "rb") as audio:
        response = httpx.post(
            "http://127.0.0.1:8000/api/stt",
            files={"audio": (filename, audio, "audio/webm")},
            timeout=120
        )

    response.raise_for_status()
    prediction = response.json()["texte"]

    references.append(norm(reference))
    hypotheses.append(norm(prediction))

    print(f"\nFichier : {filename}")
    print(f"Référence : {reference}")
    print(f"Prédiction : {prediction}")

score = wer(references, hypotheses)

print("\n==========================")
print(f"WER GLOBAL : {score:.2%}")
print("==========================")
