#!/usr/bin/env python
"""
Script pour réindexer uniquement les pages principales d'ESILV.
Supprime la collection actuelle et réindexe avec la nouvelle structuration améliorée.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin
sys.path.insert(0, str(Path(__file__).parent))

from rag.vector_store import vector_store
from config import settings
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from rag.document_processor import document_processor
from langchain_core.documents import Document
import json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Liste des pages principales importantes d'ESILV
MAIN_PAGES = [
    # Page d'accueil
    "https://www.esilv.fr/",
    
    # Formations principales
    "https://www.esilv.fr/formations",
    "https://www.esilv.fr/formations/cycle-ingenieur",
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures",
    "https://www.esilv.fr/formations/prepa-integree",
    
    # Majeures principales (spécialisations)
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/eco-innovation",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/finance",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/informatique",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/mechanical-engineering",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/actuariat",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/cyber-security",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/data-science",
    "https://www.esilv.fr/formations/cycle-ingenieur/majeures/ia",
    
    # Parcours importants
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours/parcours-start-up",
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours/parcours-souverainete-numerique-et-defense",
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours/parcours-ux-design",
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours/parcours-ingenieurs-daffaires",
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours/parcours-recherche",
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours/parcours-quantique",
    "https://www.esilv.fr/formations/cycle-ingenieur/parcours/parcours-convergence-hpc-ia",
    
    # Admissions
    "https://www.esilv.fr/admissions",
    "https://www.esilv.fr/admissions/concours-avenir-prepas",
    "https://www.esilv.fr/admissions/rencontrez-nous/journees-portes-ouvertes",
    "https://www.esilv.fr/admissions/rencontrez-nous/rendez-vous-personnalise",
    "https://www.esilv.fr/admissions/rencontrez-nous/salons-orientation-ingenieur",
    "https://www.esilv.fr/admissions/logement",
    
    # École / À propos
    "https://www.esilv.fr/ecole-ingenieurs/cursus",
    "https://www.esilv.fr/lecole",
    "https://www.esilv.fr/lecole/le-projet-pedagogique",
    "https://www.esilv.fr/lecole/mission-de-lesilv",
    "https://www.esilv.fr/lecole/10-bonnes-raisons-dintegrer-lesilv",
    "https://www.esilv.fr/lecole/la-transversalite",
    "https://www.esilv.fr/lecole/vie-etudiante",
    "https://www.esilv.fr/lecole/vie-etudiante/associations-etudiantes",
    "https://www.esilv.fr/lecole/agenda",
    "https://www.esilv.fr/lecole/reseaux",
    "https://www.esilv.fr/lecole/certification-blockchain-diplomes-esilv",
    
    # International
    "https://www.esilv.fr/international",
    "https://www.esilv.fr/en/international",
    "https://www.esilv.fr/en/international/incoming-outgoing-mobility",
    
    # Objectifs éducatifs
    "https://www.esilv.fr/formations/cycle-ingenieur/objectifs-educatifs-du-programme",
    
    # Apprentissage et double diplômes
    "https://www.esilv.fr/formations/cycle-ingenieur/apprentissage",
    "https://www.esilv.fr/formations/cycle-ingenieur/double-diplomes-cursus-ingenieur",
    
    # Parcours sportifs
    "https://www.esilv.fr/formations/parcours-sportifs-de-haut-niveau",
    
    # Entreprises et débouchés
    "https://www.esilv.fr/entreprises-debouches",
    "https://www.esilv.fr/entreprises-debouches/stages-ingenieurs",
    "https://www.esilv.fr/entreprises-debouches/deposer-une-offre",
    "https://www.esilv.fr/entreprises-debouches/relations-entreprises/taxe-apprentissage",
    
    # Recherche
    "https://www.esilv.fr/recherche/corps-professoral",
    "https://www.esilv.fr/en/faculty-research",
    "https://www.esilv.fr/en/faculty-research/faculty",
    
    # Vie étudiante
    "https://www.esilv.fr/lecole/vie-etudiante",
    "https://www.esilv.fr/en/student-life",
    "https://www.esilv.fr/en/student-life/student-associations",
    "https://www.esilv.fr/en/student-life/open-days",
    
    # Carrières
    "https://www.esilv.fr/en/careers",
    "https://www.esilv.fr/en/careers/corporate-relations",
]


async def delete_collection():
    """Supprime la collection ChromaDB actuelle."""
    logger.info("=" * 70)
    logger.info("SUPPRESSION DE LA COLLECTION ACTUELLE")
    logger.info("=" * 70)
    
    try:
        # Vérifier si la collection existe
        try:
            collection = vector_store.client.get_collection(name=vector_store.collection_name)
            count = collection.count()
            logger.info(f"Collection '{vector_store.collection_name}' trouvée avec {count} documents")
            
            # Supprimer la collection
            vector_store.client.delete_collection(name=vector_store.collection_name)
            logger.info(f"✅ Collection '{vector_store.collection_name}' supprimée avec succès")
        except Exception as e:
            if "does not exist" in str(e) or "not found" in str(e).lower():
                logger.info("ℹ️  La collection n'existe pas encore, pas besoin de la supprimer")
            else:
                logger.warning(f"⚠️  Erreur lors de la vérification/suppression: {e}")
                # Essayer de réinitialiser le client
                try:
                    vector_store.client.reset()
                    logger.info("✅ Base de données ChromaDB réinitialisée")
                except Exception as reset_error:
                    logger.error(f"❌ Erreur lors de la réinitialisation: {reset_error}")
                    raise
        
        # Réinitialiser le vectorstore pour forcer la création d'une nouvelle collection
        vector_store._vectorstore = None
        logger.info("✅ VectorStore réinitialisé")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression de la collection: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


async def scrape_page_simple(url: str) -> dict:
    """Scrape une page avec httpx + BeautifulSoup (fallback simple)."""
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements (scripts, styles, navigation, forms, cookies, etc.)
            unwanted_tags = ["script", "style", "nav", "footer", "aside", "header", 
                           "form", "noscript", "iframe", "svg", "button", "a"]
            for tag in unwanted_tags:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Remove cookie banners and consent popups
            for element in soup.find_all(class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['cookie', 'consent', 'gdpr', 'privacy', 'banner']
            )):
                element.decompose()
            
            # Remove navigation and menu elements by class/id
            navigation_keywords = ['menu', 'navigation', 'nav', 'breadcrumb', 'sidebar', 'widget']
            for keyword in navigation_keywords:
                for element in soup.find_all(class_=lambda x: x and keyword in x.lower()):
                    element.decompose()
                for element in soup.find_all(id=lambda x: x and keyword in x.lower()):
                    element.decompose()
            
            # Remove "Lire la suite", "Plus d'infos", and similar navigation text
            unwanted_text_patterns = [
                'lire la suite', 'lire la suite →', 'plus d\'infos', 'plus d\'infos',
                'images associées', 'image 1', 'image 2', 'image 3', 'image 4', 'image 5',
                'image 6', 'image 7', 'image 8', 'image 9', 'image 10',
                'prochains évènements', 'évènements', 'actualités', 'presse', 'actus', 'agenda',
                'projets', 'menu', 'english', 'français', 'recrutement', 'plan d\'accès',
                'mentions légales', 'brochure', 'candidature', 'en savoir plus',
                'demandez-nous une documentation', 'nos brochures en téléchargement'
            ]
            
            # Remove elements containing unwanted text
            for pattern in unwanted_text_patterns:
                for element in soup.find_all(string=lambda text: text and pattern.lower() in text.lower()):
                    parent = element.parent
                    if parent:
                        # Check if it's a link or button-like element
                        if parent.name in ['a', 'button', 'span'] or parent.get('class') and any(
                            kw in ' '.join(parent.get('class', [])).lower() for kw in ['link', 'button', 'read-more']
                        ):
                            parent.decompose()
                        # If it's standalone text, try to remove the parent paragraph/div
                        elif parent.name in ['p', 'div', 'li'] and len(parent.get_text().strip()) < 100:
                            # Only remove if the element is mostly just this unwanted text
                            if pattern.lower() in parent.get_text().lower():
                                parent.decompose()
            
            # Remove form elements
            for form in soup.find_all('form'):
                form.decompose()
            
            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else url.split('/')[-1] or 'ESILV Page'
            
            # Extract main content (prioritize main/article over body)
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if main_content:
                # Remove any remaining unwanted elements from main content
                for tag in ["script", "style", "form", "nav", "footer", "aside", "a", "button"]:
                    for element in main_content.find_all(tag):
                        element.decompose()
                
                # Remove elements with unwanted text from main content
                for pattern in unwanted_text_patterns:
                    for element in main_content.find_all(string=lambda text: text and pattern.lower() in text.lower()):
                        parent = element.parent
                        if parent and parent.name in ['a', 'button', 'span', 'p']:
                            if len(parent.get_text().strip()) < 150:  # Short elements likely navigation
                                parent.decompose()
                
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text: remove excessive whitespace, empty lines, and unwanted patterns
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Skip lines that are just unwanted patterns
                if any(pattern.lower() in line.lower() for pattern in unwanted_text_patterns):
                    continue
                # Skip very short lines that are likely navigation
                if len(line) < 10 and line.lower() in [p.lower() for p in unwanted_text_patterns]:
                    continue
                lines.append(line)
            
            text = '\n'.join(lines)
            
            # Final cleanup: remove repeated patterns and clean up
            import re
            # Remove multiple consecutive newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            # Remove lines that are just numbers or single characters
            text = '\n'.join([line for line in text.split('\n') if len(line.strip()) > 2 or line.strip().isdigit()])
            
            # Extract only relevant images (limit to 10 per page, prioritize main content)
            images = []
            if main_content:
                for img in main_content.find_all('img', limit=10):
                    img_src = img.get('src') or img.get('data-src')
                    if img_src:
                        if img_src.startswith('//'):
                            img_src = 'https:' + img_src
                        elif img_src.startswith('/'):
                            img_src = urljoin(url, img_src)
                        elif not img_src.startswith('http'):
                            img_src = urljoin(url, img_src)
                        if img_src.startswith('http') and img_src not in images:
                            images.append(img_src)
                            if len(images) >= 10:  # Limit to 10 images per page
                                break
            
            return {
                "title": title_text,
                "content": text,
                "url": url,
                "source": "esilv_website_httpx",
                "metadata": {
                    "source": url,
                    "url": url,
                    "title": title_text,
                    "images": json.dumps(images) if images else "",
                    "image_count": len(images)
                },
                "images": images
            }
    except Exception as e:
        logger.warning(f"Erreur lors du scraping de {url}: {e}")
        return None


async def reindex_main_pages():
    """Réindexe uniquement les pages principales."""
    logger.info("=" * 70)
    logger.info("RÉINDEXATION DES PAGES PRINCIPALES")
    logger.info("=" * 70)
    logger.info(f"Nombre de pages à indexer: {len(MAIN_PAGES)}")
    
    try:
        # Filtrer les URLs (exclure les PDFs et sitemaps)
        exclude_patterns = [r".*\.pdf$", r".*sitemap.*", r".*\.xml$"]
        filtered_urls = []
        for url in MAIN_PAGES:
            should_exclude = False
            for pattern in exclude_patterns:
                import re
                if re.match(pattern, url, re.IGNORECASE):
                    should_exclude = True
                    break
            if not should_exclude:
                filtered_urls.append(url)
        
        logger.info(f"URLs à scraper après filtrage: {len(filtered_urls)}")
        logger.info("URLs principales:")
        for i, url in enumerate(filtered_urls[:10], 1):
            logger.info(f"  {i}. {url}")
        if len(filtered_urls) > 10:
            logger.info(f"  ... et {len(filtered_urls) - 10} autres")
        
        # Scraper les URLs avec httpx (simple et fiable)
        logger.info("\nDébut du scraping avec httpx...")
        all_content = []
        
        # Scraper en parallèle avec limite de concurrence
        semaphore = asyncio.Semaphore(5)  # Max 5 requêtes simultanées
        
        async def scrape_with_limit(url):
            async with semaphore:
                return await scrape_page_simple(url)
        
        tasks = [scrape_with_limit(url) for url in filtered_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict) and result:
                all_content.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Erreur lors du scraping: {result}")
        
        logger.info(f"\n✅ Scraping terminé: {len(all_content)} pages scrapées")
        
        # Indexer le contenu avec la nouvelle structuration
        logger.info("\nDébut de l'indexation avec la nouvelle structuration...")
        
        total_chunks = 0
        indexed = 0
        errors = 0
        
        # Try to import filter_complex_metadata
        try:
            from langchain_community.vectorstores.utils import filter_complex_metadata
        except ImportError:
            def filter_complex_metadata(docs):
                for doc in docs:
                    if hasattr(doc, 'metadata') and isinstance(doc.metadata, dict):
                        filtered_meta = {}
                        for key, value in doc.metadata.items():
                            if isinstance(value, (list, dict)):
                                filtered_meta[key] = json.dumps(value) if value else ""
                            elif isinstance(value, (str, int, float, bool)) or value is None:
                                filtered_meta[key] = value
                            else:
                                filtered_meta[key] = str(value)
                        doc.metadata = filtered_meta
                return docs
        
        for content in all_content:
            try:
                # Ensure metadata is a dictionary
                metadata = content.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                
                # Add source and URL to metadata
                metadata["source"] = content.get("url", "")
                metadata["url"] = content.get("url", "")
                metadata["title"] = content.get("title", "")
                metadata["content_type"] = "web_page"
                metadata["file_type"] = "html"
                metadata["scraped_from"] = content.get("source", "esilv_website_httpx")
                
                # Add images to metadata (only store at source level, not in each chunk)
                # Limit to max 10 images per source
                images = content.get("images", [])
                if images:
                    image_urls = [img if isinstance(img, str) else img.get('url', '') for img in images[:10]]
                    # Store images only in source metadata, not in chunks
                    metadata["images"] = json.dumps(image_urls) if image_urls else ""
                    metadata["image_count"] = len(image_urls)
                else:
                    metadata["images"] = ""
                    metadata["image_count"] = 0
                
                # Create document
                doc = Document(
                    page_content=content["content"],
                    metadata=metadata
                )
                
                # Process and chunk with improved structure
                chunks = document_processor.text_splitter.split_documents([doc])
                
                # Add rich structured metadata to each chunk
                for i, chunk in enumerate(chunks):
                    chunk.metadata["chunk_index"] = i
                    chunk.metadata["total_chunks"] = len(chunks)
                    chunk.metadata["chunk_id"] = f"{metadata.get('title', 'page').replace(' ', '_')}_chunk_{i}"
                    chunk.metadata["content_type"] = "web_page"
                    chunk.metadata["file_type"] = "html"
                    chunk.metadata["chunk_length"] = len(chunk.page_content)
                    chunk.metadata["scraped_from"] = content.get("source", "esilv_website_httpx")
                    
                    # Don't store images in chunks - they're stored at source level only
                    # This reduces metadata bloat and improves performance
                
                # Filter complex metadata before adding to ChromaDB
                chunks = filter_complex_metadata(chunks)
                
                # Add to vector store
                vector_store.add_documents(chunks)
                
                total_chunks += len(chunks)
                indexed += 1
                
                logger.info(f"✅ Indexé: {content.get('title', content.get('url', 'unknown'))} - {len(chunks)} chunks")
                
            except Exception as e:
                errors += 1
                logger.error(f"❌ Erreur lors de l'indexation de {content.get('url', 'unknown')}: {e}")
                continue
        
        stats = {
            "indexed": indexed,
            "total_chunks": total_chunks,
            "errors": errors
        }
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ RÉINDEXATION TERMINÉE AVEC SUCCÈS")
        logger.info("=" * 70)
        logger.info(f"Statistiques d'indexation:")
        logger.info(f"  - Pages indexées: {stats.get('indexed', 0)}")
        logger.info(f"  - Chunks créés: {stats.get('total_chunks', 0)}")
        logger.info(f"  - Erreurs: {stats.get('errors', 0)}")
        
        # Vérifier le résultat
        try:
            collection = vector_store.client.get_collection(name=vector_store.collection_name)
            final_count = collection.count()
            logger.info(f"  - Documents dans la collection: {final_count}")
        except Exception as e:
            logger.warning(f"⚠️  Impossible de vérifier le nombre de documents: {e}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la réindexation: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


async def main():
    """Fonction principale."""
    logger.info("\n" + "=" * 70)
    logger.info("RÉINDEXATION DES PAGES PRINCIPALES ESILV")
    logger.info("=" * 70)
    logger.info("\nCe script va:")
    logger.info("  1. Supprimer la collection ChromaDB actuelle")
    logger.info("  2. Réindexer uniquement les pages principales d'ESILV")
    logger.info("  3. Utiliser la nouvelle structuration améliorée")
    logger.info("\n" + "=" * 70)
    
    # Demander confirmation
    response = input("\n⚠️  Êtes-vous sûr de vouloir supprimer la collection actuelle ? (oui/non): ")
    if response.lower() not in ['oui', 'o', 'yes', 'y']:
        logger.info("❌ Opération annulée par l'utilisateur")
        return
    
    try:
        # Étape 1: Supprimer la collection
        await delete_collection()
        
        # Étape 2: Réindexer les pages principales
        stats = await reindex_main_pages()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ RÉINDEXATION COMPLÈTE AVEC SUCCÈS!")
        logger.info("=" * 70)
        logger.info(f"\nVous pouvez maintenant tester le RAG avec des questions comme:")
        logger.info("  - 'Quelles sont les majeures de l'ESILV ?'")
        logger.info("  - 'Comment s'inscrire à l'ESILV ?'")
        logger.info("  - 'Quels sont les parcours proposés ?'")
        logger.info("\n")
        
    except KeyboardInterrupt:
        logger.info("\n❌ Opération interrompue par l'utilisateur")
    except Exception as e:
        logger.error(f"\n❌ Erreur fatale: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

