# 🚀 Lancement Rapide - ESILV Smart Assistant

## Lancement en une seule commande

```powershell
.\launch.ps1
```

C'est tout ! Le script `launch.ps1` va automatiquement :

1. ✅ Configurer Ollama pour stocker les modèles dans `E:\ollama_models`
2. ✅ Démarrer Ollama s'il n'est pas déjà en cours d'exécution
3. ✅ Vérifier les modèles installés
4. ✅ Vous proposer de télécharger les modèles manquants
5. ✅ Installer les dépendances Python et Node.js si nécessaire
6. ✅ Créer la configuration (.env) si elle n'existe pas
7. ✅ Lancer le backend et le frontend dans des fenêtres séparées

## Options disponibles

```powershell
# Lancer sans vérifier les modèles
.\launch.ps1 -SkipModelCheck

# Lancer avec installation automatique des modèles (sans confirmation)
.\launch.ps1 -AutoInstallModels
```

## Après le lancement

Une fois le script terminé, vous verrez :

```
✓ Application lancée avec succès!

  Backend:  http://localhost:8000
  Frontend: http://localhost:3000
  API Docs: http://localhost:8000/docs
```

Ouvrez votre navigateur sur **http://localhost:3000** pour commencer à utiliser l'application.

## Arrêter l'application

Fermez simplement les fenêtres PowerShell où tournent le backend et le frontend.

## Dépannage

### Ollama ne démarre pas automatiquement

Si Ollama ne démarre pas automatiquement, démarrez-le manuellement :

```powershell
$env:OLLAMA_MODELS = "E:\ollama_models"
ollama serve
```

Puis relancez `.\launch.ps1`

### Les modèles ne se téléchargent pas

Assurez-vous qu'Ollama est en cours d'exécution et que vous avez une connexion Internet. Vous pouvez aussi télécharger les modèles manuellement :

```powershell
ollama pull ministral-3
ollama pull mistral-large-3:675b-cloud
```

### Erreurs de dépendances

Si vous rencontrez des erreurs lors de l'installation des dépendances :

**Backend :**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Frontend :**
```powershell
cd frontend
npm install
```

## Modèles supportés

- `ministral-3` (modèle par défaut)
- `mistral-large-3:675b-cloud`
- `mistral`
- `llama3`
- `mistral:7b`

Les modèles sont stockés dans `E:\ollama_models` (chemin absolu).

