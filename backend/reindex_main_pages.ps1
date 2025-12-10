# Script PowerShell pour réindexer les pages principales ESILV
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Réindexation des pages principales ESILV" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que l'environnement virtuel existe
$venvPath = Join-Path $PSScriptRoot "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "❌ Environnement virtuel non trouvé dans $venvPath" -ForegroundColor Red
    Write-Host "   Créez-le d'abord avec: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Activer l'environnement virtuel
Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

# Vérifier que le script existe
$scriptPath = Join-Path $PSScriptRoot "reindex_main_pages.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ Script reindex_main_pages.py non trouvé" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Lancement du script de réindexation..." -ForegroundColor Yellow
Write-Host ""

# Exécuter le script
python $scriptPath

# Vérifier le code de sortie
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Erreur lors de la réindexation (code: $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "✅ Réindexation terminée!" -ForegroundColor Green

