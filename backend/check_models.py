"""Script pour vérifier et télécharger les modèles Mistral depuis Ollama."""
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
import subprocess
from config import settings

def check_ollama_running():
    """Vérifie si Ollama est en cours d'exécution."""
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False

def get_installed_models():
    """Récupère la liste des modèles installés."""
    try:
        response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get("models", []):
                model_name = model.get("name", "")
                # Extraire le nom de base (sans le tag)
                base_name = model_name.split(":")[0] if ":" in model_name else model_name
                if base_name not in models:
                    models.append(base_name)
            return models
        return []
    except Exception as e:
        print(f"Erreur lors de la récupération des modèles: {e}")
        return []

def pull_model(model_name):
    """Télécharge un modèle depuis Ollama."""
    print(f"Téléchargement de {model_name}...")
    try:
        # Utiliser encoding utf-8 pour éviter les erreurs d'encodage
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Remplacer les caractères invalides
            timeout=600  # 10 minutes timeout
        )
        if result.returncode == 0:
            print(f"✓ {model_name} téléchargé avec succès")
            return True
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            # Filtrer les messages d'erreur pour ne garder que les informations importantes
            if "file does not exist" in error_msg.lower():
                print(f"⚠ Modèle {model_name} n'existe pas dans le registre Ollama")
            else:
                print(f"✗ Erreur lors du téléchargement de {model_name}")
                if error_msg:
                    print(f"  Détails: {error_msg[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"✗ Timeout lors du téléchargement de {model_name}")
        return False
    except FileNotFoundError:
        print("✗ Ollama n'est pas installé ou n'est pas dans le PATH")
        return False
    except Exception as e:
        print(f"✗ Erreur: {e}")
        return False

def main():
    """Fonction principale."""
    print("=" * 60)
    print("Vérification des modèles Mistral pour ESILV Smart Assistant")
    print("=" * 60)
    
    # Vérifier si Ollama est en cours d'exécution
    print("\n1. Vérification d'Ollama...")
    if not check_ollama_running():
        print("✗ Ollama n'est pas en cours d'exécution!")
        print("  Veuillez démarrer Ollama avec: ollama serve")
        return 1
    print("✓ Ollama est en cours d'exécution")
    
    # Récupérer les modèles installés
    print("\n2. Récupération des modèles installés...")
    installed_models = get_installed_models()
    print(f"Modèles installés: {', '.join(installed_models) if installed_models else 'Aucun'}")
    
    # Modèles requis depuis la configuration
    required_models = settings.ollama_available_models.copy()
    
    print("\n3. Vérification des modèles requis...")
    missing_models = []
    
    # Vérifier chaque modèle requis
    for model in required_models:
        model_base = model.split(":")[0]  # Enlever le tag si présent
        if model_base not in installed_models:
            missing_models.append(model)
            print(f"  ⚠ {model} manquant")
        else:
            print(f"  ✓ {model_base} trouvé")
    
    # Vérifier si au moins un modèle requis est disponible
    available_required = len(required_models) - len(missing_models)
    
    if missing_models:
        if available_required > 0:
            print(f"\n✓ Au moins un modèle requis est disponible ({available_required}/{len(required_models)})")
            print(f"  Les modèles manquants ne seront pas téléchargés automatiquement.")
            print(f"  Pour télécharger manuellement: ollama pull <nom_modele>")
        else:
            # Aucun modèle requis n'est disponible, on peut proposer de télécharger
            print(f"\n⚠ Aucun modèle requis n'est disponible!")
            print(f"  Téléchargement du premier modèle requis: {required_models[0]}")
            if not pull_model(required_models[0]):
                print(f"  ⚠ Échec du téléchargement de {required_models[0]}")
    else:
        print("\n✓ Tous les modèles requis sont installés")
    
    # Afficher les modèles disponibles
    print("\n5. Modèles disponibles:")
    installed_models = get_installed_models()
    for model in installed_models:
        print(f"  - {model}")
    
    print("\n" + "=" * 60)
    print("Vérification terminée!")
    print("=" * 60)
    
    # Afficher le chemin des modèles si configuré
    ollama_models_path = os.environ.get("OLLAMA_MODELS")
    if ollama_models_path:
        print(f"\nNote: Les modèles sont stockés dans: {ollama_models_path}")
    else:
        print("\nNote: Pour changer l'emplacement des modèles, utilisez:")
        print("  Windows: setx OLLAMA_MODELS E:\\ollama_models")
        print("  Puis redémarrez Ollama")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
