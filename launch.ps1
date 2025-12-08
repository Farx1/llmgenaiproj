# Script principal pour lancer l'application ESILV Smart Assistant
# Ce script configure tout et lance l'application en une seule commande

param(
    [switch]$SkipModelCheck = $false,
    [switch]$AutoInstallModels = $false
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ESILV Smart Assistant - Lancement" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Definir le repertoire du projet
$projectRoot = $PSScriptRoot
# Utiliser E:\ollama_models comme emplacement des modeles (chemin absolu)
$modelsDir = "E:\ollama_models"

# ============================================
# ETAPE 1: Configuration d'Ollama
# ============================================
Write-Host "[1/6] Configuration d'Ollama..." -ForegroundColor Yellow

# Creer le repertoire des modeles
if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
    Write-Host "  OK Repertoire cree: $modelsDir" -ForegroundColor Green
} else {
    Write-Host "  OK Repertoire existe: $modelsDir" -ForegroundColor Green
}

# Definir OLLAMA_MODELS ABSOLUMENT (pour cette session et les processus enfants)
$env:OLLAMA_MODELS = $modelsDir
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $modelsDir, "Process")
Write-Host "  OK OLLAMA_MODELS defini: $modelsDir" -ForegroundColor Green
Write-Host "  IMPORTANT: Les modeles seront telecharges dans: $modelsDir" -ForegroundColor Cyan

# Verifier si Ollama est en cours d'execution
Write-Host "  Verification d'Ollama..." -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  OK Ollama est en cours d'execution" -ForegroundColor Green
    $ollamaRunning = $true
} catch {
    Write-Host "  Attention Ollama n'est pas en cours d'execution" -ForegroundColor Yellow
    Write-Host "  Demarrage d'Ollama avec OLLAMA_MODELS=$modelsDir..." -ForegroundColor Gray
    
    # Demarrer Ollama en arriere-plan avec OLLAMA_MODELS defini
    try {
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = "ollama"
        $processInfo.Arguments = "serve"
        $processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
        $processInfo.UseShellExecute = $false
        $processInfo.EnvironmentVariables["OLLAMA_MODELS"] = $modelsDir
        $process = [System.Diagnostics.Process]::Start($processInfo)
        Start-Sleep -Seconds 5
        Write-Host "  OK Ollama demarre avec OLLAMA_MODELS=$modelsDir" -ForegroundColor Green
    } catch {
        Write-Host "  Attention Impossible de demarrer Ollama automatiquement" -ForegroundColor Yellow
        Write-Host "  Veuillez demarrer Ollama manuellement avec:" -ForegroundColor Yellow
        Write-Host "    `$env:OLLAMA_MODELS = '$modelsDir'" -ForegroundColor White
        Write-Host "    ollama serve" -ForegroundColor White
    }
    
    # Verifier a nouveau
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
        Write-Host "  OK Ollama demarre avec succes" -ForegroundColor Green
        $ollamaRunning = $true
    } catch {
        Write-Host "  Erreur Impossible de demarrer Ollama automatiquement" -ForegroundColor Red
        Write-Host "  Veuillez demarrer Ollama manuellement: ollama serve" -ForegroundColor Yellow
        Write-Host "  Assurez-vous que OLLAMA_MODELS=$modelsDir est defini" -ForegroundColor Yellow
        $ollamaRunning = $false
    }
}

# ============================================
# ETAPE 2: Verification des modeles
# ============================================
Write-Host ""
Write-Host "[2/6] Verification des modeles..." -ForegroundColor Yellow

$requiredModels = @("ministral-3", "mistral-large-3:675b-cloud", "mistral", "mistral:7b", "llama3")
$installedModels = @()

# Verifier si le dossier ollama_models contient des fichiers
$modelsDirEmpty = $true
if (Test-Path $modelsDir) {
    $filesInDir = Get-ChildItem -Path $modelsDir -Recurse -File -ErrorAction SilentlyContinue
    if ($filesInDir.Count -gt 0) {
        $modelsDirEmpty = $false
        Write-Host "  OK Dossier ollama_models contient des fichiers ($($filesInDir.Count) fichiers)" -ForegroundColor Green
    } else {
        Write-Host "  Attention Dossier ollama_models est vide" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Attention Dossier ollama_models n'existe pas" -ForegroundColor Yellow
}

if ($ollamaRunning) {
    try {
        $modelsResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
        $installedModels = $modelsResponse.models | ForEach-Object { $_.name }
        Write-Host "  OK Modeles installes dans Ollama: $($installedModels -join ', ')" -ForegroundColor Green
    } catch {
        Write-Host "  Attention Impossible de recuperer la liste des modeles" -ForegroundColor Yellow
    }
}

# Verifier les modeles (en tenant compte des variantes comme :latest, :7b, etc.)
$missingModels = @()
foreach ($requiredModel in $requiredModels) {
    $found = $false
    foreach ($installedModel in $installedModels) {
        # Verifier si le modele correspond (avec ou sans tag)
        $modelPrefix = "${requiredModel}:"
        if ($installedModel -eq $requiredModel -or $installedModel.StartsWith($modelPrefix)) {
            $found = $true
            break
        }
    }
    if (-not $found) {
        $missingModels += $requiredModel
    }
}

# Si le dossier est vide, proposer de telecharger les modeles requis
if ($modelsDirEmpty) {
    Write-Host "  Le dossier ollama_models est vide" -ForegroundColor Yellow
    $missingModels = $requiredModels
} elseif ($missingModels.Count -gt 0) {
    Write-Host "  Attention Modeles manquants: $($missingModels -join ', ')" -ForegroundColor Yellow
}

if ($missingModels.Count -gt 0) {
    $modelsToDownload = @()
    
    if ($AutoInstallModels) {
        # Mode automatique: telecharger tous les modeles manquants
        $modelsToDownload = $missingModels
        Write-Host "  Mode automatique: telechargement de tous les modeles manquants" -ForegroundColor Cyan
    } elseif (-not $SkipModelCheck) {
        # Mode interactif: permettre de choisir les modeles
        Write-Host ""
        Write-Host "  Modeles disponibles a telecharger:" -ForegroundColor Cyan
        for ($i = 0; $i -lt $missingModels.Count; $i++) {
            Write-Host "    [$($i + 1)] $($missingModels[$i])" -ForegroundColor White
        }
        Write-Host "    [A] Tous les modeles" -ForegroundColor White
        Write-Host "    [N] Aucun" -ForegroundColor White
        Write-Host ""
        $response = Read-Host "  Selectionnez les modeles a telecharger (ex: 1,2,3 ou A pour tous, N pour aucun)"
        
        if ($response -eq "A" -or $response -eq "a") {
            $modelsToDownload = $missingModels
        } elseif ($response -eq "N" -or $response -eq "n") {
            $modelsToDownload = @()
        } else {
            # Parser la reponse (ex: "1,2,3" ou "1 2 3")
            $selections = $response -split '[,\s]+' | ForEach-Object { $_.Trim() }
            foreach ($sel in $selections) {
                $index = [int]$sel - 1
                if ($index -ge 0 -and $index -lt $missingModels.Count) {
                    $modelsToDownload += $missingModels[$index]
                }
            }
            # Supprimer les doublons
            $modelsToDownload = $modelsToDownload | Select-Object -Unique
        }
    } else {
        $modelsToDownload = @()
    }
    
    if ($modelsToDownload.Count -gt 0) {
        Write-Host ""
        Write-Host "  Telechargement des modeles selectionnes: $($modelsToDownload -join ', ')" -ForegroundColor Gray
        Write-Host "  Destination ABSOLUE: $modelsDir" -ForegroundColor Cyan
        foreach ($model in $modelsToDownload) {
            Write-Host "    Telechargement de $model..." -ForegroundColor Cyan
            # S'assurer que OLLAMA_MODELS est defini ABSOLUMENT dans le processus
            $env:OLLAMA_MODELS = $modelsDir
            # Utiliser ProcessStartInfo pour definir explicitement OLLAMA_MODELS
            $processInfo = New-Object System.Diagnostics.ProcessStartInfo
            $processInfo.FileName = "ollama"
            $processInfo.Arguments = "pull $model"
            $processInfo.UseShellExecute = $false
            $processInfo.CreateNoWindow = $true
            $processInfo.EnvironmentVariables["OLLAMA_MODELS"] = $modelsDir
            $process = [System.Diagnostics.Process]::Start($processInfo)
            $process.WaitForExit()
            if ($process.ExitCode -eq 0) {
                Write-Host "    OK $model telecharge dans $modelsDir" -ForegroundColor Green
            } else {
                Write-Host "    Erreur lors du telechargement de $model (code: $($process.ExitCode))" -ForegroundColor Red
            }
        }
        
        # Verifier apres telechargement que les fichiers sont bien dans le dossier
        Start-Sleep -Seconds 2
        $filesAfter = Get-ChildItem -Path $modelsDir -Recurse -File -ErrorAction SilentlyContinue
        if ($filesAfter.Count -gt 0) {
            Write-Host "  OK Verification: $($filesAfter.Count) fichiers dans $modelsDir" -ForegroundColor Green
        } else {
            Write-Host "  Attention: Le dossier semble toujours vide apres telechargement" -ForegroundColor Yellow
            Write-Host "  Verifiez que OLLAMA_MODELS=$modelsDir est bien defini pour Ollama" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Aucun modele selectionne pour telechargement" -ForegroundColor Gray
        Write-Host "  Vous pouvez les telecharger plus tard avec: ollama pull <nom_modele>" -ForegroundColor Gray
    }
} else {
    Write-Host "  OK Tous les modeles requis sont installes" -ForegroundColor Green
}

# ============================================
# ETAPE 3: Verification des dependances backend
# ============================================
Write-Host ""
Write-Host "[3/6] Verification du backend..." -ForegroundColor Yellow

$backendDir = Join-Path $projectRoot "backend"

if (-not (Test-Path (Join-Path $backendDir "requirements.txt"))) {
    Write-Host "  Erreur Fichier requirements.txt introuvable" -ForegroundColor Red
    exit 1
}

# Verifier si Python est installe
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  OK Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  Erreur Python n'est pas installe ou pas dans le PATH" -ForegroundColor Red
    exit 1
}

# Verifier si les dependances sont installees
$venvPath = Join-Path $backendDir "venv"
if (Test-Path $venvPath) {
    Write-Host "  OK Environnement virtuel trouve" -ForegroundColor Green
} else {
    Write-Host "  Attention Environnement virtuel non trouve" -ForegroundColor Yellow
    Write-Host "  Creation de l'environnement virtuel..." -ForegroundColor Gray
    Set-Location $backendDir
    python -m venv venv
    Write-Host "  OK Environnement virtuel cree" -ForegroundColor Green
}

# Activer l'environnement virtuel et installer les dependances
Set-Location $backendDir
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    Write-Host "  OK Environnement virtuel active" -ForegroundColor Green
    
    # Verifier si les dependances sont installees (verification plus robuste)
    $pythonExe = Join-Path $backendDir "venv\Scripts\python.exe"
    if (Test-Path $pythonExe) {
        $checkResult = & $pythonExe -c "import fastapi; import langchain" 2>&1
        if ($LASTEXITCODE -ne 0 -or $checkResult) {
            Write-Host "  Installation des dependances Python..." -ForegroundColor Gray
            Write-Host "  (Cela peut prendre plusieurs minutes...)" -ForegroundColor Yellow
            & $pythonExe -m pip install --quiet --upgrade pip
            & $pythonExe -m pip install --quiet -r requirements.txt
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  OK Dependances installees" -ForegroundColor Green
            } else {
                Write-Host "  Attention Erreur lors de l'installation (code: $LASTEXITCODE)" -ForegroundColor Yellow
                Write-Host "  Vous pouvez installer manuellement avec: pip install -r requirements.txt" -ForegroundColor Gray
            }
        } else {
            Write-Host "  OK Dependances deja installees" -ForegroundColor Green
        }
    } else {
        Write-Host "  Attention Python de l'environnement virtuel introuvable" -ForegroundColor Yellow
    }
}

# ============================================
# ETAPE 4: Verification des dependances frontend
# ============================================
Write-Host ""
Write-Host "[4/6] Verification du frontend..." -ForegroundColor Yellow

$frontendDir = Join-Path $projectRoot "frontend"

if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Host "  Erreur Fichier package.json introuvable" -ForegroundColor Red
    exit 1
}

# Verifier si Node.js est installe
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  OK Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  Erreur Node.js n'est pas installe ou pas dans le PATH" -ForegroundColor Red
    exit 1
}

# Verifier si node_modules existe
Set-Location $frontendDir
if (Test-Path "node_modules") {
    Write-Host "  OK Dependances Node.js installees" -ForegroundColor Green
} else {
    Write-Host "  Installation des dependances Node.js..." -ForegroundColor Gray
    npm install
    Write-Host "  OK Dependances installees" -ForegroundColor Green
}

# ============================================
# ETAPE 5: Creation du fichier .env si necessaire
# ============================================
Write-Host ""
Write-Host "[5/6] Configuration..." -ForegroundColor Yellow

Set-Location $backendDir
if (-not (Test-Path ".env")) {
    Write-Host "  Creation du fichier .env..." -ForegroundColor Gray
    $envContent = @"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_DEFAULT_MODEL=ministral-3
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=esilv_docs
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000"]
ESILV_BASE_URL=https://www.esilv.fr
"@
    # Ecrire sans BOM UTF-8
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText((Join-Path $backendDir ".env"), $envContent, $utf8NoBom)
    Write-Host "  OK Fichier .env cree" -ForegroundColor Green
} else {
    Write-Host "  OK Fichier .env existe deja" -ForegroundColor Green
}

# ============================================
# ETAPE 6: Lancement de l'application
# ============================================
Write-Host ""
Write-Host "[6/6] Lancement de l'application..." -ForegroundColor Yellow
Write-Host ""

# Demarrer le backend dans une nouvelle fenetre
Write-Host "  Demarrage du backend..." -ForegroundColor Gray
$backendScript = Join-Path $projectRoot "start_backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$backendScript`"" -WindowStyle Normal

# Attendre que le backend demarre
Start-Sleep -Seconds 5

# Demarrer le frontend dans une nouvelle fenetre
Write-Host "  Demarrage du frontend..." -ForegroundColor Gray
$frontendScript = Join-Path $projectRoot "start_frontend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", "`"$frontendScript`"" -WindowStyle Normal

# ============================================
# RESUME
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  OK Application lancee avec succes!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Les serveurs s'executent dans des fenetres separees." -ForegroundColor Yellow
Write-Host "  Fermez les fenetres pour arreter les serveurs." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Modeles Ollama stockes dans: $modelsDir" -ForegroundColor Gray
Write-Host ""
