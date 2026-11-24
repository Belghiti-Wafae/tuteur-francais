import sqlite3

db = sqlite3.connect("data/tuteur.db", check_same_thread=False)
db.executescript("""
CREATE TABLE IF NOT EXISTS corrections(id INTEGER PRIMARY KEY, ts TEXT DEFAULT CURRENT_TIMESTAMP,
  niveau TEXT, nb_mots INT, nb_erreurs INT);
CREATE TABLE IF NOT EXISTS erreurs(id INTEGER PRIMARY KEY, ts TEXT DEFAULT CURRENT_TIMESTAMP,
  niveau TEXT, type TEXT, extrait TEXT, regle TEXT);
CREATE TABLE IF NOT EXISTS bilans(id INTEGER PRIMARY KEY, ts TEXT DEFAULT CURRENT_TIMESTAMP, resume TEXT);
""")

def log_correction(niveau, phrase, k):
    db.execute("INSERT INTO corrections(niveau,nb_mots,nb_erreurs) VALUES(?,?,?)",
               (niveau, len(phrase.split()), len(k.erreurs)))
    db.executemany("INSERT INTO erreurs(niveau,type,extrait,regle) VALUES(?,?,?,?)",
                   [(niveau, e.type, e.extrait, e.regle) for e in k.erreurs])
    db.commit()

def top_erreurs(n=3):
    return [r[0] for r in db.execute(
        "SELECT type FROM erreurs GROUP BY type ORDER BY COUNT(*) DESC LIMIT ?", (n,))]

def taux_erreur(n=30):
    s, m = db.execute("SELECT SUM(nb_erreurs), SUM(nb_mots) FROM "
                      "(SELECT * FROM corrections ORDER BY id DESC LIMIT ?)", (n,)).fetchone()
    return (s or 0) / m if m else None

def save_bilan(resume):
    db.execute("INSERT INTO bilans(resume) VALUES(?)", (resume,)); db.commit()

def dernier_resume():
    row = db.execute("SELECT resume FROM bilans ORDER BY id DESC LIMIT 1").fetchone()
    return row[0] if row else ""