# Script principal pour lancer l'application ESILV Smart Assistant
# Ce script configure tout et lance l'application en une seule commande
#

param(
    [switch]$SkipModelCheck = $false,
    [switch]$AutoInstallModels = $false
)

# Configuration de l'encodage UTF-8
try {
    # Configurer les encodages AVANT toute sortie
    $OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    
    # Essayer de changer la page de code système à UTF-8 (65001)
    try {
        $null = chcp 65001 2>$null
    } catch {
        # Ignorer si chcp echoue (peut ne pas etre disponible dans certains contextes)
    }
    
    # Configurer les paramètres par défaut pour les cmdlets
    $PSDefaultParameterValues['*:Encoding'] = 'utf8'
    if ($PSVersionTable.PSVersion.Major -ge 6) {
        $PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
    }
} catch {
    # Si la configuration echoue, continuer quand meme
}

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ESILV Smart Assistant - Lancement" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Définir le répertoire du projet
$projectRoot = $PSScriptRoot
# Utiliser E:\ollama_models comme emplacement des modèles (chemin absolu)
$modelsDir = "E:\ollama_models"

# ============================================
# ETAPE 1: Configuration d'Ollama
# ============================================
Write-Host "[1/6] Configuration d'Ollama..." -ForegroundColor Yellow

# Créer le répertoire des modèles
if (-not (Test-Path $modelsDir)) {
    New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
    Write-Host "  OK Repertoire cree: $modelsDir" -ForegroundColor Green
} else {
    Write-Host "  OK Repertoire existe: $modelsDir" -ForegroundColor Green
}

# Definir OLLAMA_MODELS pour cette session
$env:OLLAMA_MODELS = $modelsDir
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $modelsDir, "Process")
Write-Host "  OK OLLAMA_MODELS defini: $modelsDir" -ForegroundColor Green
Write-Host "  IMPORTANT: Les modeles seront telecharges dans: $modelsDir" -ForegroundColor Cyan

# Verifier si Ollama est en cours d'execution
Write-Host "  Verification d'Ollama..." -ForegroundColor Gray
$ollamaRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  OK Ollama est en cours d'execution" -ForegroundColor Green
    $ollamaRunning = $true
} catch {
    Write-Host "  Attention: Ollama n'est pas en cours d'execution" -ForegroundColor Yellow
    Write-Host "  Demarrage d'Ollama avec OLLAMA_MODELS=$modelsDir..." -ForegroundColor Gray

    # Demarrer Ollama en arriere-plan avec OLLAMA_MODELS defini
    try {
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = "ollama"
        $processInfo.Arguments = "serve"
        $processInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Minimized
        $processInfo.UseShellExecute = $false
        $processInfo.EnvironmentVariables["OLLAMA_MODELS"] = $modelsDir
        [System.Diagnostics.Process]::Start($processInfo) | Out-Null
        Start-Sleep -Seconds 5
    } catch {
        Write-Host "  Attention: Impossible de demarrer Ollama automatiquement" -ForegroundColor Yellow
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
        Write-Host "  Erreur: Impossible de verifier Ollama apres demarrage" -ForegroundColor Red
        Write-Host "  Vous pourrez quand meme continuer, mais la verification des modeles sera limitee." -ForegroundColor Yellow
        $ollamaRunning = $false
    }
}

# ============================================
# ETAPE 2: Verification des modeles Ollama
# ============================================
Write-Host ""
Write-Host "[2/6] Verification des modeles..." -ForegroundColor Yellow

# Modeles minimum requis (pour compatibilite)
$requiredModels = @("llama3", "mistral", "qwen2.5")

# Modeles recommandes avec leurs context windows
$recommendedModels = @(
    @{Name="qwen2.5"; Context="1M+ (up to 2M fine-tuned)"; Size="72B"; Description="Top for ultra-long RAG; handles full books reliably"},
    @{Name="qwen2.5:7b"; Context="1M+"; Size="7B"; Description="Qwen2.5 7B"},
    @{Name="qwen2.5:14b"; Context="1M+"; Size="14B"; Description="Qwen2.5 14B"},
    @{Name="qwen2.5:32b"; Context="1M+"; Size="32B"; Description="Qwen2.5 32B"},
    @{Name="qwen2.5:72b"; Context="1M+"; Size="72B"; Description="Qwen2.5 72B"},
    @{Name="llama3.1"; Context="128K"; Size="8B-405B"; Description="Balanced for docs; strong reasoning in RAG workflows"},
    @{Name="llama3.1:8b"; Context="128K"; Size="8B"; Description="Llama 3.1 8B"},
    @{Name="llama3.1:70b"; Context="128K"; Size="70B"; Description="Llama 3.1 70B"},
    @{Name="deepseek-r1"; Context="164K-262K"; Size="16B-236B"; Description="Efficient long-context retrieval; coding/RAG optimized"},
    @{Name="deepseek-r1:7b"; Context="164K-262K"; Size="7B"; Description="DeepSeek-R1 7B"},
    @{Name="deepseek-r1:14b"; Context="164K-262K"; Size="14B"; Description="DeepSeek-R1 14B"},
    @{Name="mistral"; Context="128K"; Size="7B-12B"; Description="Good for medium-large docs; Ollama-friendly"},
    @{Name="mistral:7b"; Context="128K"; Size="7B"; Description="Mistral 7B"},
    @{Name="mixtral"; Context="128K"; Size="8x7B"; Description="Mistral Mixtral"},
    @{Name="mixtral:8x7b"; Context="128K"; Size="8x7B"; Description="Mixtral 8x7B"},
    @{Name="gemma2"; Context="128K"; Size="12B-27B"; Description="Solid RAG up to 90K; quality holds well"},
    @{Name="gemma2:9b"; Context="128K"; Size="9B"; Description="Gemma 2 9B"},
    @{Name="gemma2:27b"; Context="128K"; Size="27B"; Description="Gemma 2 27B"},
    @{Name="phi3"; Context="128K"; Size="12B-27B"; Description="Solid RAG up to 90K; quality holds well"},
    @{Name="phi3:mini"; Context="128K"; Size="Mini"; Description="Phi-3 Mini"},
    @{Name="phi3:medium"; Context="128K"; Size="Medium"; Description="Phi-3 Medium"},
    @{Name="command-r+"; Context="128K-1M"; Size="35B-104B"; Description="Retrieval-focused; coherent over long inputs"},
    @{Name="internlm2.5"; Context="128K-1M"; Size="35B-104B"; Description="Retrieval-focused; coherent over long inputs"}
)

$installedModels = @()

# Verifier si le dossier de modeles contient des fichiers
$modelsDirEmpty = $true
if (Test-Path $modelsDir) {
    $filesInDir = Get-ChildItem -Path $modelsDir -Recurse -File -ErrorAction SilentlyContinue
    if ($filesInDir.Count -gt 0) {
        $modelsDirEmpty = $false
        Write-Host "  OK Dossier ollama_models contient des fichiers ($($filesInDir.Count) fichiers)" -ForegroundColor Green
    } else {
        Write-Host "  Attention: Dossier ollama_models est vide" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Attention: Dossier ollama_models n'existe pas (devrait avoir ete cree plus haut)" -ForegroundColor Yellow
}

if ($ollamaRunning) {
    try {
        $modelsResponse = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
        $installedModels = $modelsResponse.models | ForEach-Object { $_.name }
        if ($installedModels.Count -gt 0) {
            Write-Host "  Modeles installes: $($installedModels -join ', ')" -ForegroundColor Green
        } else {
            Write-Host "  Aucun modele n'est encore installe dans Ollama." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  Attention: Impossible de recuperer la liste des modeles via l'API Ollama." -ForegroundColor Yellow
    }
} else {
    Write-Host "  Ollama n'est pas disponible, verification des modeles limitee." -ForegroundColor Yellow
}

# Determiner les modeles requis manquants
$missingRequiredModels = @()
foreach ($requiredModel in $requiredModels) {
    $found = $false
    foreach ($installedModel in $installedModels) {
        $modelPrefix = "${requiredModel}:"
        if ($installedModel -eq $requiredModel -or $installedModel.StartsWith($modelPrefix)) {
            $found = $true
            break
        }
    }
    if (-not $found) {
        $missingRequiredModels += $requiredModel
    }
}

# Determiner les modeles recommandes disponibles (non installes)
$availableRecommendedModels = @()
foreach ($recommendedModel in $recommendedModels) {
    $modelName = $recommendedModel.Name
    $found = $false
    foreach ($installedModel in $installedModels) {
        $modelPrefix = "${modelName}:"
        if ($installedModel -eq $modelName -or $installedModel.StartsWith($modelPrefix)) {
            $found = $true
            break
        }
    }
    if (-not $found) {
        $availableRecommendedModels += $recommendedModel
    }
}

if ($modelsDirEmpty -and $missingRequiredModels.Count -eq 0) {
    # Dossier vide mais API n'a rien remonte, on force les requis comme manquants
    $missingRequiredModels = $requiredModels
}

# Determiner si on doit proposer le telechargement
$shouldOfferDownload = $false
if (-not $SkipModelCheck -and $ollamaRunning) {
    if ($missingRequiredModels.Count -gt 0 -or $availableRecommendedModels.Count -gt 0) {
        $shouldOfferDownload = $true
    }
}

if ($shouldOfferDownload) {
    $modelsToDownload = @()
    
    # Preparer la liste des modeles a proposer
    $modelsToOffer = @()
    if ($missingRequiredModels.Count -gt 0) {
        Write-Host ""
        Write-Host "  Modeles minimum requis manquants:" -ForegroundColor Yellow
        foreach ($model in $missingRequiredModels) {
            $modelsToOffer += $model
            Write-Host "    - $model (requis)" -ForegroundColor Red
        }
    }
    
    if ($availableRecommendedModels.Count -gt 0) {
        Write-Host ""
        Write-Host "  Modeles recommandes disponibles (avec grands context windows pour RAG):" -ForegroundColor Cyan
        $recommendedCount = 0
        foreach ($model in $availableRecommendedModels) {
            if ($recommendedCount -lt 10) {  # Limiter l'affichage a 10 modeles
                $modelsToOffer += $model.Name
                Write-Host "    - $($model.Name) (Context: $($model.Context), Size: $($model.Size))" -ForegroundColor White
                $recommendedCount++
            }
        }
        if ($availableRecommendedModels.Count -gt 10) {
            Write-Host "    ... et $($availableRecommendedModels.Count - 10) autres modeles recommandes" -ForegroundColor Gray
        }
    }
    
    if ($modelsToOffer.Count -gt 0) {
        if ($AutoInstallModels) {
            # Mode automatique: telecharger tous les modeles manquants requis
            $modelsToDownload = $missingRequiredModels
            Write-Host ""
            Write-Host "  Mode automatique: telechargement des modeles requis uniquement" -ForegroundColor Cyan
        } else {
            # Mode interactif: permettre de choisir les modeles
            Write-Host ""
            Write-Host "  Options de telechargement:" -ForegroundColor Cyan
            Write-Host "    [1] Telecharger les modeles requis uniquement ($($missingRequiredModels.Count) modeles)" -ForegroundColor White
            Write-Host "    [2] Choisir parmi les modeles recommandes" -ForegroundColor White
            Write-Host "    [N] Aucun (continuer sans telecharger)" -ForegroundColor White
            Write-Host ""
            $choice = Read-Host "  Votre choix (1, 2, ou N)"
            
            if ($choice -eq "1") {
                $modelsToDownload = $missingRequiredModels
            } elseif ($choice -eq "2") {
                Write-Host ""
                Write-Host "  Selectionnez les modeles a telecharger:" -ForegroundColor Cyan
                for ($i = 0; $i -lt [Math]::Min($modelsToOffer.Count, 20); $i++) {
                    $modelName = $modelsToOffer[$i]
                    $isRequired = $missingRequiredModels -contains $modelName
                    $marker = if ($isRequired) { " [REQUIS]" } else { "" }
                    Write-Host "    [$($i + 1)] $modelName$marker" -ForegroundColor $(if ($isRequired) { "Yellow" } else { "White" })
                }
                Write-Host "    [A] Tous les modeles affiches" -ForegroundColor White
                Write-Host "    [N] Aucun" -ForegroundColor White
                Write-Host ""
                $response = Read-Host "  Selection (ex: 1,2,3 ou A pour tous, N pour aucun)"
                
                if ($response -eq "A" -or $response -eq "a") {
                    $modelsToDownload = $modelsToOffer
                } elseif ($response -eq "N" -or $response -eq "n") {
                    $modelsToDownload = @()
                } else {
                    # Parser la reponse (ex: "1,2,3" ou "1 2 3")
                    $selections = $response -split '[,\s]+' | ForEach-Object { $_.Trim() }
                    foreach ($sel in $selections) {
                        $index = [int]$sel - 1
                        if ($index -ge 0 -and $index -lt $modelsToOffer.Count) {
                            $modelsToDownload += $modelsToOffer[$index]
                        }
                    }
                    # Supprimer les doublons
                    $modelsToDownload = $modelsToDownload | Select-Object -Unique
                }
            } else {
                $modelsToDownload = @()
            }
        }
    } else {
        # Aucun modele a proposer
        $modelsToDownload = @()
    }
    
    if ($modelsToDownload.Count -gt 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  Telechargement des modeles" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Modeles a telecharger: $($modelsToDownload.Count)" -ForegroundColor Yellow
        Write-Host "  Liste: $($modelsToDownload -join ', ')" -ForegroundColor White
        Write-Host "  Destination: $modelsDir" -ForegroundColor Cyan
        Write-Host ""
        
        $successCount = 0
        $failCount = 0
        $startTime = Get-Date
        
        foreach ($model in $modelsToDownload) {
            Write-Host "  Telechargement de '$model'..." -ForegroundColor Cyan
            $modelStartTime = Get-Date
            try {
                $env:OLLAMA_MODELS = $modelsDir
                & ollama pull $model
                if ($LASTEXITCODE -eq 0) {
                    $successCount++
                    $modelEndTime = Get-Date
                    $modelDuration = ($modelEndTime - $modelStartTime).TotalSeconds
                    Write-Host "  OK SUCCES: $model telecharge (Duree: $([Math]::Round($modelDuration, 1)) secondes)" -ForegroundColor Green
                } else {
                    $failCount++
                    Write-Host "  ERREUR: Echec du telechargement de $model (code: $LASTEXITCODE)" -ForegroundColor Red
                }
            }
            catch {
                $failCount++
                Write-Host "  EXCEPTION: Erreur lors du telechargement de $model" -ForegroundColor Red
                Write-Host "    Message: $($_.Exception.Message)" -ForegroundColor Red
            }
            Write-Host ""
        }
        
        # Resume final
        $endTime = Get-Date
        $totalDuration = ($endTime - $startTime).TotalSeconds
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  Resume du telechargement" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  Total: $($modelsToDownload.Count) modeles" -ForegroundColor White
        Write-Host "  Reussis: $successCount" -ForegroundColor Green
        Write-Host "  Echoues: $failCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Gray" })
        Write-Host "  Duree totale: $([Math]::Round($totalDuration / 60, 1)) minutes" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host "  Aucun modele selectionne pour telechargement" -ForegroundColor Gray
        Write-Host "  Vous pouvez les telecharger plus tard avec: ollama pull nom_modele" -ForegroundColor Gray
    }
} else {
    if (-not $SkipModelCheck) {
        Write-Host "  OK Tous les modeles requis sont deja installes." -ForegroundColor Green
    } else {
        Write-Host "  Verification des modeles ignoree (SkipModelCheck)." -ForegroundColor Gray
    }
}

# ============================================
# ETAPE 3: Verification des dependances backend
# ============================================
Write-Host ""
Write-Host "[3/6] Verification du backend..." -ForegroundColor Yellow

$backendDir = Join-Path $projectRoot "backend"

if (-not (Test-Path (Join-Path $backendDir "requirements.txt"))) {
    Write-Host "  Erreur: Fichier requirements.txt introuvable dans '$backendDir'" -ForegroundColor Red
    exit 1
}

# Verifier si Python est installe
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  OK Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  Erreur: Python n'est pas installe ou pas dans le PATH." -ForegroundColor Red
    exit 1
}

# Verifier si l'environnement virtuel existe
$venvPath = Join-Path $backendDir "venv"
if (Test-Path $venvPath) {
    Write-Host "  OK Environnement virtuel trouve." -ForegroundColor Green
} else {
    Write-Host "  Environnement virtuel non trouve, creation..." -ForegroundColor Yellow
    Set-Location $backendDir
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK Environnement virtuel cree." -ForegroundColor Green
    } else {
        Write-Host "  Erreur: impossible de creer l'environnement virtuel (code: $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
}

# Activer l'environnement virtuel et installer les dependances
Set-Location $backendDir
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    Write-Host "  OK Environnement virtuel active." -ForegroundColor Green

    $pythonExe = Join-Path $backendDir "venv\Scripts\python.exe"
    if (Test-Path $pythonExe) {
        Write-Host "  Installation / mise a jour des dependances Python..." -ForegroundColor Gray
        & $pythonExe -m pip install --upgrade pip
        & $pythonExe -m pip install -r requirements.txt
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  OK Dependances Python installees." -ForegroundColor Green
        } else {
            Write-Host "  Attention: erreur lors de l'installation des dependances (code: $LASTEXITCODE)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Erreur: Python dans le venv introuvable." -ForegroundColor Red
    }
} else {
    Write-Host "  Erreur: script d'activation du venv introuvable." -ForegroundColor Red
}

# ============================================
# ETAPE 4: Verification des dependances frontend
# ============================================
Write-Host ""
Write-Host "[4/6] Verification du frontend..." -ForegroundColor Yellow

$frontendDir = Join-Path $projectRoot "frontend"

if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
    Write-Host "  Erreur: Fichier package.json introuvable dans '$frontendDir'" -ForegroundColor Red
    exit 1
}

# Verifier si Node.js est installe
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  OK Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  Erreur: Node.js n'est pas installe ou pas dans le PATH." -ForegroundColor Red
    exit 1
}

# Verifier si node_modules existe
Set-Location $frontendDir
if (Test-Path "node_modules") {
    Write-Host "  OK Dependances Node.js deja installees." -ForegroundColor Green
} else {
    Write-Host "  Installation des dependances Node.js..." -ForegroundColor Gray
    npm install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK Dependances Node.js installees." -ForegroundColor Green
    } else {
        Write-Host "  Attention: erreur lors de npm install (code: $LASTEXITCODE)" -ForegroundColor Yellow
    }
}

# ============================================
# ETAPE 5: Création du fichier .env si nécessaire
# ============================================
Write-Host ""
Write-Host "[5/6] Configuration (.env)..." -ForegroundColor Yellow

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
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $backendDir ".env"), $envContent, $utf8NoBom)
    Write-Host "  OK Fichier .env cree." -ForegroundColor Green
} else {
    Write-Host "  OK Fichier .env deja present." -ForegroundColor Green
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
Write-Host "  OK Application lancee avec succes !" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend :  http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend : http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API Docs : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Les serveurs s'executent dans des fenetres separees." -ForegroundColor Yellow
Write-Host "  Fermez ces fenetres pour arreter les serveurs." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Modeles Ollama stockes dans : $modelsDir" -ForegroundColor Gray
Write-Host ""
