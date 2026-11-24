import json, re, statistics, time
import httpx

def norm(s): return re.sub(r"[^\w\s]", "", s.lower()).strip()

data = json.load(open("data/jeu_test.json"))
exact = detect = 0; lat = []
for d in data:
    t = time.time()
    r = httpx.post("http://127.0.0.1:8000/api/correct",
                   json={"phrase": d["phrase"], "level": d["niveau"]}, timeout=60).json()
    lat.append(time.time() - t)
    exact += norm(r["phrase_corrigee"]) == norm(d["attendu"])
    detect += (len(r["erreurs"]) > 0) == (d["nb_erreurs"] > 0)
n = len(data)
print(f"Correction exacte : {exact/n:.0%} | Détection d'erreur : {detect/n:.0%} | Latence moyenne : {statistics.mean(lat):.1f} s")