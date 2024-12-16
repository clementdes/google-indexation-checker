import streamlit as st
import pandas as pd
import plotly.express as px
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# Import des configurations
from google_domains import DOMAIN_OPTIONS
from google_languages import HL_OPTIONS
from google_locations import GL_OPTIONS

async def check_indexation_async(session, url, api_key, gl, hl, google_domain):
    """
    Version asynchrone de la vérification d'indexation
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
        async with session.get(api_url, params=params) as response:
            data = await response.json()
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

async def process_urls_async(urls, api_key, gl, hl, google_domain, progress_bar, status_text):
    """
    Traite une liste d'URLs de manière asynchrone
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        chunk_size = 5  # Nombre de requêtes simultanées
        
        for i in range(0, len(urls), chunk_size):
            chunk = urls[i:i + chunk_size]
            chunk_tasks = [
                check_indexation_async(session, url, api_key, gl, hl, google_domain)
                for url in chunk
            ]
            
            # Exécuter les requêtes du chunk en parallèle
            chunk_results = await asyncio.gather(*chunk_tasks)
            tasks.extend(chunk_results)
            
            # Mettre à jour la progression
            progress = (i + len(chunk)) / len(urls)
            progress_bar.progress(progress)
            status_text.text(f"Traitement des URLs {i+1}-{min(i+chunk_size, len(urls))} sur {len(urls)}...")
            
            # Petite pause entre les chunks pour éviter de surcharger l'API
            await asyncio.sleep(0.5)
        
        return tasks

def main():
    # Configuration de la page
    st.set_page_config(page_title="Vérificateur d'indexation Google", layout="wide")

    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        api_key = st.text_input("Clé API ScaleSerp", type="password")
        
        selected_country = st.selectbox(
            "Localisation Google (gl)", 
            options=list(GL_OPTIONS.keys()),
            format_func=lambda x: x
        )
        gl = GL_OPTIONS[selected_country]
        
        selected_language = st.selectbox(
            "Langue d'interface (hl)", 
            options=list(HL_OPTIONS.keys()),
            format_func=lambda x: x
        )
        hl = HL_OPTIONS[selected_language]
        
        selected_domain = st.selectbox(
            "Domaine Google",
            options=list(DOMAIN_OPTIONS.keys()),
            format_func=lambda x: x
        )
        google_domain = DOMAIN_OPTIONS[selected_domain]
        
        st.divider()
        st.caption("Paramètres actuels :")
        st.code(f"gl={gl}&hl={hl}&google_domain={google_domain}")

    st.title("Vérificateur d'indexation Google")

    urls_input = st.text_area(
        "Entrez vos URLs (une par ligne)",
        height=200,
        help="Collez vos URLs ici, une par ligne"
    )

    if st.button("Vérifier l'indexation"):
        if not api_key:
            st.error("Veuillez entrer votre clé API ScaleSerp")
        elif not urls_input:
            st.error("Veuillez entrer au moins une URL")
        else:
            urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Exécuter le traitement asynchrone
            with ThreadPoolExecutor() as executor:
                loop = asyncio.new_event_loop()
                results = loop.run_until_complete(
                    process_urls_async(urls, api_key, gl, hl, google_domain, progress_bar, status_text)
                )
            
            # Créer le DataFrame avec les résultats
            df = pd.DataFrame(results)
            
            # Affichage des résultats (reste identique)
            st.header("Résultats")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                indexation_stats = df['indexed'].value_counts()
                fig = px.pie(
                    values=indexation_stats.values,
                    names=indexation_stats.index,
                    title="Répartition des URLs",
                    color_discrete_map={"Oui": "#00CC96", "Non": "#EF553B", "Erreur": "#636EFA"}
                )
                st.plotly_chart(fig, use_container_width=True)
                
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
