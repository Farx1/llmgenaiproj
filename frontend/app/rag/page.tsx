'use client'

import { useState, useEffect } from 'react'
import { Search, Database, FileText, Image as ImageIcon, ExternalLink, Loader2 } from 'lucide-react'

interface RAGStats {
  collection_info: {
    name: string
    document_count: number
    status: string
  }
  sample_sources: Array<{
    source: string
    title: string
    chunks: number
    file_type: string
    scraped_from: string
  }>
  total_sources: number
}

interface SearchResult {
  content: string
  full_content: string
  metadata: any
  score: number
  source: string
  title: string
  images: string[]
}

interface Source {
  source: string
  title: string
  chunks: number
  file_type: string
  scraped_from: string
}

interface SourceChunk {
  id: string
  content: string
  preview: string
  metadata: any
  images: string[]
  chunk_index: number
  title: string
}

interface SourceDetails {
  source: string
  title: string
  total_chunks: number
  chunks: SourceChunk[]
  limit: number
  offset: number
  has_more: boolean
  file_type: string
  scraped_from: string
}

export default function RAGPage() {
  const [stats, setStats] = useState<RAGStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null)
  
  // Sources pagination
  const [sources, setSources] = useState<Source[]>([])
  const [sourcesLoading, setSourcesLoading] = useState(false)
  const [sourcesOffset, setSourcesOffset] = useState(0)
  const [sourcesLimit] = useState(20)
  const [hasMoreSources, setHasMoreSources] = useState(true)
  const [totalSources, setTotalSources] = useState(0)
  
  // Selected source details
  const [selectedSource, setSelectedSource] = useState<Source | null>(null)
  const [sourceDetails, setSourceDetails] = useState<SourceDetails | null>(null)
  const [sourceDetailsLoading, setSourceDetailsLoading] = useState(false)
  const [sourceChunksOffset, setSourceChunksOffset] = useState(0)
  const [sourceChunksLimit] = useState(20)

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetchRAGStats()
    fetchSources(0)
  }, [])

  const fetchSources = async (offset: number = 0) => {
    try {
      setSourcesLoading(true)
      const response = await fetch(
        `${apiUrl}/api/documents/rag/sources?limit=${sourcesLimit}&offset=${offset}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          mode: 'cors',
          credentials: 'omit',
          cache: 'no-cache',
        }
      )

      if (!response.ok) {
        throw new Error(`Backend responded with status ${response.status}`)
      }

      const data = await response.json()
      if (offset === 0) {
        setSources(data.sources || [])
      } else {
        setSources(prev => [...prev, ...(data.sources || [])])
      }
      setTotalSources(data.total || 0)
      setHasMoreSources(data.has_more || false)
      setSourcesOffset(offset + (data.sources?.length || 0))
    } catch (err: any) {
      console.error('Error fetching sources:', err)
      setError(`Erreur lors du chargement des sources: ${err.message}`)
    } finally {
      setSourcesLoading(false)
    }
  }

  const loadMoreSources = () => {
    if (!sourcesLoading && hasMoreSources) {
      fetchSources(sourcesOffset)
    }
  }

  const fetchSourceDetails = async (source: Source, offset: number = 0) => {
    try {
      setSourceDetailsLoading(true)
      const encodedSource = encodeURIComponent(source.source)
      const response = await fetch(
        `${apiUrl}/api/documents/rag/source/${encodedSource}?limit=${sourceChunksLimit}&offset=${offset}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          mode: 'cors',
          credentials: 'omit',
          cache: 'no-cache',
        }
      )

      if (!response.ok) {
        throw new Error(`Backend responded with status ${response.status}`)
      }

      const data = await response.json()
      if (offset === 0) {
        setSourceDetails(data)
      } else if (sourceDetails) {
        setSourceDetails({
          ...data,
          chunks: [...sourceDetails.chunks, ...data.chunks]
        })
      }
      setSourceChunksOffset(offset + (data.chunks?.length || 0))
    } catch (err: any) {
      console.error('Error fetching source details:', err)
      setError(`Erreur lors du chargement des détails: ${err.message}`)
    } finally {
      setSourceDetailsLoading(false)
    }
  }

  const handleSourceClick = (source: Source) => {
    setSelectedSource(source)
    setSourceChunksOffset(0)
    fetchSourceDetails(source, 0)
  }

  const loadMoreChunks = () => {
    if (selectedSource && sourceDetails && !sourceDetailsLoading && sourceDetails.has_more) {
      fetchSourceDetails(selectedSource, sourceChunksOffset)
    }
  }

  const fetchRAGStats = async () => {
    try {
      setLoading(true)
      setError('')
      
      // Create abort controller for timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 seconds timeout
      
      const response = await fetch(`${apiUrl}/api/documents/rag/stats`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        mode: 'cors',
        credentials: 'omit',
        signal: controller.signal,
        cache: 'no-cache',
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`Backend responded with status ${response.status}`)
      }

      const data = await response.json()
      setStats(data)
      setError('')
    } catch (err: any) {
      console.error('Error fetching RAG stats:', err)
      if (err.name === 'AbortError' || err.message?.includes('timeout') || err.message?.includes('aborted')) {
        setError(`Timeout: Le backend ne répond pas. Vérifiez que le serveur backend est démarré sur ${apiUrl}`)
      } else if (err.name === 'TypeError' || err.message?.includes('fetch') || err.message?.includes('Failed to fetch')) {
        setError(`Impossible de se connecter au backend sur ${apiUrl}. Vérifiez que le serveur backend est démarré.`)
      } else {
        setError(`Erreur lors du chargement des statistiques RAG: ${err.message || 'Erreur inconnue'}`)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    try {
      setSearching(true)
      const response = await fetch(
        `${apiUrl}/api/documents/rag/search?query=${encodeURIComponent(searchQuery)}&k=10`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          mode: 'cors',
          credentials: 'omit',
        }
      )

      if (!response.ok) {
        throw new Error(`Backend responded with status ${response.status}`)
      }

      const data = await response.json()
      setSearchResults(data.results || [])
      setError('')
    } catch (err: any) {
      console.error('Error searching RAG:', err)
      setError(`Erreur lors de la recherche: ${err.message}`)
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <main className="min-h-screen bg-gray-50" suppressHydrationWarning>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-2">
            <Database className="h-8 w-8 text-primary-600" />
            RAG - Base de Connaissances
          </h1>
          <p className="text-gray-600">
            Visualisez et explorez les données indexées dans le système RAG
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 text-sm font-medium">⚠️ Erreur de connexion</p>
            <p className="text-red-600 text-xs mt-1">{error}</p>
            <p className="text-red-600 text-xs mt-2">
              Pour démarrer le backend, exécutez: <code className="bg-red-100 px-1 rounded">cd backend && python main.py</code>
            </p>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            <span className="ml-2 text-gray-600">Chargement des statistiques...</span>
          </div>
        ) : stats ? (
          <div className="space-y-6">
            {/* Statistics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Documents indexés</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {stats.collection_info.document_count.toLocaleString()}
                    </p>
                  </div>
                  <FileText className="h-12 w-12 text-primary-600 opacity-50" />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Sources uniques</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">
                      {stats.total_sources.toLocaleString()}
                    </p>
                  </div>
                  <Database className="h-12 w-12 text-primary-600 opacity-50" />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Statut</p>
                    <p className="text-lg font-semibold text-gray-900 mt-2 capitalize">
                      {stats.collection_info.status}
                    </p>
                  </div>
                  <div
                    className={`h-3 w-3 rounded-full ${
                      stats.collection_info.status === 'active'
                        ? 'bg-green-500'
                        : 'bg-gray-400'
                    }`}
                  />
                </div>
              </div>
            </div>

            {/* Search Section */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Search className="h-5 w-5" />
                Rechercher dans la base de connaissances
              </h2>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Rechercher des informations..."
                  className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  suppressHydrationWarning
                />
                <button
                  onClick={handleSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
                  suppressHydrationWarning
                >
                  {searching ? (
                    <>
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Recherche...
                    </>
                  ) : (
                    <>
                      <Search className="h-5 w-5" />
                      Rechercher
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  Résultats de recherche ({searchResults.length})
                </h2>
                <div className="space-y-4">
                  {searchResults.map((result, index) => (
                    <div
                      key={index}
                      className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors cursor-pointer"
                      onClick={() => setSelectedResult(result)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900 mb-2">
                            {result.title}
                          </h3>
                          <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                            {result.content}
                          </p>
                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            <span>Score: {(result.score * 100).toFixed(1)}%</span>
                            <span className="flex items-center gap-1">
                              <FileText className="h-3 w-3" />
                              {result.source.split('/').pop()}
                            </span>
                            {result.images.length > 0 && (
                              <span className="flex items-center gap-1">
                                <ImageIcon className="h-3 w-3" />
                                {result.images.length} image(s)
                              </span>
                            )}
                          </div>
                        </div>
                        {result.images.length > 0 && (
                          <div className="ml-4">
                            <img
                              src={result.images[0]}
                              alt="Preview"
                              className="w-24 h-24 object-cover rounded"
                              onError={(e) => {
                                e.currentTarget.style.display = 'none'
                              }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sources List with Pagination */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                Sources indexées ({totalSources > 0 ? totalSources : stats?.total_sources || 0})
              </h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Source
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Chunks
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Origine
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sources.map((source, index) => (
                      <tr
                        key={index}
                        className="hover:bg-gray-50 cursor-pointer transition-colors"
                        onClick={() => handleSourceClick(source)}
                      >
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">
                            {source.title}
                          </div>
                          <div className="text-xs text-gray-500 truncate max-w-md">
                            {source.source}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {source.file_type || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {source.chunks}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span
                            className={`px-2 py-1 rounded ${
                              source.scraped_from === 'esilv_website_crawl4ai'
                                ? 'bg-blue-100 text-blue-800'
                                : 'bg-green-100 text-green-800'
                            }`}
                          >
                            {source.scraped_from === 'esilv_website_crawl4ai'
                              ? 'Site Web'
                              : 'Upload'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Load More Button */}
              {hasMoreSources && (
                <div className="mt-4 flex justify-center">
                  <button
                    onClick={loadMoreSources}
                    disabled={sourcesLoading}
                    className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
                  >
                    {sourcesLoading ? (
                      <>
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Chargement...
                      </>
                    ) : (
                      <>
                        Charger plus ({sources.length}/{totalSources})
                      </>
                    )}
                  </button>
                </div>
              )}
              
              {!hasMoreSources && sources.length > 0 && (
                <div className="mt-4 text-center text-sm text-gray-500">
                  Toutes les sources ont été chargées ({sources.length} sources)
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <p className="text-gray-600">Aucune donnée RAG disponible</p>
          </div>
        )}

        {/* Modal for source details */}
        {selectedSource && sourceDetails && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => {
              setSelectedSource(null)
              setSourceDetails(null)
            }}
          >
            <div
              className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-2xl font-bold text-gray-900">
                      {sourceDetails.title}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {sourceDetails.source}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedSource(null)
                      setSourceDetails(null)
                    }}
                    className="text-gray-400 hover:text-gray-600 text-2xl"
                  >
                    ✕
                  </button>
                </div>
                
                <div className="mb-4 flex gap-4 text-sm">
                  <div className="bg-gray-100 px-3 py-1 rounded">
                    <span className="font-semibold">Chunks:</span> {sourceDetails.total_chunks}
                  </div>
                  <div className="bg-gray-100 px-3 py-1 rounded">
                    <span className="font-semibold">Type:</span> {sourceDetails.file_type}
                  </div>
                  <div className="bg-gray-100 px-3 py-1 rounded">
                    <span className="font-semibold">Origine:</span>{' '}
                    {sourceDetails.scraped_from === 'esilv_website_crawl4ai' ? 'Site Web' : 'Upload'}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold text-gray-900">
                      Extraits ({sourceDetails.chunks.length} / {sourceDetails.total_chunks})
                    </h4>
                    {sourceDetails.chunks.length > 0 && (
                      <div className="text-sm text-gray-500">
                        Chunks {sourceDetails.chunks[0].chunk_index + 1} à {sourceDetails.chunks[sourceDetails.chunks.length - 1].chunk_index + 1}
                      </div>
                    )}
                  </div>
                  
                  {sourceDetailsLoading && sourceDetails.chunks.length === 0 ? (
                    <div className="flex justify-center items-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
                      <span className="ml-2 text-gray-600">Chargement des chunks...</span>
                    </div>
                  ) : (
                    <>
                      {sourceDetails.chunks.length === 0 ? (
                        <div className="text-center py-8 text-gray-500">
                          Aucun chunk trouvé pour cette source
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {sourceDetails.chunks.map((chunk, idx) => (
                            <div
                              key={chunk.id || idx}
                              className="border border-gray-200 rounded-lg p-5 hover:border-primary-300 transition-all bg-gray-50 hover:bg-white shadow-sm"
                            >
                              <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-200">
                                <div className="flex items-center gap-3">
                                  <span className="bg-primary-100 text-primary-700 px-2 py-1 rounded text-xs font-semibold">
                                    Chunk #{chunk.chunk_index + 1}
                                  </span>
                                  {chunk.images.length > 0 && (
                                    <span className="text-xs text-gray-600 flex items-center gap-1 bg-blue-50 px-2 py-1 rounded">
                                      <ImageIcon className="h-3 w-3" />
                                      {chunk.images.length} image{chunk.images.length > 1 ? 's' : ''}
                                    </span>
                                  )}
                                </div>
                                <span className="text-xs text-gray-400">
                                  {chunk.content.length} caractères
                                </span>
                              </div>
                              
                              <div className="prose prose-sm max-w-none">
                                <p className="text-gray-800 leading-relaxed whitespace-pre-wrap break-words">
                                  {chunk.content}
                                </p>
                              </div>
                              
                              {chunk.images.length > 0 && (
                                <div className="mt-4 pt-3 border-t border-gray-200">
                                  <h5 className="text-xs font-semibold text-gray-700 mb-2 flex items-center gap-1">
                                    <ImageIcon className="h-4 w-4" />
                                    Images associées ({chunk.images.length})
                                  </h5>
                                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                    {chunk.images.map((imgUrl, imgIdx) => (
                                      <a
                                        key={imgIdx}
                                        href={imgUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block group"
                                      >
                                        <div className="relative overflow-hidden rounded-lg border border-gray-200 hover:border-primary-400 transition-all">
                                          <img
                                            src={imgUrl}
                                            alt={`Image ${imgIdx + 1} du chunk ${chunk.chunk_index + 1}`}
                                            className="w-full h-32 object-cover group-hover:scale-105 transition-transform duration-200"
                                            onError={(e) => {
                                              e.currentTarget.style.display = 'none'
                                              const parent = e.currentTarget.parentElement
                                              if (parent) {
                                                parent.innerHTML = '<div class="w-full h-32 bg-gray-100 flex items-center justify-center text-xs text-gray-400">Image non disponible</div>'
                                              }
                                            }}
                                          />
                                          <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-10 transition-opacity flex items-center justify-center">
                                            <ExternalLink className="h-4 w-4 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                                          </div>
                                        </div>
                                      </a>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      
                      {sourceDetails.has_more && (
                        <div className="flex justify-center mt-4">
                          <button
                            onClick={loadMoreChunks}
                            disabled={sourceDetailsLoading}
                            className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
                          >
                            {sourceDetailsLoading ? (
                              <>
                                <Loader2 className="h-5 w-5 animate-spin" />
                                Chargement...
                              </>
                            ) : (
                              <>
                                Charger plus de chunks ({sourceDetails.chunks.length} / {sourceDetails.total_chunks})
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Modal for detailed search result */}
        {selectedResult && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onClick={() => setSelectedResult(null)}
          >
            <div
              className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-2xl font-bold text-gray-900">
                    {selectedResult.title}
                  </h3>
                  <button
                    onClick={() => setSelectedResult(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
                <div className="mb-4">
                  <p className="text-sm text-gray-600 mb-2">
                    <strong>Source:</strong> {selectedResult.source}
                  </p>
                  <p className="text-sm text-gray-600">
                    <strong>Score de similarité:</strong>{(selectedResult.score * 100).toFixed(1)}%
                  </p>
                </div>
                <div className="prose max-w-none mb-4">
                  <p className="text-gray-700 whitespace-pre-wrap">
                    {selectedResult.full_content}
                  </p>
                </div>
                {selectedResult.images.length > 0 && (
                  <div className="mt-4">
                    <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
                      <ImageIcon className="h-5 w-5" />
                      Images associées ({selectedResult.images.length})
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {selectedResult.images.map((imgUrl, idx) => (
                        <a
                          key={idx}
                          href={imgUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block"
                        >
                          <img
                            src={imgUrl}
                            alt={`Image ${idx + 1}`}
                            className="w-full h-32 object-cover rounded hover:opacity-80 transition-opacity"
                            onError={(e) => {
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  )
}

