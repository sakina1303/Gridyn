export async function api(path, options = {}) {
  const response = await fetch(path, options)
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

export function post(path, data) {
  return api(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}
