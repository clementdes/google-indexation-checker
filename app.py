import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from time import sleep

# Import des configurations depuis les fichiers annexes
from google_domains import DOMAIN_OPTIONS
from google_languages import HL_OPTIONS
from google_locations import GL_OPTIONS

def check_indexation(url, api_key, gl, hl, google_domain):
    """
    Vérifie si une URL est indexée sur Google via l'API ScaleSerp
    """
    api_url = "https://api.scaleserp.com/search"
    params = {
        "api_key": api_key,
        "q": f"site:{url}",
        "num": 1,
        "gl": gl,
        "hl": hl,
        "google_domain": google_domain
    }
    
    try:
        response = requests.get(api_url, params=params)
        data = response.json()
        
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

def main():
    # Configuration de la page
    st.set_page_config(page_title="Vérificateur d'indexation Google", layout="wide")

    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Clé API ScaleSerp", type="password")
        
        # Sélection du pays
        selected_country = st.selectbox(
            "Localisation Google (gl)", 
            options=list(GL_OPTIONS.keys()),
            format_func=lambda x: x
        )
        gl = GL_OPTIONS[selected_country]
        
        # Sélection de la langue d'interface
        selected_language = st.selectbox(
            "Langue d'interface (hl)", 
            options=list(HL_OPTIONS.keys()),
            format_func=lambda x: x
        )
        hl = HL_OPTIONS[selected_language]
        
        # Sélection du domaine Google
        selected_domain = st.selectbox(
            "Domaine Google",
            options=list(DOMAIN_OPTIONS.keys()),
            format_func=lambda x: x
        )
        google_domain = DOMAIN_OPTIONS[selected_domain]
        
        # Afficher les paramètres actuels
        st.divider()
        st.caption("Paramètres actuels :")
        st.code(f"gl={gl}&hl={hl}&google_domain={google_domain}")

    # Contenu principal
    st.title("Vérificateur d'indexation Google")

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
            urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            for i, url in enumerate(urls):
                progress = (i + 1) / len(urls)
                progress_bar.progress(progress)
                status_text.text(f"Vérification de {url}...")
                
                result = check_indexation(url, api_key, gl, hl, google_domain)
                results.append(result)
                
                sleep(1)
            
            # Créer un DataFrame avec les résultats
            df = pd.DataFrame(results)
            
            # Statistiques et visualisation
            st.header("Résultats")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # Camembert
                indexation_stats = df['indexed'].value_counts()
                fig = px.pie(
                    values=indexation_stats.values,
                    names=indexation_stats.index,
                    title="Répartition des URLs",
                    color_discrete_map={"Oui": "#00CC96", "Non": "#EF553B", "Erreur": "#636EFA"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistiques numériques
                total_urls = len(df)
                indexed_count = len(df[df['indexed'] == 'Oui'])
                non_indexed_count = len(df[df['indexed'] == 'Non'])
                error_count = len(df[df['indexed'] == 'Erreur'])
                
                st.metric("Total URLs", total_urls)
                st.metric("URLs indexées", f"{indexed_count} ({indexed_count/total_urls*100:.1f}%)")
                st.metric("URLs non indexées", f"{non_indexed_count} ({non_indexed_count/total_urls*100:.1f}%)")
                if error_count > 0:
                    st.metric("Erreurs", f"{error_count} ({error_count/total_urls*100:.1f}%)")
            
            with col2:
                # Tableaux des résultats
                tab1, tab2, tab3 = st.tabs(["URLs indexées", "URLs non indexées", "Erreurs"])
                
                with tab1:
                    urls_indexees = df[df['indexed'] == 'Oui']
                    if not urls_indexees.empty:
                        st.dataframe(
                            urls_indexees[['url', 'title']],
                            column_config={
                                "url": "URL",
                                "title": "Titre de la page"
                            },
                            hide_index=True
                        )
                    else:
                        st.info("Aucune URL indexée trouvée")
                
                with tab2:
                    urls_non_indexees = df[df['indexed'] == 'Non']
                    if not urls_non_indexees.empty:
                        st.dataframe(
                            urls_non_indexees[['url']],
                            hide_index=True
                        )
                    else:
                        st.info("Aucune URL non indexée trouvée")
                
                with tab3:
                    urls_en_erreur = df[df['indexed'] == 'Erreur']
                    if not urls_en_erreur.empty:
                        st.dataframe(
                            urls_en_erreur[['url', 'title']],
                            column_config={
                                "url": "URL",
                                "title": "Message d'erreur"
                            },
                            hide_index=True
                        )
                    else:
                        st.info("Aucune erreur")
            
            # Bouton de téléchargement
            st.divider()
            csv = df.to_csv(index=False)
            st.download_button(
                label="Télécharger les résultats (CSV)",
                data=csv,
                file_name="resultats_indexation.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
