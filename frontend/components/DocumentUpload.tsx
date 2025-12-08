'use client'

import { useState } from 'react'
import { Upload, FileText, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import axios from 'axios'

export default function DocumentUpload() {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setUploadStatus('idle')
      setMessage('')
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setIsUploading(true)
    setUploadStatus('idle')
    setMessage('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      )

      setUploadStatus('success')
      setMessage(`Document uploaded successfully! ${response.data.chunks} chunks processed.`)
      setFile(null)
      
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (error: any) {
      setUploadStatus('error')
      setMessage(error.response?.data?.detail || 'Error uploading document. Please try again.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-semibold mb-4 flex items-center space-x-2">
        <FileText className="h-5 w-5 text-primary-600" />
        <span>Upload Documents</span>
      </h2>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select a document
          </label>
          <input
            id="file-input"
            type="file"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-lg file:border-0
              file:text-sm file:font-semibold
              file:bg-primary-50 file:text-primary-700
              hover:file:bg-primary-100
              cursor-pointer"
            accept=".txt,.pdf,.md,.doc,.docx"
            disabled={isUploading}
          />
        </div>

        {file && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-sm text-gray-700">
              <span className="font-medium">Selected:</span> {file.name}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Size: {(file.size / 1024).toFixed(2)} KB
            </p>
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!file || isUploading}
          className="w-full bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          {isUploading ? (
            <>
              <Loader2 className="animate-spin h-5 w-5" />
              <span>Uploading...</span>
            </>
          ) : (
            <>
              <Upload className="h-5 w-5" />
              <span>Upload Document</span>
            </>
          )}
        </button>

        {message && (
          <div
            className={`p-3 rounded-lg flex items-start space-x-2 ${
              uploadStatus === 'success'
                ? 'bg-green-50 text-green-800'
                : uploadStatus === 'error'
                ? 'bg-red-50 text-red-800'
                : ''
            }`}
          >
            {uploadStatus === 'success' ? (
              <CheckCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            ) : uploadStatus === 'error' ? (
              <XCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
            ) : null}
            <p className="text-sm">{message}</p>
          </div>
        )}

        <div className="text-xs text-gray-500 mt-4">
          <p className="mb-1">Supported formats: TXT, PDF, MD, DOC, DOCX</p>
          <p>Documents will be processed and added to the knowledge base for better answers.</p>
        </div>
      </div>
    </div>
  )
}

