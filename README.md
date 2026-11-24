# Camille — tuteur de français vocal (A1 à C2)

Tuteur de français pour adultes : conversation orale, explication de notions,
exercices générés et corrections commentées, avec avatar 3D facultatif.

## Fonctionnalités
- Comptes utilisateurs et historique des conversations
- Trois modes : conversation sur un thème, explication de notion, exercices
- Correction commentée en parallèle de la conversation (type d'erreur, règle, phrase corrigée)
- Exercices ciblés sur les erreurs fréquentes de chaque utilisateur
- Reconnaissance vocale locale (Whisper), synthèse vocale (Piper), avatar 3D (Three.js + VRM)
- Adaptation au niveau CECRL, de A1 à C2, et à la langue maternelle

## Architecture
Navigateur → FastAPI → LLM (API) · Whisper (STT) · Piper (TTS) · SQLite

## Installation
```bash
git clone https://github.com/VOTRE-NOM/tuteur-francais.git
cd tuteur-francais
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis renseignez votre clé d'API
```
**Voix Piper** : téléchargez `fr_FR-siwis-medium.onnx` et son `.onnx.json`
(dépôt Hugging Face « rhasspy/piper-voices ») dans `data/voix/`.
Sans Piper, l'application utilise la voix française de macOS.

**Avatar 3D (facultatif)** : placez un modèle `avatar.vrm` (créé avec VRoid Studio)
dans `static/`.

## Lancer
```bash
uvicorn app.main:app --reload
```
Ouvrez http://127.0.0.1:8000

## Limites
Un seul serveur local, voix traitées sur la machine, pas de réinitialisation de
mot de passe, synchronisation labiale approximative.

## Licence
MIT. Les voix et modèles 3D ont leurs propres licences.