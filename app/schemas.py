from typing import Any
from pydantic import BaseModel, field_validator

def _t(x):
    if isinstance(x, str): return x
    if isinstance(x, dict): return " — ".join(str(v) for v in x.values())
    if isinstance(x, list): return ", ".join(map(str, x))
    return str(x)

class _Base(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _coerce(cls, v, info):
        ann = cls.model_fields[info.field_name].annotation
        if ann is str: return _t(v) if v is not None else ""
        if ann == list[str]: return [_t(x) for x in (v or [])]
        return v

class ChatOut(_Base):
    reponse: str

class Erreur(_Base):
    extrait: str = ""
    type: str = "autre"
    explication: str = ""
    regle: str = ""

class Correction(_Base):
    phrase_corrigee: str = ""
    erreurs: list[Erreur] = []
    encouragement: str = ""

class Explication(_Base):
    titre: str = ""
    explication: str
    exemples: list[str] = []
    verification: str = ""

class Exercice(_Base):
    type: str = "qcm"
    enonce: str
    options: list[str] = []
    reponse: str = ""
    indice: str = ""
    explication: str = ""

class Exercices(_Base):
    notion: str = ""
    exercices: list[Exercice]