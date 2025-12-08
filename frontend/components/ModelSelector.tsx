'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

interface ModelSelectorProps {
  models: string[]
  selectedModel: string
  onModelChange: (model: string) => void
}

export default function ModelSelector({
  models,
  selectedModel,
  onModelChange,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="bg-white border border-gray-300 rounded-lg px-4 py-2 flex items-center space-x-2 hover:bg-gray-50"
      >
        <span className="text-sm font-medium text-gray-700">
          Model: <span className="text-primary-600">{selectedModel}</span>
        </span>
        <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full mt-2 bg-white border border-gray-300 rounded-lg shadow-lg z-20 min-w-[200px]">
            {models.map((model) => (
              <button
                key={model}
                onClick={() => {
                  onModelChange(model)
                  setIsOpen(false)
                }}
                className={`w-full text-left px-4 py-2 hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                  selectedModel === model ? 'bg-primary-50 text-primary-600' : 'text-gray-700'
                }`}
              >
                {model}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

