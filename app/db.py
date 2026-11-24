import hashlib, hmac, json, os, secrets, sqlite3, time

import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(BASE, "data"), exist_ok=True)
db = sqlite3.connect(os.path.join(BASE, "data", "app.db"), check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, pwd TEXT, nom TEXT DEFAULT '',
  l1 TEXT DEFAULT '', niveau TEXT DEFAULT 'A1', objectif TEXT DEFAULT '', avatar INT DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INT, exp REAL);
CREATE TABLE IF NOT EXISTS convs(id INTEGER PRIMARY KEY, user_id INT, mode TEXT, theme TEXT, niveau TEXT,
  titre TEXT, ts TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS msgs(id INTEGER PRIMARY KEY, conv_id INT, role TEXT, kind TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS erreurs(id INTEGER PRIMARY KEY, user_id INT, type TEXT, extrait TEXT);
""")

def _hash(p, salt=None):
    salt = salt or os.urandom(16)
    return salt.hex() + ":" + hashlib.scrypt(p.encode(), salt=salt, n=2**14, r=8, p=1).hex()

def check_pwd(p, stored):
    s, h = stored.split(":")
    return hmac.compare_digest(_hash(p, bytes.fromhex(s)).split(":")[1], h)

def create_user(email, pwd, nom):
    c = db.execute("INSERT INTO users(email,pwd,nom) VALUES(?,?,?)", (email, _hash(pwd), nom))
    db.commit(); return c.lastrowid

def user_by_email(e): return db.execute("SELECT * FROM users WHERE email=?", (e,)).fetchone()
def user_by_id(i): return db.execute("SELECT * FROM users WHERE id=?", (i,)).fetchone()

def new_session(uid):
    t = secrets.token_urlsafe(32)
    db.execute("INSERT INTO sessions VALUES(?,?,?)", (t, uid, time.time() + 30 * 86400)); db.commit(); return t

def user_by_token(t):
    if not t: return None
    return db.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.exp>?",
                      (t, time.time())).fetchone()

def end_session(t): db.execute("DELETE FROM sessions WHERE token=?", (t,)); db.commit()

def set_prefs(uid, l1, niveau, objectif, avatar):
    db.execute("UPDATE users SET l1=?,niveau=?,objectif=?,avatar=? WHERE id=?", (l1, niveau, objectif, int(avatar), uid))
    db.commit()

def create_conv(uid, mode, theme, niveau, titre):
    c = db.execute("INSERT INTO convs(user_id,mode,theme,niveau,titre) VALUES(?,?,?,?,?)", (uid, mode, theme, niveau, titre))
    db.commit(); return c.lastrowid

def list_convs(uid):
    return [dict(r) for r in db.execute("SELECT id,titre,mode,ts FROM convs WHERE user_id=? ORDER BY id DESC", (uid,))]

def get_conv(cid, uid):
    r = db.execute("SELECT * FROM convs WHERE id=? AND user_id=?", (cid, uid)).fetchone()
    return dict(r) if r else None

def del_conv(cid, uid):
    if get_conv(cid, uid):
        db.execute("DELETE FROM msgs WHERE conv_id=?", (cid,)); db.execute("DELETE FROM convs WHERE id=?", (cid,)); db.commit()

def add_msg(cid, role, kind, data):
    db.execute("INSERT INTO msgs(conv_id,role,kind,data) VALUES(?,?,?,?)", (cid, role, kind, json.dumps(data, ensure_ascii=False)))
    db.commit()

def get_msgs(cid):
    return [{"role": r["role"], "kind": r["kind"], "data": json.loads(r["data"])}
            for r in db.execute("SELECT * FROM msgs WHERE conv_id=? ORDER BY id", (cid,))]

def history(cid, n=8):
    rows = db.execute("SELECT kind,data FROM msgs WHERE conv_id=? AND kind IN ('user','chat') ORDER BY id DESC LIMIT ?", (cid, n)).fetchall()
    out = []
    for r in reversed(rows):
        d = json.loads(r["data"])
        out.append({"role": "user", "content": d["text"]} if r["kind"] == "user" else {"role": "assistant", "content": d["reponse"]})
    return out

def log_errors(uid, errs):
    db.executemany("INSERT INTO erreurs(user_id,type,extrait) VALUES(?,?,?)", [(uid, e.type, e.extrait) for e in errs]); db.commit()

def top_erreurs(uid, n=3):
    return [r[0] for r in db.execute("SELECT type FROM erreurs WHERE user_id=? GROUP BY type ORDER BY COUNT(*) DESC LIMIT ?", (uid, n))]
import functools, threading, types

_lock = threading.RLock()

def _locked(f):
    @functools.wraps(f)
    def w(*a, **k):
        with _lock:
            return f(*a, **k)
    return w

for _n, _f in list(globals().items()):
    if isinstance(_f, types.FunctionType) and _f.__module__ == __name__ and not _n.startswith("_"):
        globals()[_n] = _locked(_f)