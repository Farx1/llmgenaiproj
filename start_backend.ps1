# Script PowerShell pour demarrer le backend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Demarrage du Backend ESILV Smart Assistant" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Definir OLLAMA_MODELS ABSOLUMENT
# Utiliser E:\ollama_models comme emplacement des modeles (chemin absolu)
$modelsDir = "E:\ollama_models"
$env:OLLAMA_MODELS = $modelsDir
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $modelsDir, "Process")
Write-Host "OLLAMA_MODELS defini: $modelsDir" -ForegroundColor Gray

# Definir le repertoire du projet
$projectRoot = $PSScriptRoot

# Aller dans le repertoire backend (depuis la racine du projet)
$backendDir = Join-Path $projectRoot "backend"
if (-not (Test-Path (Join-Path $backendDir "main.py"))) {
    Write-Host "Erreur: Fichier main.py introuvable dans $backendDir" -ForegroundColor Red
    exit 1
}

Set-Location $backendDir

# Verifier si l'environnement virtuel existe
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activation de l'environnement virtuel..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Aucun environnement virtuel trouve. Utilisation de Python global." -ForegroundColor Yellow
}

# Verifier si Ollama est en cours d'execution
Write-Host "Verification d'Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "OK: Ollama est en cours d'execution" -ForegroundColor Green
} catch {
    Write-Host "ERREUR: Ollama n'est pas en cours d'execution!" -ForegroundColor Red
    Write-Host "  Veuillez demarrer Ollama avec: ollama serve" -ForegroundColor Yellow
    exit 1
}

# Verifier les modeles (verification seulement, pas de telechargement automatique)
Write-Host "Verification des modeles..." -ForegroundColor Yellow
python check_models.py

# Demarrer le serveur
Write-Host ""
Write-Host "Demarrage du serveur FastAPI..." -ForegroundColor Yellow
Write-Host "Le serveur sera accessible sur http://localhost:8000" -ForegroundColor Cyan
Write-Host "Documentation API: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arreter le serveur" -ForegroundColor Yellow
Write-Host ""

python main.py

