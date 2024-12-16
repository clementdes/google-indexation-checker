import streamlit as st
import requests
import pandas as pd
from time import sleep

def check_indexation(url, api_key):
    """
    Vérifie si une URL est indexée sur Google via l'API ScaleSerp
    """
    # Construire l'URL de l'API
    api_url = "https://api.scaleserp.com/search"
    params = {
        "api_key": api_key,
        "q": f"site:{url}",
        "num": 1
    }
    
    try:
        response = requests.get(api_url, params=params)
        data = response.json()
        
        # Vérifier si des résultats organiques sont présents
        is_indexed = len(data.get("organic_results", [])) > 0
        title = data.get("organic_results", [{}])[0].get("title", "") if is_indexed else ""
        
        return {
            "url": url,
            "indexed": "Oui" if is_indexed else "Non",
            "title": title
        }
    except Exception as e:
        return {
            "url": url,
            "indexed": "Erreur",
            "title": str(e)
        }

# Configuration de la page Streamlit
st.set_page_config(page_title="Vérificateur d'indexation Google", layout="wide")

# Titre de l'application
st.title("Vérificateur d'indexation Google")

# Champ pour l'API key
api_key = st.text_input("Clé API ScaleSerp", type="password")

# Zone de texte pour les URLs
urls_input = st.text_area(
    "Entrez vos URLs (une par ligne)",
    height=200,
    help="Collez vos URLs ici, une par ligne"
)

# Bouton pour lancer la vérification
if st.button("Vérifier l'indexation"):
    if not api_key:
        st.error("Veuillez entrer votre clé API ScaleSerp")
    elif not urls_input:
        st.error("Veuillez entrer au moins une URL")
    else:
        # Convertir le texte en liste d'URLs
        urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
        
        # Créer une barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        for i, url in enumerate(urls):
            # Mettre à jour la barre de progression
            progress = (i + 1) / len(urls)
            progress_bar.progress(progress)
            status_text.text(f"Vérification de {url}...")
            
            # Vérifier l'indexation
            result = check_indexation(url, api_key)
            results.append(result)
            
            # Pause pour éviter de surcharger l'API
            sleep(1)
        
        # Créer un DataFrame avec les résultats
        df = pd.DataFrame(results)
        
        # Afficher les résultats
        st.success("Vérification terminée!")
        st.dataframe(
            df,
            column_config={
                "url": "URL",
                "indexed": "Indexé",
                "title": "Titre de la page"
            },
            hide_index=True
        )
        
        # Ajouter un bouton de téléchargement
        csv = df.to_csv(index=False)
        st.download_button(
            label="Télécharger les résultats (CSV)",
            data=csv,
            file_name="resultats_indexation.csv",
            mime="text/csv"
        )