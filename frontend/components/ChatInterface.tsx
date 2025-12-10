'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import axios from 'axios'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: Date
}

interface ChatInterfaceProps {
  selectedModel: string
  availableModels?: string[]
}

export default function ChatInterface({ selectedModel, availableModels = [] }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading || availableModels.length === 0) return

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Create assistant message placeholder for streaming
    const assistantMessageId = Date.now()
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date()
    }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      // Try streaming endpoint first for better UX
      let useStreaming = true
      let response: Response
      
      try {
        console.log('🚀 Sending streaming request to:', `${apiUrl}/api/chat/stream`)
        console.log('📝 Message:', userMessage.content.substring(0, 100))
        console.log('🤖 Model:', selectedModel)
        
        response = await fetch(`${apiUrl}/api/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.content,
            conversation_history: messages.map(m => ({
              role: m.role,
              content: m.content
            })),
            model: selectedModel
          }),
          signal: AbortSignal.timeout(120000), // 120 seconds timeout for streaming
        })
        
        console.log('✅ Streaming response received, status:', response.status)

        if (!response.ok) {
          if (response.status === 404) {
            // Streaming not available, fallback to non-streaming
            useStreaming = false
          } else {
            throw new Error(`HTTP error! status: ${response.status}`)
          }
        }
      } catch (streamError: any) {
        // If streaming fails, fallback to non-streaming
        console.warn('Streaming not available, using fallback:', streamError)
        useStreaming = false
      }

      if (useStreaming && response!.ok) {
        // Handle streaming response
        const reader = response!.body?.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        if (!reader) {
          throw new Error('No response body reader available')
        }

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.type === 'chunk') {
                  // Append chunk to assistant message
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'assistant') {
                      lastMsg.content += data.content || ''
                    }
                    return newMessages
                  })
                } else if (data.type === 'done') {
                  setIsLoading(false)
                  return
                } else if (data.type === 'error') {
                  throw new Error(data.error || 'Unknown streaming error')
                }
              } catch (parseError) {
                console.warn('Failed to parse SSE data:', line, parseError)
              }
            }
          }
        }
        setIsLoading(false)
      } else {
        // Fallback to non-streaming endpoint
        const fallbackResponse = await fetch(`${apiUrl}/api/chat/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.content,
            conversation_history: messages.map(m => ({
              role: m.role,
              content: m.content
            })),
            model: selectedModel
          }),
          signal: AbortSignal.timeout(60000), // 60 seconds timeout
        })

        if (!fallbackResponse.ok) {
          throw new Error(`HTTP error! status: ${fallbackResponse.status}`)
        }

        const data = await fallbackResponse.json()
        
        // Update the last message (assistant message) with the full response
        setMessages(prev => {
          const newMessages = [...prev]
          const lastMsg = newMessages[newMessages.length - 1]
          if (lastMsg.role === 'assistant') {
            lastMsg.content = data.answer || 'No answer received'
          }
          return newMessages
        })
        
        setIsLoading(false)
      }
    } catch (error: any) {
      console.error('Error sending message:', error)
      
      let errorText = 'Sorry, I encountered an error. Please try again.'
      
      if (error.message?.includes('Failed to fetch') || error.message?.includes('Network')) {
        errorText = '❌ Cannot connect to the backend server. Please make sure the backend is running on http://localhost:8000'
      } else if (error.message?.includes('HTTP error')) {
        errorText = `Server error: ${error.message}. Please check the backend logs.`
      } else {
        errorText = `Error: ${error.message || 'Unknown error'}`
      }
      
      // Update the last message (assistant message) with error
      setMessages(prev => {
        const newMessages = [...prev]
        const lastMsg = newMessages[newMessages.length - 1]
        if (lastMsg.role === 'assistant' && lastMsg.content === '') {
          lastMsg.content = errorText
        } else {
          // If streaming already started, append error
          newMessages.push({
            role: 'assistant',
            content: errorText,
            timestamp: new Date()
          })
        }
        return newMessages
      })
    } finally {
      setIsLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg flex flex-col h-[600px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            {availableModels.length > 0 ? (
              <>
                <p className="text-lg mb-2 font-semibold">👋 Welcome to ESILV Smart Assistant!</p>
                <p className="text-sm">Ask me anything about ESILV programs, admissions, courses, or news.</p>
              </>
            ) : (
              <>
                <p className="text-lg mb-2 font-semibold text-red-600">⚠️ No Models Available</p>
                <p className="text-sm">Please install at least one Ollama model to use the assistant.</p>
                <p className="text-xs mt-2 text-gray-400">Run: ollama pull &lt;model_name&gt;</p>
              </>
            )}
          </div>
        )}
        
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 chat-message ${
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="whitespace-pre-wrap break-words text-base leading-relaxed font-normal">
                {message.content.split('\n').map((line, lineIdx) => {
                  // Check if line contains markdown image link: [![alt](img_url)](img_url)
                  const imageLinkMatch = line.match(/\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)/);
                  if (imageLinkMatch) {
                    const [, alt, imgUrl, linkUrl] = imageLinkMatch;
                    return (
                      <div key={lineIdx} className="my-2">
                        <a 
                          href={linkUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="block hover:opacity-90 transition-opacity"
                        >
                          <img 
                            src={imgUrl} 
                            alt={alt || 'Image'} 
                            className="max-w-full h-auto rounded-lg shadow-md border border-gray-200"
                            onError={(e) => {
                              // Hide image if it fails to load
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                        </a>
                        <a 
                          href={linkUrl} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 mt-1 block"
                        >
                          🔗 Ouvrir l'image
                        </a>
                      </div>
                    );
                  }
                  // Regular text line
                  return <p key={lineIdx}>{line}</p>;
                })}
              </div>
              {message.timestamp && (
                <p className={`text-xs mt-1 ${
                  message.role === 'user' ? 'text-primary-100' : 'text-gray-500'
                }`}>
                  {message.timestamp.toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <Loader2 className="animate-spin h-5 w-5 text-gray-500" />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t p-4" suppressHydrationWarning>
        <div className="flex space-x-2" suppressHydrationWarning>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={availableModels.length > 0 ? "Type your message..." : "No models available. Please install a model first."}
                className="flex-1 resize-none border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-gray-900 disabled:bg-gray-100 disabled:cursor-not-allowed"
                rows={2}
                disabled={isLoading || availableModels.length === 0}
                suppressHydrationWarning
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim() || availableModels.length === 0}
                className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                suppressHydrationWarning
              >
            {isLoading ? (
              <Loader2 className="animate-spin h-5 w-5" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

