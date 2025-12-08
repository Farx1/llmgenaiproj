# Script PowerShell pour demarrer le frontend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Demarrage du Frontend ESILV Smart Assistant" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Aller dans le repertoire frontend (depuis la racine du projet)
# $PSScriptRoot est deja la racine du projet (ou le script est a la racine)
$projectRoot = $PSScriptRoot
$frontendDir = Join-Path $projectRoot "frontend"
if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Host "Erreur: Fichier package.json introuvable dans $frontendDir" -ForegroundColor Red
    exit 1
}

Set-Location $frontendDir

# Verifier si node_modules existe
if (-not (Test-Path "node_modules")) {
    Write-Host "Installation des dependances npm..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erreur lors de l'installation des dependances" -ForegroundColor Red
        exit 1
    }
}

# Demarrer le serveur de developpement
Write-Host ""
Write-Host "Demarrage du serveur Next.js..." -ForegroundColor Yellow
Write-Host "Le frontend sera accessible sur http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arreter le serveur" -ForegroundColor Yellow
Write-Host ""

npm run dev

