import { auth } from '../auth/client.js'

export async function api(path, options = {}) {
  const base = import.meta.env.VITE_GRIDYN_API_BASE_URL || ''
  const { data } = auth ? await auth.auth.getSession() : { data: { session: null } }
  const headers = new Headers(options.headers || {})
  if (data.session?.access_token) headers.set('Authorization', `Bearer ${data.session.access_token}`)
  const response = await fetch(`${base}${path}`, { ...options, headers })
  let body
  const type = response.headers.get('content-type') || ''
  if (type.includes('application/json')) body = await response.json()
  else body = await response.text()
  if (!response.ok) {
    const detail = body?.detail || body
    throw new Error(detail?.message || body?.message || String(body) || `HTTP ${response.status}`)
  }
  return body
}

export async function downloadReport(path, filename) {
  const content = await api(path)
  const blob = new Blob([typeof content === 'string' ? content : JSON.stringify(content, null, 2)],
    { type: filename.endsWith('.md') ? 'text/markdown' : 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function post(path, data) {
  return api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
