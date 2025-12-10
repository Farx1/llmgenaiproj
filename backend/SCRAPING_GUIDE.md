# Guide de Scraping ESILV avec Firecrawl

Ce guide explique comment scraper toutes les pages du site ESILV en utilisant Firecrawl.

## Prérequis

1. **Clé API Firecrawl** : Obtenez votre clé sur https://firecrawl.dev
2. **Configuration** : Ajoutez `FIRECRAWL_API_KEY=fc-YOUR_API_KEY` dans le fichier `.env`

## Méthodes de Scraping

### Méthode 1 : Script Python (Recommandé)

Le script `scrape_esilv.py` permet de scraper plusieurs URLs avec exclusion automatique des PDFs.

#### Option A : Utiliser un fichier de URLs

1. Créez un fichier `esilv_urls.txt` dans le dossier `backend/` :
```bash
# Exemple de contenu
https://www.esilv.fr
https://www.esilv.fr/formations
https://www.esilv.fr/admissions
https://www.esilv.fr/ecole
```

2. Lancez le script :
```bash
cd backend
python scrape_esilv.py
```

#### Option B : URLs en ligne de commande

```bash
cd backend
python scrape_esilv.py https://www.esilv.fr https://www.esilv.fr/formations
```

#### Option C : URL par défaut

Si aucun fichier ou argument n'est fourni, le script utilise `https://www.esilv.fr` par défaut.

### Méthode 2 : API REST

#### Endpoint Synchrone (attendre les résultats)

```bash
curl -X POST "http://localhost:8000/api/documents/scrape-esilv-sync" \
  -H "Content-Type: application/json" \
  -d '{
    "sections": [
      "https://www.esilv.fr",
      "https://www.esilv.fr/formations",
      "https://www.esilv.fr/admissions"
    ],
    "limit": 1000,
    "use_langchain": true,
    "exclude_patterns": [".*\\.pdf$"]
  }'
```

#### Endpoint Asynchrone (en arrière-plan)

```bash
curl -X POST "http://localhost:8000/api/documents/scrape-esilv" \
  -H "Content-Type: application/json" \
  -d '{
    "sections": ["https://www.esilv.fr/formations"],
    "limit": 1000,
    "exclude_patterns": [".*\\.pdf$"]
  }'
```

## Paramètres

- **sections/urls** : Liste d'URLs de départ (Firecrawl découvrira automatiquement toutes les pages liées)
- **limit** : Nombre maximum de pages à scraper par URL (défaut: 50, recommandé: 1000 pour tout scraper)
- **exclude_patterns** : Patterns regex pour exclure des URLs (défaut: `[".*\\.pdf$"]` pour exclure les PDFs)
- **use_langchain** : Utiliser LangChain FireCrawlLoader (recommandé: `true`)

## Fonctionnalités

✅ **Découverte automatique** : Firecrawl découvre et scrape automatiquement toutes les pages accessibles depuis les URLs de départ

✅ **Exclusion des PDFs** : Les PDFs sont automatiquement exclus (configurable)

✅ **Support JavaScript** : Firecrawl gère automatiquement le contenu JavaScript et dynamique

✅ **Markdown optimisé RAG** : Le contenu est converti en Markdown optimisé pour la recherche vectorielle

✅ **Intégration LangChain** : Les documents sont directement compatibles avec LangChain

## Exemple Complet

```python
# backend/scrape_esilv.py
from utils.firecrawl_langchain import scrape_with_langchain_loader, index_firecrawl_documents

# URLs à scraper
urls = [
    "https://www.esilv.fr",
    "https://www.esilv.fr/formations",
    "https://www.esilv.fr/admissions"
]

# Scraper chaque URL
all_docs = []
for url in urls:
    docs = scrape_with_langchain_loader(
        url=url,
        mode="crawl",  # "crawl" pour toutes les pages, "scrape" pour une seule
        exclude_patterns=[r".*\.pdf$"]  # Exclure les PDFs
    )
    all_docs.extend(docs)

# Indexer dans ChromaDB
stats = index_firecrawl_documents(all_docs)
print(f"Indexed {stats['indexed']} documents, {stats['chunks']} chunks")
```

## Résultat

Après le scraping, toutes les pages sont indexées dans ChromaDB et le chatbot peut répondre aux questions en utilisant ce contenu.

Vérifiez les statistiques dans la réponse de l'API ou les logs du script.

