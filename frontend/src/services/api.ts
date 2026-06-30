import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── Profile ────────────────────────────────────────────────────────────────

export const createProfile = (data) =>
  api.post('/api/profile', data).then((r) => r.data)

export const updateProfile = (profileId, data) =>
  api.put(`/api/profile/${profileId}`, data).then((r) => r.data)

export const getProfile = async (profileId) => {
  try {
    const r = await api.get(`/api/profile/${profileId}`)
    return r.data
  } catch (error) {
    if (error.response?.status === 404) {
      localStorage.removeItem('labelx_profile_id')
      window.location.href = '/profile'
    }
    throw error
  }
}

// ── History ────────────────────────────────────────────────────────────────

export const getHistory = (profileId, limit = 20) =>
  api.get(`/api/history/${profileId}`, { params: { limit } }).then((r) => r.data)

// ── Analysis (SSE streaming via fetch + ReadableStream) ────────────────────

export async function* streamAnalysis(profileId, ingredients, rawText = null) {
  const body = JSON.stringify({
    profile_id: profileId,
    ingredients,
    raw_text: rawText,
  })

  const url = `${BASE_URL}/api/analyze`
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    if (response.status === 404 && err.detail?.includes('Profile not found')) {
      localStorage.removeItem('labelx_profile_id')
      window.location.href = '/profile'
    }
    throw new Error(err.detail || `Server error: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw) {
          try {
            yield JSON.parse(raw)
          } catch {
            // Ignore parse errors
          }
        }
      }
    }
  }
}

// ── Image OCR analysis ────────────────────────────────────────────────────

export async function* streamImageAnalysis(profileId, imageFile) {
  const formData = new FormData()
  formData.append('profile_id', profileId)
  formData.append('file', imageFile)

  const url = `${BASE_URL}/api/analyze/image`
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    if (response.status === 404 && err.detail?.includes('Profile not found')) {
      localStorage.removeItem('labelx_profile_id')
      window.location.href = '/profile'
    }
    throw new Error(err.detail || `Server error: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw) {
          try {
            yield JSON.parse(raw)
          } catch {
            // Ignore
          }
        }
      }
    }
  }
}

export default api
