# Migration de Firecrawl vers Crawl4AI

## Résumé

Le projet a été migré de **Firecrawl** vers **Crawl4AI** pour les raisons suivantes :
- ✅ **Open Source** : Pas de limites d'API ou de coûts
- ✅ **Pas de clé API requise** : Installation locale uniquement
- ✅ **Support JavaScript** : Basé sur Playwright pour gérer le contenu dynamique
- ✅ **Extraction d'images** : Récupère automatiquement les images avec leur contexte
- ✅ **Traitement concurrent** : Scrape plusieurs URLs en parallèle

## Changements effectués

### 1. Dépendances (`requirements.txt`)
- ❌ Supprimé : `firecrawl-py>=1.0.0`
- ✅ Ajouté : `crawl4ai>=0.3.0`

### 2. Nouveaux fichiers
- ✅ `backend/utils/crawl4ai_scraper.py` : Nouveau scraper basé sur Crawl4AI
  - Classe `Crawl4AIScraper` avec support async
  - Extraction d'images depuis `result.media['images']`
  - Traitement concurrent avec `asyncio.Semaphore`
  - Indexation automatique dans ChromaDB

### 3. Fichiers modifiés

#### `backend/scrape_esilv.py`
- Migration vers `async/await` pour utiliser Crawl4AI
- Utilise `crawl4ai_scraper.scrape_urls()` au lieu de Firecrawl
- Filtre automatique des fichiers XML sitemap
- Support du traitement concurrent (5 URLs en parallèle par défaut)

#### `backend/api/documents.py`
- Endpoints `/scrape-esilv` et `/scrape-esilv-sync` mis à jour
- Utilise `crawl4ai_scraper` au lieu de `firecrawl_scraper`
- Support async pour les tâches en arrière-plan

#### `backend/agents/retrieval_agent.py`
- Extraction des images depuis les métadonnées des documents
- Format markdown pour les images : `[![alt](img_url)](img_url)`
- Limite de 5 images par chunk pour éviter la surcharge

#### `frontend/components/ChatInterface.tsx`
- Affichage des images avec liens cliquables
- Support du format markdown `[![alt](img_url)](img_url)`
- Images cliquables qui ouvrent dans un nouvel onglet
- Gestion des erreurs de chargement d'images

#### `backend/config.py`
- Suppression de la configuration `firecrawl_api_key`
- Ajout d'un commentaire sur Crawl4AI (pas de clé API requise)

## Utilisation

### Installation

```bash
pip install crawl4ai>=0.3.0
```

Crawl4AI nécessite Playwright. Si ce n'est pas déjà installé :

```bash
playwright install chromium
```

### Scraping

#### Via script Python

```bash
cd backend
python scrape_esilv.py
```

Le script charge automatiquement les URLs depuis `esilv_urls.txt` et scrape chaque URL (mode "scrape" - pas de crawl).

#### Via API

```bash
curl -X POST "http://localhost:8000/api/documents/scrape-esilv-sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sections": ["https://www.esilv.fr/formations"],
    "exclude_patterns": [".*\\.pdf$"],
    "max_concurrent": 5
  }'
```

### Fonctionnalités

1. **Extraction d'images** : Les images sont automatiquement extraites et stockées dans les métadonnées
2. **Affichage dans le chat** : Les images apparaissent dans les réponses avec des liens cliquables
3. **Traitement concurrent** : Jusqu'à 5 URLs scrapées en parallèle (configurable)
4. **Filtrage automatique** : Les PDFs et fichiers sitemap XML sont automatiquement exclus

## Avantages de Crawl4AI

- ✅ **Pas de limites** : Open source, pas de quotas d'API
- ✅ **Performance** : Traitement concurrent pour scraper rapidement
- ✅ **Images** : Extraction automatique avec contexte
- ✅ **JavaScript** : Support complet du contenu dynamique via Playwright
- ✅ **Markdown propre** : Génère du Markdown optimisé pour RAG

## Notes

- Les fichiers Firecrawl (`firecrawl_scraper.py`, `firecrawl_langchain.py`) peuvent être supprimés si non utilisés ailleurs
- La configuration `.env` n'a plus besoin de `FIRECRAWL_API_KEY`
- Crawl4AI utilise Playwright qui nécessite des navigateurs installés (chromium, firefox, ou webkit)

