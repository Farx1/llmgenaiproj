# Script pour nettoyer le cache Next.js et redémarrer proprement
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Nettoyage du cache Next.js" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Arrêter tous les processus Node.js liés à Next.js sur le port 3000
Write-Host "`nArrêt des processus Next.js sur le port 3000..." -ForegroundColor Yellow
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
        Start-Sleep -Seconds 3
    } else {
        Write-Host "Aucun processus sur le port 3000" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Erreur lors de la vérification du port 3000" -ForegroundColor Yellow
}

# Attendre un peu pour que les fichiers soient libérés
Start-Sleep -Seconds 2

# Supprimer le cache .next
Write-Host "`nSuppression du cache .next..." -ForegroundColor Yellow
if (Test-Path ".next") {
    try {
        # Essayer plusieurs fois avec des délais
        $maxRetries = 5
        $retryCount = 0
        $success = $false
        
        while ($retryCount -lt $maxRetries -and -not $success) {
            try {
                Remove-Item -Recurse -Force .next -ErrorAction Stop
                Write-Host "✅ Cache .next supprimé avec succès" -ForegroundColor Green
                $success = $true
            } catch {
                $retryCount++
                if ($retryCount -lt $maxRetries) {
                    Write-Host "   Tentative $retryCount/$maxRetries..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 2
                } else {
                    Write-Host "⚠️  Impossible de supprimer .next après $maxRetries tentatives" -ForegroundColor Red
                    Write-Host "   Fermez tous les terminaux et navigateurs, puis réessayez" -ForegroundColor Yellow
                }
            }
        }
    } catch {
        Write-Host "⚠️  Erreur lors de la suppression de .next" -ForegroundColor Red
    }
} else {
    Write-Host "Pas de cache .next trouvé" -ForegroundColor Yellow
}

# Supprimer aussi node_modules/.cache si présent
if (Test-Path "node_modules\.cache") {
    try {
        Remove-Item -Recurse -Force node_modules\.cache -ErrorAction Stop
        Write-Host "✅ Cache node_modules/.cache supprimé" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Impossible de supprimer node_modules/.cache" -ForegroundColor Yellow
    }
}

# Supprimer .turbo si présent (cache Turbo)
if (Test-Path ".turbo") {
    try {
        Remove-Item -Recurse -Force .turbo -ErrorAction Stop
        Write-Host "✅ Cache .turbo supprimé" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Impossible de supprimer .turbo" -ForegroundColor Yellow
    }
}

Write-Host "`n✅ Nettoyage terminé!" -ForegroundColor Green
Write-Host "`nVous pouvez maintenant redémarrer le serveur avec: npm run dev" -ForegroundColor Cyan

