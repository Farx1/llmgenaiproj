# Test script pour vérifier l'endpoint RAG stats
Write-Host "`n=== Test de l'endpoint RAG Stats ===" -ForegroundColor Cyan
Write-Host "Attente de 3 secondes pour que le backend soit prêt..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/documents/rag/stats" -Method Get -ErrorAction Stop
    
    Write-Host "`n✅ Réponse reçue:" -ForegroundColor Green
    Write-Host "  Documents indexés: $($response.collection_info.document_count)" -ForegroundColor $(if ($response.collection_info.document_count -gt 0) { "Green" } else { "Red" })
    Write-Host "  Statut: $($response.collection_info.status)" -ForegroundColor $(if ($response.collection_info.status -eq "active") { "Green" } else { "Yellow" })
    Write-Host "  Sources uniques: $($response.total_sources)" -ForegroundColor Green
    
    if ($response.collection_info.document_count -eq 0) {
        Write-Host "`n⚠️  ATTENTION: L'endpoint retourne 0 documents alors que le test au démarrage montre 93,239 documents!" -ForegroundColor Red
        Write-Host "   Le backend doit être redémarré pour charger le nouveau code." -ForegroundColor Yellow
    } else {
        Write-Host "`n✅ SUCCESS: L'endpoint fonctionne correctement!" -ForegroundColor Green
    }
} catch {
    Write-Host "`n❌ Erreur lors de l'appel à l'endpoint:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "`nVérifiez que le backend est bien démarré sur http://localhost:8000" -ForegroundColor Yellow
}

