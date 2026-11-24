from pydantic import BaseModel

class ChatOut(BaseModel):
    reponse: str
class Erreur(BaseModel):
    extrait: str
    type: str
    explication: str
    regle: str = ""

class Correction(BaseModel):
    phrase_corrigee: str
    erreurs: list[Erreur] = []
    encouragement: str = ""

class Explication(BaseModel):
    titre: str
    explication: str
    exemples: list[str]
    verification: str
class Exercice(BaseModel):
    type: str
    enonce: str
    options: list[str] = []
    reponse: str
    indice: str = ""
    explication: str

class Exercices(BaseModel):
    notion: str
    exercices: list[Exercice]
class Bilan(BaseModel):
    resume: str
    points_forts: list[str]
    a_retravailler: list[str]
    vocabulaire: list[str]
    objectif_prochain: str