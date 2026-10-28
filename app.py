
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from agents import run_agents


# CONFIGURATION
st.set_page_config(
    page_title="LogiMind | Data Governance",
    page_icon="📦",
    layout="wide"
)


# STYLE DE L'INTERFACE
st.markdown("""
<style>
.stApp {
    background-color: #F5F7FB;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
[data-testid="stSidebar"] {
    background-color: #17243A;
}
[data-testid="stSidebar"] * {
    color: white;
}
.hero {
    background: linear-gradient(120deg, #17243A, #254B69);
    padding: 28px;
    border-radius: 18px;
    color: white;
    margin-bottom: 22px;
}
.hero p {
    color: #D8E6F3;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 16px;
    border: 1px solid #E5EAF2;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# DONNEES DE DEMONSTRATION
def sample_data():
    return pd.DataFrame([
        ["CMD001", "CL001", "0612345678",
         "12 rue des Fleurs, Rabat", "2026-10-22", "A livrer", 250],
        ["CMD002", "CL002", "",
         "8 avenue Hassan II, Kenitra", "2026-10-22", "A livrer", 180],
        ["CMD003", "CL003", "0622334455",
         "Casablanca", "2026-10-23", "A livrer", 320],
        ["CMD004", "CL004", "0633445566",
         "5 boulevard Zerktouni, Casablanca", "2026-15-40", "A livrer", 95],
        ["CMD005", "CL005", "0644556677",
         "20 rue Ibn Sina, Fes", "2026-10-24", "A livrer", 410],
        ["CMD005", "CL005", "0644556677",
         "20 rue Ibn Sina, Fes", "2026-10-24", "A livrer", 410],
        ["CMD007", "CL007", "0677889900",
         "3 rue des Ecoles, Tanger", "2026-10-25", "A livrer", 135],
        ["CMD008", "CL008", "0688990011",
         "", "2026-10-25", "A livrer", 220],
        ["CMD009", "CL009", "0699001122",
         "14 avenue Mohammed V, Meknes", "2026-10-26", "A livrer", 75],
        ["CMD010", "CL010", "0600112233",
         "2 rue Al Qods, Agadir", "2026-10-27", "A livrer", 160],
    ], columns=[
        "commande_id",
        "client_id",
        "telephone",
        "adresse",
        "date_livraison",
        "statut",
        "montant"
    ])


# INITIALISATION DE LA SESSION
if "data" not in st.session_state:
    st.session_state.data = sample_data()

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "decisions" not in st.session_state:
    st.session_state.decisions = {}

if "history" not in st.session_state:
    st.session_state.history = []


# OUTILS POUR L'INTERFACE
def reset_analysis():
    st.session_state.analysis = None
    st.session_state.decisions = {}


def record_history(action, detail, responsable="Système",
                   commentaire=""):
    st.session_state.history.append({
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Action": action,
        "Détail": detail,
        "Responsable": responsable,
        "Commentaire": commentaire
    })


# NAVIGATION
with st.sidebar:
    st.markdown("# 📦 LogiMind")
    st.caption("DATA GOVERNANCE")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Vue d'ensemble",
            "Données & analyse",
            "Agents",
            "Validation humaine",
            "Historique & résultats"
        ]
    )

    st.divider()
    st.caption("Prototype pédagogique")
    st.caption("Les décisions critiques restent supervisées par un humain.")


# EN-TETE
st.markdown("""
<div class="hero">
    <h1>LogiMind</h1>
    <p>Fiabiliser les données pour anticiper les risques de livraison.</p>
    <p>Qualité · Documentation · Linéage · Orchestration</p>
</div>
""", unsafe_allow_html=True)


# PAGE 1 : VUE D'ENSEMBLE
if page == "Vue d'ensemble":
    st.subheader("Tableau de bord")
    st.write(
        "Identifiez les problèmes de données avant la préparation "
        "des tournées de livraison."
    )

    data = st.session_state.data
    analysis = st.session_state.analysis

    total_issues = (
        0 if analysis is None else len(analysis["anomalies"])
    )

    pending = 0
    accepted = 0
    rejected = 0

    if analysis is not None:
        for i in range(total_issues):
            decision = st.session_state.decisions.get(i)
            if decision is None:
                pending += 1
            elif decision["decision"] == "Acceptée":
                accepted += 1
            else:
                rejected += 1

    a, b, c, d = st.columns(4)
    a.metric("Commandes", len(data))
    b.metric("Anomalies", total_issues)
    c.metric("En attente", pending)
    d.metric("Décisions acceptées", accepted)

    st.subheader("Parcours de gouvernance")

    cols = st.columns(4)
    steps = [
        ("01", "Importer", "CSV de livraison"),
        ("02", "Analyser", "Agents spécialisés"),
        ("03", "Prioriser", "Orchestrateur"),
        ("04", "Valider", "Responsable Data")
    ]

    for col, (num, title, description) in zip(cols, steps):
        with col:
            st.markdown(f"### {num}")
            st.markdown(f"**{title}**")
            st.caption(description)

    st.info(
        "LogiMind détecte les anomalies, propose des actions et conserve "
        "les décisions humaines. Il ne corrige pas automatiquement "
        "les données dans cette version."
    )


# PAGE 2 : DONNEES ET ANALYSE
elif page == "Données & analyse":
    st.subheader("Importer les données de livraison")

    st.write(
        "Utilisez le jeu de démonstration ou importez un fichier CSV. "
        "Pour cette version, les colonnes attendues sont :"
    )

    st.code(
        "commande_id, client_id, telephone, adresse, "
        "date_livraison, statut, montant"
    )

    uploaded = st.file_uploader(
        "Choisir un fichier CSV",
        type=["csv"]
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Utiliser les données de démonstration",
            use_container_width=True
        ):
            st.session_state.data = sample_data()
            reset_analysis()
            st.success("Données de démonstration chargées.")

    with col2:
        if st.button(
            "Importer mon CSV",
            use_container_width=True,
            disabled=uploaded is None
        ):
            try:
                st.session_state.data = pd.read_csv(uploaded)
                reset_analysis()
                st.success("Fichier CSV importé.")
            except Exception as e:
                st.error(f"Erreur de lecture du fichier : {e}")

    st.subheader("Aperçu des données")
    st.dataframe(
        st.session_state.data,
        use_container_width=True,
        hide_index=True
    )

    if st.button(
        "Lancer l'analyse des agents",
        type="primary",
        use_container_width=True
    ):
        try:
            result = run_agents(st.session_state.data)

            st.session_state.analysis = result
            st.session_state.decisions = {}

            record_history(
                "Analyse lancée",
                f"{len(result['anomalies'])} anomalie(s) détectée(s)"
            )

            st.success("Analyse terminée.")

        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")

    analysis = st.session_state.analysis

    if analysis is not None:
        st.divider()
        st.subheader("Résultats de l'analyse")

        anomalies = analysis["anomalies"]

        if anomalies.empty:
            st.success("Aucune anomalie détectée par les règles configurées.")
        else:
            st.dataframe(
                anomalies[[
                    "commande_id",
                    "type",
                    "agent",
                    "priority",
                    "detail",
                    "recommendation"
                ]],
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "Priorité illustrative = gravité × impact. "
                "Le score ne constitue pas une probabilité réelle "
                "d'échec de livraison."
            )

        st.subheader("Documentation proposée")
        st.dataframe(
            analysis["documentation"],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("Traçabilité des colonnes")
        st.dataframe(
            analysis["lineage"],
            use_container_width=True,
            hide_index=True
        )


# PAGE 3 : AGENTS
elif page == "Agents":
    st.subheader("L'équipe LogiMind")
    st.write(
        "Quatre agents spécialisés collaborent pour fiabiliser "
        "les données de livraison avant leur utilisation."
    )

    agent_info = [
        (
            "🧠 1. Orchestrateur",
            "Coordonne le processus d'analyse, lance les contrôles "
            "et rassemble les résultats pour préparer les priorités."
        ),
        (
            "🛡️ 2. Agent Qualité",
            "Détecte les valeurs manquantes, les doublons, "
            "les téléphones suspects, les adresses incomplètes "
            "et les dates invalides."
        ),
        (
            "📚 3. Agent Documentation",
            "Décrit les colonnes du fichier et aide à comprendre "
            "les données analysées."
        ),
        (
            "🔗 4. Agent Linéage",
            "Trace la source du fichier et les étapes du traitement "
            "pour faciliter la traçabilité."
        )
    ]

    for name, description in agent_info:
        with st.container(border=True):
            st.markdown(f"### {name}")
            st.write(description)

    st.divider()
    st.subheader("Cycle de collaboration")
    
    st.subheader("État des agents")

    st.write(
        "Suivez l'état de chaque agent pendant le traitement."
    )

    noms_agents = [
        "Orchestrateur",
        "Qualité",
        "Documentation",
        "Linéage"
    ]

    # États de démonstration : ils ne sont pas encore
    # reliés à l'exécution réelle des agents.
    etats = [
        "Terminé",
        "En cours",
        "Bloqué",
        "Terminé"
    ]

    valeurs = {
        "Terminé": 0,
        "En cours": 1,
        "Bloqué": 2
    }

    couleurs = [
        [0, 0, 0.49, "#2ca02c"],
        [0.5, "#f39c12"],
        [1, "#d62728"]
    ]

    matrice = [[valeurs[etat] for etat in etats]]

    fig_heatmap = px.imshow(
        matrice,
        x=noms_agents,
        y=["État"],
        color_continuous_scale=[
            [0, "#2ca02c"],
            [0.499, "#2ca02c"],
            [0.5, "#f39c12"],
            [0.999, "#f39c12"],
            [1, "#d62728"]
        ],
        zmin=0,
        zmax=2,
        aspect="auto"
    )

    fig_heatmap.update_traces(
        text=[etats],
        texttemplate="%{text}"
    )

    fig_heatmap.update_layout(
        height=220,
        coloraxis_showscale=False,
        xaxis=dict(side="top"),
        yaxis=dict(showticklabels=False)
    )

    st.plotly_chart(
        fig_heatmap,
        use_container_width=True
    )

    st.caption(
        "Attention : les états affichés sont fictifs pour le moment. "
        "La prochaine étape consistera à les relier à l'exécution réelle."
    )

    
    


    steps = [
        ("1. Importation", "Le responsable importe un fichier CSV."),
        ("2. Contrôle qualité", "L'agent Qualité recherche les anomalies."),
        ("3. Documentation", "L'agent Documentation décrit les colonnes."),
        ("4. Traçabilité", "L'agent Linéage conserve les informations de provenance."),
        ("5. Synthèse", "L'Orchestrateur rassemble les résultats et les priorités."),
        ("6. Validation humaine", "Le responsable accepte ou rejette les recommandations.")
    ]

    for title, description in steps:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.write(description)

    analysis = st.session_state.analysis

    if analysis is None:
        st.info(
            "Pour voir les résultats de la collaboration, "
            "ouvrez «  Données & analyse» et lancez une analyse."
        )
    else:
        anomalies = analysis["anomalies"]

        st.success("Analyse disponible : les résultats sont prêts à être examinés.")
        col1, col2, col3 = st.columns(3)
        col1.metric("Anomalies détectées", len(anomalies))
        col2.metric(
            "Agents concernés",
            anomalies["agent"].nunique() if not anomalies.empty else 0
        )
        col3.metric(
            "Commandes concernées",
            anomalies["commande_id"].nunique() if not anomalies.empty else 0
        )

        st.write("**Résultats regroupés par agent**")

        if not anomalies.empty:
            st.dataframe(
                anomalies.groupby("agent").size().reset_index(
                    name="Nombre d'anomalies"
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Aucune anomalie n'a été détectée.")

    st.warning(
        "Limite du prototype : les agents utilisent actuellement "
        "des règles Python. L'Orchestrateur rassemble les résultats, "
        "mais les agents ne sont pas encore des agents autonomes basés "
        "sur un modèle de langage (LLM). Le linéage reste simplifié."
    )



# PAGE 4 : VALIDATION HUMAINE
elif page == "Validation humaine":
    st.subheader("Centre de validation")

    analysis = st.session_state.analysis

    if analysis is None:
        st.info("Lancez d'abord une analyse dans « Données & analyse ».")

    elif analysis["anomalies"].empty:
        st.success("Aucune recommandation à valider.")

    else:
        anomalies = analysis["anomalies"]

        st.write(
            "Examinez chaque recommandation. Accepter une recommandation "
            "ne signifie pas que la donnée a été automatiquement corrigée."
        )

        for i, issue in anomalies.iterrows():
            with st.container(border=True):
                st.markdown(
                    f"### {issue['commande_id']} — {issue['type']}"
                )

                st.write(f"**Agent :** {issue['agent']}")
                st.write(f"**Priorité :** {issue['priority']} / 25")
                st.write(f"**Constat :** {issue['detail']}")
                st.write(
                    f"**Recommandation :** {issue['recommendation']}"
                )

                current = st.session_state.decisions.get(i)

                if current is not None:
                    st.success(
                        f"Décision : {current['decision']} — "
                        f"{current['responsable']}"
                    )
                    if current["commentaire"]:
                        st.caption(current["commentaire"])

                else:
                    with st.form(key=f"decision_form_{i}"):
                        responsable = st.text_input(
                            "Nom ou rôle du responsable",
                            value="Responsable Data",
                            key=f"responsable_{i}"
                        )

                        commentaire = st.text_input(
                            "Commentaire (facultatif)",
                            key=f"commentaire_{i}"
                        )

                        choix = st.radio(
                            "Décision",
                            ["Accepter", "Rejeter"],
                            horizontal=True,
                            key=f"choix_{i}"
                        )

                        submitted = st.form_submit_button(
                            "Enregistrer la décision"
                        )

                    if submitted:
                        decision = (
                            "Acceptée"
                            if choix == "Accepter"
                            else "Rejetée"
                        )

                        record = {
                            "decision": decision,
                            "responsable": responsable.strip()
                            or "Responsable Data",
                            "commentaire": commentaire.strip(),
                            "date": datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        }

                        st.session_state.decisions[i] = record

                        record_history(
                            decision,
                            f"{issue['commande_id']} — {issue['type']}",
                            record["responsable"],
                            record["commentaire"]
                        )

                        st.rerun()


# PAGE 5 : HISTORIQUE ET RESULTATS
elif page == "Historique & résultats":
    st.subheader("Historique des actions")

    if st.session_state.history:
        st.dataframe(
            pd.DataFrame(st.session_state.history),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info(
            "L'historique apparaîtra après le lancement d'une analyse "
            "ou l'enregistrement d'une décision."
        )

    st.divider()
    st.subheader("Bilan de l'analyse")

    analysis = st.session_state.analysis

    if analysis is None:
        st.info("Lancez d'abord une analyse.")

    else:
        anomalies = analysis["anomalies"]
        total = len(anomalies)

        accepted = sum(
            decision["decision"] == "Acceptée"
            for decision in st.session_state.decisions.values()
        )

        rejected = sum(
            decision["decision"] == "Rejetée"
            for decision in st.session_state.decisions.values()
        )

        pending = total - accepted - rejected

        metrics = pd.DataFrame({
            "Indicateur": [
                "Anomalies détectées",
                "Recommandations acceptées",
                "Recommandations rejetées",
                "Décisions en attente"
            ],
            "Nombre": [total, accepted, rejected, pending]
        })

        st.dataframe(
            metrics,
            use_container_width=True,
            hide_index=True
        )

        fig = px.bar(
            metrics,
            x="Indicateur",
            y="Nombre",
            title="Bilan des recommandations"
        )

        st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Les décisions et l'historique sont conservés en mémoire "
            "pendant la session. Cette version ne modifie pas les données "
            "et ne sauvegarde pas encore les décisions dans PostgreSQL."
        )


# PIED DE PAGE
st.divider()
st.caption(
    "LogiMind — Prototype pédagogique | "
    "Analyse des données de livraison | Validation humaine requise"
)
