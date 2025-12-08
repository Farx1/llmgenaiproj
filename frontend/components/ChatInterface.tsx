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

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/chat/`,
        {
          message: userMessage.content,
          conversation_history: messages.map(m => ({
            role: m.role,
            content: m.content
          })),
          model: selectedModel
        },
        {
          timeout: 60000, // 60 seconds timeout for LLM responses
        }
      )

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.answer,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      console.error('Error sending message:', error)
      
      let errorText = 'Sorry, I encountered an error. Please try again.'
      
      if (error.code === 'ECONNREFUSED' || error.message?.includes('Network Error') || error.message?.includes('Failed to fetch')) {
        errorText = '❌ Cannot connect to the backend server. Please make sure the backend is running on http://localhost:8000'
      } else if (error.response?.status === 500) {
        errorText = `Server error: ${error.response?.data?.detail || 'Internal server error'}. Please check the backend logs.`
      } else if (error.response?.status === 404) {
        errorText = 'API endpoint not found. Please check the backend configuration.'
      } else if (error.response?.data?.detail) {
        errorText = `Error: ${error.response.data.detail}`
      }
      
      const errorMessage: Message = {
        role: 'assistant',
        content: errorText,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
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
              <p className="whitespace-pre-wrap break-words text-base leading-relaxed font-normal">{message.content}</p>
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

