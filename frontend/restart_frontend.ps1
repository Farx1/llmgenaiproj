# Script pour redémarrer proprement le frontend Next.js
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Redémarrage du Frontend Next.js" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Arrêter les processus sur le port 3000
Write-Host "`nArrêt des processus sur le port 3000..." -ForegroundColor Yellow
try {
    $port3000 = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($port3000) {
        foreach ($pid in $port3000) {
            try {
                Stop-Process -Id $pid -Force -ErrorAction Stop
                Write-Host "✅ Processus arrêté (PID: $pid)" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  Impossible d'arrêter le processus (PID: $pid)" -ForegroundColor Yellow
            }
        }
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "⚠️  Erreur lors de la vérification du port 3000" -ForegroundColor Yellow
}

# Nettoyer le cache
Write-Host "`nNettoyage du cache..." -ForegroundColor Yellow
if (Test-Path ".next") {
    try {
        Remove-Item -Recurse -Force .next -ErrorAction Stop
        Write-Host "✅ Cache .next supprimé" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Impossible de supprimer .next (peut-être verrouillé)" -ForegroundColor Yellow
    }
}

Start-Sleep -Seconds 1

# Vérifier que le backend est démarré
Write-Host "`nVérification du backend..." -ForegroundColor Yellow
$backendRunning = Test-NetConnection -ComputerName localhost -Port 8000 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $backendRunning) {
    Write-Host "⚠️  Le backend n'est pas démarré sur le port 8000" -ForegroundColor Red
    Write-Host "   Démarrez le backend avec: cd ..\backend && python main.py" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continuer quand même? (O/N)"
    if ($continue -ne "O" -and $continue -ne "o") {
        Write-Host "Arrêt du script" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✅ Backend détecté sur le port 8000" -ForegroundColor Green
}

# Démarrer le serveur
Write-Host "`nDémarrage du serveur Next.js..." -ForegroundColor Yellow
Write-Host "Le frontend sera accessible sur http://localhost:3000" -ForegroundColor Cyan
Write-Host "Appuyez sur Ctrl+C pour arrêter le serveur" -ForegroundColor Yellow
Write-Host ""

npm run dev

