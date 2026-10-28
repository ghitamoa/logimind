"""Interface de supervision humaine LOGIMIND (Flask, Python pur).  Lancer :  python app.py"""
import json, os
from flask import Flask, render_template_string, request, redirect, url_for
import seed, agents

DB = seed.DB
app = Flask(__name__)

def init():
    if not os.path.exists(DB):
        seed.build(); agents.orchestrate(DB)

def scores():
    con = agents.connect(DB); r = agents.quality_scores(con); con.close(); return r

def q(sql, args=()):
    con = agents.connect(DB); r = agents.rows(con, sql, args); con.close(); return r

CSS = """
:root{--navy:#0B1B33;--blue:#2F6BFF;--bg:#F4F6FB;--card:#fff;--ink:#14213D;--mut:#6B7690;--line:#E3E8F2;
--hi:#E5484D;--mid:#F5A524;--lo:#8A94A8;--ok:#12A87C}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 "Segoe UI",Calibri,Arial,sans-serif}
header{background:var(--navy);color:#fff;padding:0 32px;display:flex;align-items:center;gap:28px;height:64px}
.brand{font:700 22px Cambria,Georgia,serif;letter-spacing:.5px}.brand small{display:block;font:400 11px "Segoe UI",sans-serif;color:#9FB2D6;letter-spacing:1.5px;text-transform:uppercase}
nav{display:flex;gap:4px;margin-left:12px}nav a{color:#B9C7E4;text-decoration:none;padding:8px 14px;border-radius:8px;font-size:14px}
nav a.on,nav a:hover{background:#1B3157;color:#fff}.sp{flex:1}
.who{font-size:13px;color:#9FB2D6}.who b{color:#fff}
main{max-width:1180px;margin:28px auto;padding:0 24px}
.kpis{display:grid;grid-template-columns:1.3fr 1fr 1fr 1fr;gap:16px;margin-bottom:24px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.kpi .l{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:1px}.kpi .v{font:700 36px Cambria,serif;margin-top:4px}
.kpi.big{background:var(--navy);color:#fff;border:0}.kpi.big .l{color:#9FB2D6}.kpi.big .v{font-size:46px}
h2{font:700 22px Cambria,serif;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 18px}
.bar{display:flex;gap:10px;align-items:center;margin-bottom:18px}
.pill{padding:6px 14px;border-radius:99px;background:#fff;border:1px solid var(--line);text-decoration:none;color:var(--ink);font-size:13px}
.pill.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.rec{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:14px;display:grid;grid-template-columns:8px 1fr auto;gap:18px}
.sev{border-radius:4px}.Haute{background:var(--hi)}.Moyenne{background:var(--mid)}.Faible{background:var(--lo)}
.chips{display:flex;gap:8px;align-items:center;margin-bottom:6px;font-size:12px}
.chip{padding:2px 10px;border-radius:99px;background:#EAF0FF;color:#1D4ED8;font-weight:600}
.chip.g{background:#E7F7F1;color:#0B7A59}.chip.r{background:#FDECEC;color:#B42318}.chip.y{background:#FFF3DC;color:#9A6200}.chip.n{background:#EEF1F6;color:#4A5568}
.rec h3{margin:0 0 4px;font-size:17px}.rec p{margin:2px 0;color:#3B4660}
.act{margin-top:8px;padding:8px 12px;background:#F2F6FF;border-radius:8px;font-size:14px}
details{margin-top:8px;font-size:13px;color:var(--mut)}summary{cursor:pointer;color:var(--blue)}details li{margin:2px 0}
.side{display:flex;flex-direction:column;gap:8px;min-width:210px}
.side input{padding:8px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:13px}
button{border:0;border-radius:9px;padding:10px 14px;font:600 14px inherit;cursor:pointer}
.b-ok{background:var(--ok);color:#fff}.b-no{background:#fff;color:var(--hi);border:1px solid #F3C5C7}.b-re{background:#fff;color:var(--blue);border:1px solid #C9D8FF}.b-dark{background:var(--navy);color:#fff}
.b-ghost{background:#1B3157;color:#fff;font-weight:500;font-size:13px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line);font-size:14px}th{background:#F7F9FD;color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.8px}
.score{display:grid;grid-template-columns:130px 1fr 80px;gap:14px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 18px;margin-bottom:10px}
.track{height:12px;background:#EDF1F8;border-radius:99px;overflow:hidden}.fill{height:100%;border-radius:99px}
.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px;overflow-x:auto}
.empty{padding:40px;text-align:center;color:var(--mut);background:#fff;border:1px dashed var(--line);border-radius:14px}
"""

BASE = """<!doctype html><html lang="fr"><meta charset="utf-8"><title>LOGIMIND – Supervision</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{{css|safe}}</style>
<header><div class="brand">LOGIMIND<small>Équipe d'agents Data</small></div>
<nav>{% for k,l in tabs %}<a class="{{'on' if k==tab}}" href="{{url_for(k)}}">{{l}}</a>{% endfor %}</nav><div class="sp"></div>
<form method="post" action="{{url_for('run')}}"><button class="b-ghost">↻ Relancer l'analyse</button></form>
<form method="post" action="{{url_for('reset')}}" onsubmit="return confirm('Réinitialiser la démo ?')"><button class="b-ghost">Réinitialiser</button></form>
<div class="who">Connectée : <b>Responsable Data</b></div></header>
<main>{{body|safe}}</main></html>"""

TABS = [("recs", "Recommandations"), ("quality", "Qualité"), ("catalog", "Catalogue"), ("lineage", "Lineage"), ("audit", "Audit")]

def page(tab, body):
    return render_template_string(BASE, css=CSS, tab=tab, tabs=TABS, body=body)

def tpl(s, **kw): return render_template_string(s, **kw)

@app.route("/")
def recs():
    st = request.args.get("status", "Proposée")
    sc = scores()
    cnt = {r["status"]: r["n"] for r in q("SELECT status, count(*) n FROM recommendations GROUP BY status")}
    sql = "SELECT * FROM recommendations" + ("" if st == "Toutes" else " WHERE status=?") + " ORDER BY priority DESC"
    items = q(sql, () if st == "Toutes" else (st,))
    for r in items:
        r["evidence"] = json.loads(r["evidence"]); r["down"] = json.loads(r["impact"]).get("downstream", [])
    body = tpl("""
<div class="kpis">
 <div class="kpi big"><div class="l">Score de qualité global</div><div class="v">{{sc['_global']}}%</div></div>
 <div class="kpi"><div class="l">En attente de décision</div><div class="v" style="color:#B45309">{{cnt.get('Proposée',0)+cnt.get('À réanalyser',0)}}</div></div>
 <div class="kpi"><div class="l">Acceptées</div><div class="v" style="color:var(--ok)">{{cnt.get('Acceptée',0)}}</div></div>
 <div class="kpi"><div class="l">Rejetées</div><div class="v" style="color:var(--hi)">{{cnt.get('Rejetée',0)}}</div></div></div>
<h2>Recommandations des agents</h2><p class="sub">Triées par priorité (gravité × impact en aval). Aucune donnée n'est modifiée sans votre décision.</p>
<div class="bar">{% for s in ['Proposée','Acceptée','Rejetée','Toutes'] %}<a class="pill {{'on' if s==st}}" href="?status={{s}}">{{s if s!='Proposée' else 'À traiter'}}</a>{% endfor %}</div>
{% for r in items %}<div class="rec"><div class="sev {{r.severity}}"></div><div>
 <div class="chips"><span class="chip">Agent {{r.agent}}</span><span class="chip {{'r' if r.severity=='Haute' else 'y' if r.severity=='Moyenne' else 'n'}}">Gravité {{r.severity}}</span>
 <span class="chip n">{{r.table_name}}</span><span class="chip n">Priorité {{r.priority}}</span>
 {% if r.status!='Proposée' %}<span class="chip {{'g' if r.status=='Acceptée' else 'r' if r.status=='Rejetée' else 'y'}}">{{r.status}}</span>{% endif %}</div>
 <h3>{{r.title}}</h3><p>{{r.detail}}</p>
 <details><summary>Voir les preuves</summary><ul>{% for e in r.evidence %}<li>{{e}}</li>{% endfor %}</ul></details>
 <div class="act"><b>Action proposée :</b> {{r.proposed_action}}{% if r.down %} · <span style="color:var(--mut)">{{r.down|length}} objets en aval concernés</span>{% endif %}</div>
 {% if r.result %}<p style="margin-top:8px"><b>Résultat :</b> {{r.result}} <span style="color:var(--mut)">({{r.decided_by}}, {{r.decided_at}}){% if r.comment %} — « {{r.comment}} »{% endif %}</span></p>{% endif %}
</div>
{% if r.status in ('Proposée','À réanalyser') %}<form class="side" method="post" action="{{url_for('decision',rid=r.id)}}">
 <input name="comment" placeholder="Commentaire (facultatif)">
 <button class="b-ok" name="d" value="accept">✓ Accepter</button>
 <button class="b-no" name="d" value="reject">✕ Rejeter</button>
 <button class="b-re" name="d" value="reanalyze">↻ Demander une réanalyse</button></form>{% else %}<div></div>{% endif %}</div>
{% else %}<div class="empty">Rien à afficher ici. Toutes les recommandations ont été traitées 🎉</div>{% endfor %}""",
              sc=sc, cnt=cnt, items=items, st=st)
    return page("recs", body)

@app.post("/decide/<int:rid>")
def decision(rid):
    agents.decide(DB, rid, request.form["d"], comment=request.form.get("comment", "").strip())
    return redirect(request.referrer or url_for("recs"))

@app.post("/run")
def run(): agents.orchestrate(DB); return redirect(url_for("recs"))

@app.post("/reset")
def reset(): seed.build(); agents.orchestrate(DB); return redirect(url_for("recs"))

@app.route("/quality")
def quality():
    sc = scores()
    rows = q("SELECT table_name, count(*) n FROM recommendations WHERE type='quality' AND status IN ('Proposée','À réanalyser') GROUP BY table_name")
    n = {r["table_name"]: r["n"] for r in rows}
    body = tpl("""<h2>Qualité des données</h2><p class="sub">Part des lignes sans anomalie détectée. Le score remonte au fil des recommandations acceptées.</p>
{% for t in tables %}{% set s=sc[t] %}<div class="score"><div><b>{{t}}</b><div style="color:var(--mut);font-size:12px">{{s.total}} lignes</div></div>
<div class="track"><div class="fill" style="width:{{s.score}}%;background:{{'var(--ok)' if s.score>=90 else 'var(--mid)' if s.score>=75 else 'var(--hi)'}}"></div></div>
<div><b style="font:700 22px Cambria,serif">{{s.score}}%</b><div style="color:var(--mut);font-size:12px">{{n.get(t,0)}} constat(s) ouvert(s)</div></div></div>{% endfor %}""",
              sc=sc, n=n, tables=agents.TABLES)
    return page("quality", body)

@app.route("/catalog")
def catalog():
    cols = []
    con = agents.connect(DB)
    cat = {(r["table_name"], r["column_name"]): r for r in agents.rows(con, "SELECT * FROM catalog")}
    for t in agents.TABLES:
        for c in con.execute(f"PRAGMA table_info({t})"):
            cols.append((t, c["name"], c["type"], cat.get((t, c["name"]))))
    con.close()
    body = tpl("""<h2>Catalogue de données</h2><p class="sub">Métadonnées publiées après validation humaine.</p>
<table><tr><th>Table</th><th>Colonne</th><th>Type</th><th>Description</th><th>Propriétaire</th><th>Sensibilité</th><th>Statut</th></tr>
{% for t,c,ty,m in cols %}<tr><td>{{t}}</td><td><b>{{c}}</b></td><td>{{ty}}</td><td>{{m.description if m else '—'}}</td><td>{{m.owner if m else '—'}}</td><td>{{m.sensitivity if m else '—'}}</td>
<td><span class="chip {{'g' if m else 'y'}}">{{'Validée' if m else 'Non documentée'}}</span></td></tr>{% endfor %}</table>""", cols=cols)
    return page("catalog", body)

@app.route("/lineage")
def lineage():
    edges = q("SELECT src,dst FROM lineage")
    nodes = sorted({e["src"] for e in edges} | {e["dst"] for e in edges})
    def lvl(n): return 0 if n.endswith((".csv", ".xlsx")) else 1 if n in agents.TABLES else 2 if n.startswith("v_") else 3
    bad = {r["table_name"] for r in q("SELECT table_name FROM recommendations WHERE type='quality' AND severity='Haute' AND status IN ('Proposée','À réanalyser')")}
    cols = [[n for n in nodes if lvl(n) == i] for i in range(4)]
    W, H, GX, GY, TOP = 190, 38, 250, 62, 50
    pos = {n: (20 + lvl(n) * GX, TOP + i * GY) for l in cols for i, n in enumerate(l)}
    # propage la « contamination » vers l'aval
    tainted = set(bad)
    con2 = agents.connect(DB)
    for b in bad: tainted |= set(agents.downstream(con2, b))
    con2.close()
    h = TOP + max(len(c) for c in cols) * GY
    svg = [f'<svg width="{20+3*GX+W+20}" height="{h}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,Arial">']
    for i, t in enumerate(["Sources", "Tables", "Vues / KPI", "Rapports"]):
        svg.append(f'<text x="{20+i*GX}" y="26" font-size="12" fill="#6B7690" font-weight="700" letter-spacing="1">{t.upper()}</text>')
    for e in edges:
        (x1, y1), (x2, y2) = pos[e["src"]], pos[e["dst"]]
        x1 += W; y1 += H / 2; y2 += H / 2; m = (x1 + x2) / 2
        hot = e["src"] in tainted and e["dst"] in tainted
        svg.append(f'<path d="M{x1},{y1} C{m},{y1} {m},{y2} {x2},{y2}" fill="none" stroke="{"#F2A0A3" if hot else "#C8D2E6"}" stroke-width="2"/>')
    for n, (x, y) in pos.items():
        c = ("#FDECEC", "#E5484D") if n in bad else ("#FFF3DC", "#F5A524") if n in tainted else ("#EAF0FF", "#2F6BFF")
        svg.append(f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="9" fill="{c[0]}" stroke="{c[1]}" stroke-width="1.5"/>'
                   f'<text x="{x+W/2}" y="{y+24}" font-size="13" text-anchor="middle" fill="#14213D" font-weight="600">{n}</text>')
    svg.append("</svg>")
    body = tpl("""<h2>Lineage des données</h2><p class="sub">D'où viennent les données et ce qu'elles alimentent.
<span class="chip r">Anomalie grave</span> <span class="chip y">Impacté en aval</span> <span class="chip">Sain</span></p><div class="panel">{{svg|safe}}</div>""", svg="".join(svg))
    return page("lineage", body)

@app.route("/audit")
def audit():
    body = tpl("""<h2>Journal d'audit</h2><p class="sub">Chaque action d'un agent ou d'un humain est tracée.</p>
<table><tr><th>Horodatage</th><th>Acteur</th><th>Action</th><th>Cible</th><th>Détails</th></tr>
{% for r in rows %}<tr><td>{{r.ts}}</td><td><span class="chip {{'' if r.actor.startswith(('Agent','Orch')) else 'g'}}">{{r.actor}}</span></td><td>{{r.action}}</td><td>{{r.target}}</td><td>{{r.details}}</td></tr>{% endfor %}</table>""",
              rows=q("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100"))
    return page("audit", body)

if __name__ == "__main__":
    init()
    print("→ Ouvrez http://127.0.0.1:5000")
    app.run(debug=False, port=5000)
