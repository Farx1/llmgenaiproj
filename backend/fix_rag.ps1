# Script PowerShell pour réparer la collection ChromaDB corrompue
# Ce script supprime la collection corrompue et la recrée

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Réparation de la collection ChromaDB" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que nous sommes dans le bon répertoire
if (-not (Test-Path "fix_chromadb_collection.py")) {
    Write-Host "❌ Erreur: Ce script doit être exécuté depuis le répertoire backend/" -ForegroundColor Red
    Write-Host "   Répertoire actuel: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

# Activer l'environnement virtuel
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "⚠️  Environnement virtuel non trouvé, continuons quand même..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Exécution du script de réparation Python..." -ForegroundColor Yellow
Write-Host ""

# Exécuter le script Python
python fix_chromadb_collection.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Réparation terminée!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Si la réparation a réussi, vous devrez ré-indexer les documents:" -ForegroundColor Yellow
Write-Host "  python scrape_esilv.py --priority" -ForegroundColor Green
Write-Host ""

