"""Équipe d'agents LOGIMIND : Qualité, Documentation, Lineage, Orchestrateur.

Chaque agent lit la base, produit des CONSTATS ; l'orchestrateur les transforme en
RECOMMANDATIONS priorisées. Aucune modification de données sans validation humaine.
Les agents sont ici à base de règles : la fonction `explain()` est le point d'entrée
où brancher un LLM (voir README).
"""
import json, sqlite3, unicodedata
from datetime import datetime

SEV_W = {"Haute": 3, "Moyenne": 2, "Faible": 1}
CRITICAL_COLS = {("commandes", "quantite"): "Haute", ("commandes", "client_id"): "Haute",
                 ("produits", "prix_unitaire"): "Moyenne", ("produits", "categorie"): "Moyenne",
                 ("clients", "ville"): "Faible", ("clients", "telephone"): "Faible"}
TABLES = ["clients", "produits", "commandes", "livraisons"]

def now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def norm(s):
    s = unicodedata.normalize("NFD", (s or "").strip().lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")
def connect(path):
    con = sqlite3.connect(path); con.row_factory = sqlite3.Row; return con
def rows(con, sql, args=()): return [dict(r) for r in con.execute(sql, args)]
def explain(text):
    """Point d'extension LLM : retourne le texte tel quel (mode règles)."""
    return text

# ---------------------------------------------------------------- Lineage
def downstream(con, node):
    edges = rows(con, "SELECT src,dst FROM lineage"); seen, stack = set(), [node]
    while stack:
        n = stack.pop()
        for e in edges:
            if e["src"] == n and e["dst"] not in seen:
                seen.add(e["dst"]); stack.append(e["dst"])
    return sorted(seen)

# ---------------------------------------------------------------- Agent Qualité
def agent_quality(con):
    F = []
    def add(key, table, sev, title, detail, evidence, action, apply, affected):
        F.append(dict(agent="Qualité", type="quality", key=key, table_name=table, severity=sev, title=title,
                      detail=detail, evidence=evidence, proposed_action=action, apply=apply, affected=affected))
    # doublons exacts de commandes
    d = rows(con, """SELECT group_concat(commande_id) ids, count(*) n FROM commandes
                     GROUP BY client_id,produit_id,quantite,date_commande HAVING n>1 AND client_id IS NOT NULL""")
    if d:
        extra = sum(x["n"] - 1 for x in d)
        add("dup:commandes", "commandes", "Haute", f"{extra} commandes en doublon",
            "Même client, même produit, même quantité et même date de commande.",
            [f"Commandes {x['ids']}" for x in d[:5]],
            "Supprimer les doublons en conservant la première occurrence", "dedupe_commandes", extra)
    # doublons « souples » de clients
    cl = rows(con, "SELECT client_id, nom FROM clients"); g = {}
    for c in cl: g.setdefault(norm(c["nom"]), []).append(c)
    dups = [v for v in g.values() if len(v) > 1]
    if dups:
        extra = sum(len(v) - 1 for v in dups)
        add("dup:clients", "clients", "Moyenne", f"{extra} clients probablement en double",
            "Noms identiques après normalisation (casse, accents, espaces).",
            [" ↔ ".join(f"#{c['client_id']} « {c['nom']} »" for c in v) for v in dups],
            "Fusionner les fiches et rattacher leurs commandes au client conservé", "merge_clients", extra)
    # valeurs manquantes
    for t in TABLES:
        cols = [r["name"] for r in con.execute(f"PRAGMA table_info({t})")][1:]
        for c in cols:
            n = con.execute(f"SELECT count(*) FROM {t} WHERE {c} IS NULL OR trim({c})=''").fetchone()[0]
            if n:
                ids = [r[0] for r in con.execute(f"SELECT rowid FROM {t} WHERE {c} IS NULL OR trim({c})='' LIMIT 6")]
                add(f"null:{t}.{c}", t, CRITICAL_COLS.get((t, c), "Faible"), f"{n} valeur{'s' if n>1 else ''} manquante{'s' if n>1 else ''} : {t}.{c}",
                    "Champ vide alors qu'il est attendu pour les analyses.",
                    [f"{t} ligne(s) {', '.join(map(str, ids))}"], "Créer un ticket de correction pour le Data Steward",
                    "ticket", n)
    # valeurs invalides
    n = con.execute("SELECT count(*) FROM commandes WHERE quantite<=0").fetchone()[0]
    if n:
        ev = [f"Commande {r[0]} : quantité = {r[1]}" for r in con.execute(
            "SELECT commande_id, quantite FROM commandes WHERE quantite<=0")]
        add("range:commandes.quantite", "commandes", "Haute", f"{n} quantités négatives ou nulles",
            "Une quantité commandée doit être strictement positive.", ev, "Mettre en quarantaine et demander une correction", "ticket", n)
    n = con.execute("SELECT count(*) FROM commandes WHERE date_livraison_prevue < date_commande").fetchone()[0]
    if n:
        ev = [f"Commande {r[0]} : commandée le {r[1]}, livraison prévue le {r[2]}" for r in con.execute(
            "SELECT commande_id,date_commande,date_livraison_prevue FROM commandes WHERE date_livraison_prevue<date_commande LIMIT 5")]
        add("date:commandes", "commandes", "Moyenne", f"{n} dates incohérentes",
            "La livraison prévue précède la date de commande.", ev, "Créer un ticket de correction", "ticket", n)
    # intégrité référentielle
    n = con.execute("SELECT count(*) FROM livraisons WHERE commande_id NOT IN (SELECT commande_id FROM commandes)").fetchone()[0]
    if n:
        ev = [f"Livraison {r[0]} → commande inexistante #{r[1]}" for r in con.execute(
            "SELECT livraison_id,commande_id FROM livraisons WHERE commande_id NOT IN (SELECT commande_id FROM commandes)")]
        add("fk:livraisons", "livraisons", "Haute", f"{n} livraisons orphelines",
            "La commande référencée n'existe pas (clé étrangère brisée).", ev, "Isoler les lignes et enquêter sur la source", "ticket", n)
    return F

def quality_scores(con):
    """Score 0-100 par table = part de lignes sans anomalie détectée."""
    out = {}
    for t in TABLES:
        total = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        pk = [r["name"] for r in con.execute(f"PRAGMA table_info({t})")][0]
        bad = set()
        for c in [r["name"] for r in con.execute(f"PRAGMA table_info({t})")][1:]:
            if (t, c) in CRITICAL_COLS:
                bad |= {r[0] for r in con.execute(f"SELECT {pk} FROM {t} WHERE {c} IS NULL OR trim({c})=''")}
        if t == "commandes":
            bad |= {r[0] for r in con.execute("SELECT commande_id FROM commandes WHERE quantite<=0 OR date_livraison_prevue<date_commande")}
            for r in con.execute("""SELECT group_concat(commande_id) FROM commandes GROUP BY client_id,produit_id,quantite,date_commande
                                    HAVING count(*)>1 AND client_id IS NOT NULL"""):
                bad |= set(map(int, r[0].split(",")[1:]))
        if t == "livraisons":
            bad |= {r[0] for r in con.execute("SELECT livraison_id FROM livraisons WHERE commande_id NOT IN (SELECT commande_id FROM commandes)")}
        if t == "clients":
            g = {}
            for r in con.execute("SELECT client_id,nom FROM clients ORDER BY client_id"): g.setdefault(norm(r[1]), []).append(r[0])
            for v in g.values(): bad |= set(v[1:])
        out[t] = dict(total=total, bad=len(bad), score=round(100 * (1 - len(bad) / max(total, 1)), 1))
    tot = sum(v["total"] for v in out.values()); bad = sum(v["bad"] for v in out.values())
    out["_global"] = round(100 * (1 - bad / max(tot, 1)), 1)
    return out

# ---------------------------------------------------------------- Agent Documentation
HINTS = {"id": "Identifiant unique", "nom": "Nom", "ville": "Ville de l'établissement", "telephone": "Numéro de téléphone (donnée personnelle)",
         "categorie": "Catégorie de produit", "prix": "Prix unitaire en dirhams", "seuil": "Seuil de stock minimal avant réapprovisionnement",
         "quantite": "Nombre d'unités", "date_commande": "Date de passage de la commande", "date_livraison_prevue": "Date de livraison promise au client",
         "date_livraison_reelle": "Date de livraison constatée", "statut": "Statut d'avancement", "chauffeur": "Chauffeur ayant effectué la tournée"}
OWNERS = {"clients": "Resp. Ventes", "produits": "Resp. Achats", "commandes": "Resp. Ventes", "livraisons": "Resp. Logistique"}

def describe(table, col):
    if col.endswith("_id") and col.startswith(table[:-1]): return f"Identifiant unique ({table})"
    if col.endswith("_id"): return f"Référence vers {col[:-3]} (clé étrangère)"
    for k, v in HINTS.items():
        if col.startswith(k) or k in col: return v
    return f"Champ {col.replace('_', ' ')}"

def agent_documentation(con):
    F = []; done = {(r["table_name"], r["column_name"]) for r in rows(con, "SELECT table_name,column_name FROM catalog")}
    for t in TABLES:
        miss = [c["name"] for c in con.execute(f"PRAGMA table_info({t})") if (t, c["name"]) not in done]
        if miss:
            props = {c: dict(description=explain(describe(t, c)), owner=OWNERS[t],
                             sensitivity="Élevée" if c in ("telephone",) else "Faible") for c in miss}
            F.append(dict(agent="Documentation", type="doc", key=f"doc:{t}", table_name=t, severity="Faible",
                          title=f"{len(miss)} colonnes non documentées : {t}",
                          detail="Descriptions, propriétaire et sensibilité proposés à partir des noms et types de colonnes.",
                          evidence=[f"{c} → {p['description']}" for c, p in list(props.items())[:5]],
                          proposed_action="Publier ces métadonnées dans le catalogue", apply="publish_doc",
                          affected=len(miss), payload=props))
    return F

# ---------------------------------------------------------------- Agent Lineage
def agent_lineage(con, quality_findings):
    F = []; seen = set()
    for f in quality_findings:
        t = f["table_name"]
        if f["severity"] == "Haute" and t not in seen:
            seen.add(t); down = downstream(con, t)
            if down:
                F.append(dict(agent="Lineage", type="impact", key=f"impact:{t}", table_name=t, severity="Haute",
                              title=f"Table « {t} » critique : {len(down)} objets en aval impactés",
                              detail="Des anomalies de gravité haute affectent une table qui alimente des KPI et rapports.",
                              evidence=["Impactés : " + ", ".join(down)],
                              proposed_action="Marquer la table « à surveiller » et alerter les propriétaires des rapports",
                              apply="flag", affected=len(down), downstream=down))
    return F

# ---------------------------------------------------------------- Orchestrateur
def orchestrate(path):
    con = connect(path); ts = now()
    q = agent_quality(con); d = agent_documentation(con); l = agent_lineage(con, q)
    findings = q + d + l
    log = lambda actor, action, target, det="": con.execute(
        "INSERT INTO audit_log(ts,actor,action,target,details) VALUES(?,?,?,?,?)", (ts, actor, action, target, det))
    log("Orchestrateur", "Analyse lancée", "base", f"{len(findings)} constats collectés")
    live = set()
    for f in findings:
        live.add(f["key"]); down = f.get("downstream") or downstream(con, f["table_name"])
        prio = round(SEV_W[f["severity"]] * (1 + len(down)) * (1 + min(f["affected"], 20) / 20), 1)
        ev = json.dumps(f["evidence"], ensure_ascii=False)
        extra = json.dumps({"apply": f["apply"], "payload": f.get("payload"), "downstream": down}, ensure_ascii=False)
        cur = con.execute("SELECT id,status FROM recommendations WHERE key=?", (f["key"],)).fetchone()
        if cur is None:
            con.execute("""INSERT INTO recommendations(key,agent,type,severity,table_name,title,detail,evidence,proposed_action,
                           impact,priority,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,'Proposée',?)""",
                        (f["key"], f["agent"], f["type"], f["severity"], f["table_name"], f["title"], f["detail"], ev,
                         f["proposed_action"], extra, prio, ts))
            log(f"Agent {f['agent']}", "Recommandation proposée", f["key"], f["title"])
        elif cur["status"] in ("Proposée", "À réanalyser"):
            con.execute("UPDATE recommendations SET title=?,evidence=?,impact=?,priority=?,status='Proposée' WHERE id=?",
                        (f["title"], ev, extra, prio, cur["id"]))
            if cur["status"] == "À réanalyser":
                log(f"Agent {f['agent']}", "Réanalyse effectuée", f["key"], "Preuves mises à jour")
    for r in rows(con, "SELECT id,key FROM recommendations WHERE status IN ('Proposée','À réanalyser')"):
        if r["key"] not in live:
            con.execute("UPDATE recommendations SET status='Résolue' WHERE id=?", (r["id"],))
            log("Orchestrateur", "Constat disparu", r["key"], "Marquée comme résolue")
    con.commit(); con.close()

# ---------------------------------------------------------------- Décision humaine
def decide(path, rec_id, decision, who="Responsable Data", comment=""):
    """decision ∈ {accept, reject, reanalyze}. Seule `accept` peut modifier les données."""
    con = connect(path); r = con.execute("SELECT * FROM recommendations WHERE id=?", (rec_id,)).fetchone()
    if not r or r["status"] not in ("Proposée", "À réanalyser"): con.close(); return "Déjà traitée"
    extra = json.loads(r["impact"]); result = ""
    if decision == "accept":
        a = extra["apply"]
        if a == "dedupe_commandes":
            n = con.execute("""DELETE FROM commandes WHERE commande_id IN (SELECT commande_id FROM commandes c WHERE EXISTS
                (SELECT 1 FROM commandes o WHERE o.commande_id<c.commande_id AND o.client_id=c.client_id AND o.produit_id=c.produit_id
                 AND o.quantite=c.quantite AND o.date_commande=c.date_commande))""").rowcount
            result = f"{n} doublons supprimés"
        elif a == "merge_clients":
            g = {}
            for c in rows(con, "SELECT client_id,nom FROM clients ORDER BY client_id"): g.setdefault(norm(c["nom"]), []).append(c["client_id"])
            n = 0
            for ids in g.values():
                for other in ids[1:]:
                    con.execute("UPDATE commandes SET client_id=? WHERE client_id=?", (ids[0], other))
                    con.execute("DELETE FROM clients WHERE client_id=?", (other,)); n += 1
            result = f"{n} fiches fusionnées"
        elif a == "publish_doc":
            for col, p in extra["payload"].items():
                con.execute("INSERT OR REPLACE INTO catalog VALUES(?,?,?,?,?,'Validée')",
                            (r["table_name"], col, p["description"], p["owner"], p["sensitivity"]))
            result = f"{len(extra['payload'])} colonnes documentées"
        elif a == "flag": result = "Table marquée « à surveiller »"
        else: result = "Ticket créé pour le Data Steward"
        status = "Acceptée"
    elif decision == "reject": status, result = "Rejetée", "Aucune modification"
    else: status, result = "À réanalyser", "Demande de nouvelle analyse"
    con.execute("UPDATE recommendations SET status=?,decided_at=?,decided_by=?,comment=?,result=? WHERE id=?",
                (status, now(), who, comment, result, rec_id))
    con.execute("INSERT INTO audit_log(ts,actor,action,target,details) VALUES(?,?,?,?,?)",
                (now(), who, f"Décision : {status}", r["key"], (comment + " | " if comment else "") + result))
    con.commit(); con.close()
    if decision == "reanalyze": orchestrate(path)
    return result
