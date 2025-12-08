# ESILV Smart Assistant

An intelligent chatbot for ESILV engineering school with multi-agent coordination, RAG capabilities, and web scraping.

## Features

- **Multi-Agent System**: Orchestration, retrieval, form-filling, and web scraping agents
- **RAG (Retrieval-Augmented Generation)**: Vectorized documentation search using ChromaDB
- **Web Scraping**: Real-time news from ESILV website
- **Model Support**: Ollama (llama3, mistral:7b, mistral) and Google AI Platform (GCP)
- **Next.js Frontend**: Modern chat interface with document upload and admin dashboard

## Project Structure

```
.
├── backend/          # Python FastAPI backend
│   ├── agents/       # Agent implementations
│   ├── rag/          # RAG and vector database
│   ├── api/          # API endpoints
│   └── utils/        # Utility functions
├── frontend/         # Next.js application
│   ├── app/          # App router pages
│   ├── components/   # React components
│   └── lib/          # Client utilities
└── docs/             # Documentation storage
```

## Quick Start

### Lancement en une seule commande (Recommandé)

Le moyen le plus simple de lancer l'application :

```powershell
.\launch.ps1
```

Ce script va automatiquement :
- ✅ Configurer Ollama pour stocker les modèles dans `E:\ollama_models`
- ✅ Vérifier et télécharger les modèles manquants (avec votre confirmation)
- ✅ Installer les dépendances Python et Node.js si nécessaire
- ✅ Créer la configuration (.env) si elle n'existe pas
- ✅ Lancer le backend et le frontend

**Options disponibles :**
```powershell
# Lancer sans vérifier les modèles
.\launch.ps1 -SkipModelCheck

# Lancer avec installation automatique des modèles (sans confirmation)
.\launch.ps1 -AutoInstallModels
```

### Lancement manuel

Si vous préférez lancer manuellement, voir [SETUP.md](SETUP.md) pour les instructions détaillées.

**Important:** Les modèles Ollama sont stockés dans `E:\ollama_models` (chemin absolu, en dehors du projet).

Pour plus d'informations, consultez :
- [LANCEMENT_RAPIDE.md](LANCEMENT_RAPIDE.md) - Guide de lancement rapide
- [SETUP.md](SETUP.md) - Guide d'installation détaillé
- [MODELS.md](MODELS.md) - Documentation des modèles
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture du système

## Usage

Une fois l'application lancée avec `.\launch.ps1` :

1. Ouvrez votre navigateur sur **http://localhost:3000**
2. Sélectionnez un modèle dans le menu déroulant (ministral-3, mistral-large-3:675b-cloud, etc.)
3. Posez vos questions sur ESILV (programmes, admissions, cours, etc.)
4. Téléchargez des documents via le panneau d'upload pour enrichir la base de connaissances
5. Consultez les statistiques et contacts dans le tableau de bord admin à `/admin`

## Documentation

- **[LANCEMENT_RAPIDE.md](LANCEMENT_RAPIDE.md)** - Guide de lancement rapide et dépannage
- **[SETUP.md](SETUP.md)** - Guide d'installation détaillé et configuration manuelle
- **[MODELS.md](MODELS.md)** - Documentation des modèles Ollama supportés
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture du système et des agents

