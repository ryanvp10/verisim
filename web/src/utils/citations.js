export function parseCitations(text) {
  if (typeof text !== 'string' || text.length === 0) return []
  const parts = []
  const re = /\[(\d+)\]/g
  let lastIndex = 0
  let match
  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'cite', n: Number(match[1]) })
    lastIndex = match.index + match[0].length
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }
  return parts
}

export function findSource(sources, n) {
  if (!Array.isArray(sources)) return null
  const found = sources.find((s) => s && Number(s.n) === Number(n))
  return found || null
}
