'use client'

import { useState, useRef, useEffect } from 'react'
import ChatInterface from '@/components/ChatInterface'
import DocumentUpload from '@/components/DocumentUpload'
import ModelSelector from '@/components/ModelSelector'

export default function Home() {
  const [selectedModel, setSelectedModel] = useState<string>('llama3')
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [backendConnected, setBackendConnected] = useState<boolean>(false)
  const [backendError, setBackendError] = useState<string>('')

  useEffect(() => {
    // Fetch available models with retry logic
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    const fetchModels = async (retryCount = 0) => {
      try {
        // Create abort controller for timeout (fallback for browsers that don't support AbortSignal.timeout)
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 10000) // Increased to 10 seconds
        
        const response = await fetch(`${apiUrl}/api/chat/models`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          signal: controller.signal,
          // Add mode to handle CORS
          mode: 'cors',
          credentials: 'omit',
          cache: 'no-cache' // Prevent caching issues
        })
        
        clearTimeout(timeoutId)
        
        if (!response.ok) {
          throw new Error(`Backend responded with status ${response.status}`)
        }
        
        const data = await response.json()
        console.log('Models data received:', data)
        
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models)
          setSelectedModel(data.default || data.models[0])
          setBackendConnected(true)
          setBackendError('')
        } else {
          setBackendConnected(true)
          setAvailableModels([])
          setBackendError('Aucun modèle Ollama disponible. Installez au moins un modèle avec: ollama pull <nom_modele>')
        }
      } catch (err: any) {
        console.error('Error fetching models:', err)
        
        // Retry logic: retry up to 3 times with increasing delay
        if (retryCount < 3 && (err.name === 'TypeError' || err.name === 'AbortError' || err.message?.includes('fetch'))) {
          const delay = (retryCount + 1) * 2000 // 2s, 4s, 6s
          console.log(`Retrying in ${delay}ms... (attempt ${retryCount + 1}/3)`)
          setTimeout(() => fetchModels(retryCount + 1), delay)
          return
        }
        
        setBackendConnected(false)
        if (err.name === 'AbortError' || err.message?.includes('timeout') || err.message?.includes('aborted')) {
          setBackendError(`Backend timeout. Please make sure the backend server is running at ${apiUrl}`)
        } else if (err.name === 'TypeError' || err.message?.includes('fetch') || err.message?.includes('Failed to fetch')) {
          setBackendError(`Cannot connect to backend at ${apiUrl}. Please make sure the backend server is running.`)
        } else {
          setBackendError(`Backend error: ${err.message || 'Unknown error'}`)
        }
      }
    }
    
    fetchModels()
  }, [])

  return (
    <main className="min-h-screen bg-gray-50" suppressHydrationWarning>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            ESILV Smart Assistant
          </h1>
          <p className="text-gray-600">
            Ask questions about programs, admissions, courses, and get the latest news from ESILV.
          </p>
        </div>

        {backendError && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm font-medium">⚠️ Backend Connection Error</p>
            <p className="text-red-600 text-xs mt-1">{backendError}</p>
            <p className="text-red-600 text-xs mt-1">
              Please start the backend server: <code className="bg-red-100 px-1 rounded">cd backend && python main.py</code>
            </p>
          </div>
        )}
        
        {backendConnected && (
          <div className="mb-4 p-2 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-800 text-xs">✓ Backend connected</p>
          </div>
        )}

        {availableModels.length > 0 && (
          <div className="mb-6">
            <ModelSelector
              models={availableModels}
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
            />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <ChatInterface selectedModel={selectedModel} availableModels={availableModels} />
          </div>
          <div className="lg:col-span-1">
            <DocumentUpload />
          </div>
        </div>
      </div>
    </main>
  )
}

