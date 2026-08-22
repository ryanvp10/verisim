const BASE = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  let data = null
  try {
    data = await res.json()
  } catch {
    // non-JSON body; fall through to generic error handling
  }
  if (!res.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : null
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return data
}

export async function apiGet(path) {
  return request(path)
}

export async function apiPost(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function formatDate(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
