# Configuration Ollama - ESILV Smart Assistant

> **Note:** Le script `launch.ps1` configure automatiquement Ollama. Cette documentation est utile pour comprendre la configuration ou pour un setup manuel.

## Stockage des modèles dans le projet

Par défaut, Ollama stocke les modèles dans un répertoire système. Ce projet configure Ollama pour stocker les modèles directement dans le répertoire `ollama_models/` du projet.

## Structure

Les modèles Ollama sont stockés dans `E:\ollama_models` (chemin absolu, en dehors du projet).

```
E:\ollama_models/          # Répertoire des modèles Ollama (créé automatiquement)
llmgenaiproj/
├── backend/
├── frontend/
└── ...
```

## Configuration automatique (recommandé)

Utilisez simplement le script de lancement principal :

```powershell
.\launch.ps1
```

Le script configure automatiquement tout ce qui est nécessaire, y compris :
- Création du répertoire `E:\ollama_models/` (si nécessaire)
- Configuration de la variable d'environnement `OLLAMA_MODELS=E:\ollama_models`
- Démarrage d'Ollama si nécessaire
- Téléchargement des modèles manquants (avec confirmation)

## Configuration manuelle

1. **Créer le répertoire des modèles:**
   ```powershell
   New-Item -ItemType Directory -Path "E:\ollama_models"
   ```

2. **Définir la variable d'environnement:**
   ```powershell
   $env:OLLAMA_MODELS = "E:\ollama_models"
   ```

3. **Démarrer Ollama:**
   ```powershell
   ollama serve
   ```

4. **Télécharger les modèles:**
   ```powershell
   ollama pull ministral-3
   ollama pull mistral-large-3:675b-cloud
   ollama pull mistral
   ollama pull llama3
   ollama pull mistral:7b
   ```

## Configuration permanente (optionnel)

Pour définir `OLLAMA_MODELS` de manière permanente sur Windows:

1. Ouvrez les **Variables d'environnement système**
2. Ajoutez une nouvelle variable utilisateur:
   - **Nom:** `OLLAMA_MODELS`
   - **Valeur:** `E:\ollama_models`

3. Redémarrez votre terminal et Ollama

## Vérification

Vérifiez que les modèles sont bien dans le répertoire:

```powershell
# Lister les modèles
ollama list

# Vérifier l'emplacement
Get-ChildItem -Path "E:\ollama_models" -Recurse | Select-Object FullName
```

## Modèles supportés

- `ministral-3` (recommandé par défaut)
- `mistral-large-3:675b-cloud`
- `mistral`
- `llama3`
- `mistral:7b`

## Dépannage

### Les modèles ne sont pas dans le répertoire

1. Vérifiez que `OLLAMA_MODELS` est défini:
   ```powershell
   echo $env:OLLAMA_MODELS
   ```
   Devrait afficher: `E:\ollama_models`

2. Assurez-vous qu'Ollama a été redémarré après avoir défini la variable

3. Vérifiez que le répertoire existe:
   ```powershell
   Test-Path "E:\ollama_models"
   ```

### Ollama ne trouve pas les modèles

Si Ollama ne trouve pas les modèles après avoir changé le répertoire:

1. Arrêtez Ollama (Ctrl+C)
2. Redéfinissez `OLLAMA_MODELS`
3. Redémarrez Ollama
4. Les modèles devraient être détectés automatiquement

## Notes

- Le répertoire `ollama_models` peut être volumineux (plusieurs Go par modèle)
- Assurez-vous d'avoir suffisamment d'espace disque
- Les modèles sont partagés entre toutes les instances d'Ollama qui utilisent le même répertoire

