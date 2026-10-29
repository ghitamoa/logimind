
import pandas as pd

import json
import os
import re
import streamlit as st
from google import genai



# COLONNES ATTENDUES PAR LOGIMIND
REQUIRED_COLUMNS = [
    "commande_id",
    "client_id",
    "telephone",
    "adresse",
    "date_livraison",
    "statut",
    "montant"
]


# AGENT 1 : QUALITE DES DONNEES
def agent_qualite(df):
    anomalies = []

    # Reinitialiser les numeros de lignes pour garder
    # une correspondance simple avec le tableau analyse.
    data = df.reset_index(drop=True).copy()

    # Detecter les identifiants de commande dupliques.
    doublons = (
        data["commande_id"].notna()
        & data["commande_id"].duplicated(keep=False)
    )

    for i, row in data.iterrows():
        commande = row["commande_id"]
        commande = (
            str(commande)
            if pd.notna(commande)
            else "Non renseignee"
        )

        # Fonction locale pour ajouter une anomalie.
        def ajouter_anomalie(
            type_anomalie,
            gravite,
            impact,
            detail,
            recommandation
        ):
            anomalies.append({
                "commande_id": commande,
                "type": type_anomalie,
                "agent": "Qualite",
                "severity": gravite,
                "impact": impact,
                "priority": gravite * impact,
                "detail": detail,
                "recommendation": recommandation
            })

        # Controle des doublons.
        if doublons.iloc[i]:
            ajouter_anomalie(
                "Commande en double",
                4,
                5,
                "Cet identifiant de commande apparait plusieurs fois.",
                "Verifier les commandes avant de confirmer la tournee."
            )

        # Controle du telephone.
        telephone = row["telephone"]

        if pd.isna(telephone) or not str(telephone).strip():
            ajouter_anomalie(
                "Telephone manquant",
                4,
                4,
                "Le numero de telephone est absent.",
                "Demander la verification du contact client."
            )
        else:
            chiffres = "".join(
                caractere
                for caractere in str(telephone)
                if caractere.isdigit()
            )

            if len(chiffres) < 8:
                ajouter_anomalie(
                    "Telephone suspect",
                    3,
                    4,
                    "Le numero semble trop court.",
                    "Verifier le numero aupres de la source."
                )

        # Controle de l'adresse.
        adresse = row["adresse"]

        if pd.isna(adresse):
            adresse = ""
        else:
            adresse = str(adresse).strip()

        if not adresse or not any(
            caractere.isdigit() for caractere in adresse
        ):
            ajouter_anomalie(
                "Adresse absente ou incomplete",
                4,
                4,
                "L'adresse est vide ou ne contient pas de numero de voie.",
                "Faire verifier et completer l'adresse avant la tournee."
            )

        # Controle de la date.
        date_livraison = pd.to_datetime(
            row["date_livraison"],
            errors="coerce"
        )

        if pd.isna(date_livraison):
            ajouter_anomalie(
                "Date invalide",
                3,
                4,
                "La date de livraison ne peut pas etre interpretee.",
                "Verifier la date avec la source de reference."
            )

        # Controle du montant.
        montant = pd.to_numeric(
            pd.Series([row["montant"]]),
            errors="coerce"
        ).iloc[0]

        if pd.isna(montant) or montant < 0:
            ajouter_anomalie(
                "Montant invalide",
                3,
                3,
                "Le montant est manquant, non numerique ou negatif.",
                "Verifier le montant dans le systeme source."
            )

    colonnes = [
        "commande_id",
        "type",
        "agent",
        "severity",
        "impact",
        "priority",
        "detail",
        "recommendation"
    ]

    resultat = pd.DataFrame(anomalies, columns=colonnes)

    if not resultat.empty:
        resultat = resultat.sort_values(
            "priority",
            ascending=False
        ).reset_index(drop=True)

    return resultat


# AGENT 2 : DOCUMENTATION

def agent_documentation(df):
    descriptions = {
        "commande_id": "Identifiant unique de la commande.",
        "client_id": "Identifiant du client.",
        "telephone": "Numéro de contact du destinataire.",
        "adresse": "Adresse de livraison du colis.",
        "date_livraison": "Date prévue pour la livraison.",
        "statut": "État actuel de la commande.",
        "montant": "Montant associé à la commande."
    }

    descriptions_gemini = {}

    # Récupération sécurisée de la clé API
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    
        except Exception as e:
            print(
                f"Erreur Gemini : {type(e).__name__}: "
                f"{str(e)[:500]}"
            )
            st.warning(
                "Gemini est momentanément indisponible. "
                "Consultez les logs de Streamlit Cloud."
            )


    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    # Demande de descriptions à Gemini
    if api_key:
        try:
            client = genai.Client(api_key=api_key)

            colonnes = [str(col) for col in df.columns]

            prompt = f"""
Tu es un assistant spécialisé en gouvernance des données.

Pour chaque colonne de cette liste :
{json.dumps(colonnes, ensure_ascii=False)}

Propose une description courte, claire et professionnelle
en français, adaptée à un fichier de commandes de livraison.

Retourne uniquement un objet JSON valide.
Chaque clé doit être le nom exact d'une colonne et chaque
valeur doit être sa description.
N'invente pas d'informations qui ne sont pas connues.
"""

            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt
            )

            texte = response.text or ""

            # Extraction du JSON produit par le modèle
            correspondance = re.search(
                r"\{.*\}",
                texte,
                re.DOTALL
            )

            if correspondance:
                resultat = json.loads(correspondance.group(0))

                if isinstance(resultat, dict):
                    descriptions_gemini = resultat

        except Exception:
            st.warning(
                "Gemini est momentanément indisponible. "
                "Les descriptions de référence seront utilisées."
            )

    # Constitution du tableau de documentation
    documentation = []

    for colonne in df.columns:
        description = descriptions_gemini.get(colonne)

        if not isinstance(description, str) or not description.strip():
            description = descriptions.get(
                colonne,
                "Description à définir avec le responsable métier."
            )

        documentation.append({
            "Colonne": colonne,
            "Description proposée": description.strip(),
            "Validation": "À valider par le responsable métier"
        })

    return pd.DataFrame(documentation)



# AGENT 3 : LINEAGE
def agent_lineage(df, source="Fichier importe"):
    traces = []

    for colonne in df.columns:
        traces.append({
            "Source": source,
            "Colonne": colonne,
            "Etape": "Importation puis analyse",
            "Destination": "LogiMind",
            "Statut": "Colonne presente dans le fichier importe"
        })

    return pd.DataFrame(traces)


# AGENT 4 : ORCHESTRATEUR
def agent_orchestrateur(df, source="Fichier importe"):
    anomalies = agent_qualite(df)
    documentation = agent_documentation(df)
    lineage = agent_lineage(df, source)

    return {
        "anomalies": anomalies,
        "documentation": documentation,
        "lineage": lineage,
        "resume": {
            "nombre_commandes": len(df),
            "nombre_colonnes": len(df.columns),
            "nombre_anomalies": len(anomalies)
        }
    }


# FONCTION PRINCIPALE APPELEE PAR APP.PY
def run_agents(df, source="Fichier importe"):
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Les donnees importees ne sont pas un tableau valide.")

    if df.empty:
        raise ValueError("Le fichier ne contient aucune ligne.")

    colonnes_manquantes = [
        colonne
        for colonne in REQUIRED_COLUMNS
        if colonne not in df.columns
    ]

    if colonnes_manquantes:
        raise ValueError(
            "Colonnes manquantes : "
            + ", ".join(colonnes_manquantes)
            + ". Verifiez les noms de colonnes de votre CSV."
        )

    resultat = agent_orchestrateur(df, source)

    return resultat

