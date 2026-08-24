import { Fragment, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { apiGet, apiPost, apiUrl, formatDate } from '../api.js'
import { parseCitations, findSource } from '../utils/citations.js'
import ThemeToggle from '../components/ThemeToggle.jsx'

function DossierCard({ dossier, selected, onSelect }) {
  const sourceCount = Array.isArray(dossier.sources) ? dossier.sources.length : 0
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left bg-surface rounded-2xl p-5 border transition duration-200 ease-out break-words cursor-pointer hover:-translate-y-0.5 hover:shadow-[0_16px_40px_-24px_rgba(23,23,23,0.25)] ${
        selected
          ? 'border-accent ring-2 ring-accent/40'
          : 'border-line hover:border-faint'
      }`}
    >
      <p className="font-medium text-ink break-words">{dossier.question}</p>
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-xs text-faint">{formatDate(dossier.created_at)}</span>
        <span className="text-xs rounded-full bg-bg border border-line px-2.5 py-0.5 text-muted">
          {sourceCount === 1 ? '1 source' : `${sourceCount} sources`}
        </span>
      </div>
    </button>
  )
}

function CitationChip({ n, onOpen }) {
  return (
    <button
      type="button"
      className="align-super text-[11px] leading-none mx-0.5 px-1.5 py-0.5 rounded-full bg-accent/25 text-accent-deep hover:bg-accent/45 transition duration-200 ease-out cursor-pointer"
      aria-label={`Open source ${n}`}
      onClick={() => onOpen(n)}
    >
      {n}
    </button>
  )
}

function renderTextWithCitations(text, onOpenSource) {
  return parseCitations(text).map((part, i) =>
    part.type === 'cite' ? (
      <CitationChip key={i} n={part.n} onOpen={onOpenSource} />
    ) : (
      <Fragment key={i}>{part.value}</Fragment>
    ),
  )
}

function DossierView({ dossier, onClose, onOpenSource }) {
  const findings = Array.isArray(dossier.findings) ? dossier.findings : []
  const notes = Array.isArray(dossier.notes) ? dossier.notes : []
  const sources = Array.isArray(dossier.sources) ? dossier.sources : []
  return (
    <section className="bg-surface text-ink rounded-3xl p-5 sm:p-7 border border-line shadow-[0_1px_2px_rgba(23,23,23,0.04)] break-words">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <span className="text-xs uppercase tracking-wide text-faint">
          {formatDate(dossier.created_at)}
        </span>
        <span className="flex items-center gap-2">
          <a
            href={apiUrl(`/api/dossiers/${dossier.dossier_id}/export`)}
            download
            className="text-xs font-medium uppercase tracking-wide border border-line rounded-full px-3 py-1 text-muted hover:text-ink hover:border-faint transition duration-200 ease-out"
          >
            Export .md
          </a>
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-medium uppercase tracking-wide text-faint hover:text-ink transition duration-200 ease-out cursor-pointer"
          >
            Close view
          </button>
        </span>
      </div>

      <h2 className="font-display text-xl font-semibold tracking-tight text-ink break-words mt-3">
        {dossier.question}
      </h2>

      <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-muted mt-7 mb-2">
        Answer
      </h3>
      <p className="text-base leading-relaxed break-words">
        {renderTextWithCitations(dossier.answer, onOpenSource)}
      </p>

      <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-muted mt-7 pt-5 border-t border-line mb-2">
        Key Findings
      </h3>
      {findings.length === 0 ? (
        <p className="text-sm text-faint">No entries</p>
      ) : (
        <ul className="list-disc pl-5 space-y-1">
          {findings.map((f, i) => (
            <li key={i} className="break-words">
              {renderTextWithCitations(f, onOpenSource)}
            </li>
          ))}
        </ul>
      )}

      <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-muted mt-7 pt-5 border-t border-line mb-2">
        Detailed Notes
      </h3>
      {notes.length === 0 ? (
        <p className="text-sm text-faint">No entries</p>
      ) : (
        <ul className="list-disc pl-5 space-y-1">
          {notes.map((note, i) => (
            <li key={i} className="break-words">
              {renderTextWithCitations(note, onOpenSource)}
            </li>
          ))}
        </ul>
      )}

      <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-muted mt-7 pt-5 border-t border-line mb-2">
        Sources
      </h3>
      {sources.length === 0 ? (
        <p className="text-sm text-faint">No entries</p>
      ) : (
        <ol className="space-y-3">
          {sources.map((s, i) => (
            <li key={s.n ?? i} className="flex items-baseline gap-2">
              <span className="w-6 h-6 rounded-full bg-accent/25 text-accent-deep text-xs font-semibold flex items-center justify-center shrink-0">
                {s.n}
              </span>
              <span className="min-w-0">
                <span className="font-medium break-words">{s.title}</span>
                <span className="block text-sm text-muted break-words">{s.excerpt}</span>
              </span>
            </li>
          ))}
        </ol>
      )}

      <ThreadPanel key={dossier.dossier_id} dossier={dossier} onOpenSource={onOpenSource} />
    </section>
  )
}

function ThreadPanel({ dossier, onOpenSource }) {
  const [thread, setThread] = useState([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState('')

  useEffect(() => {
    let ignore = false
    ;(async () => {
      try {
        const data = await apiGet(`/api/dossiers/${dossier.dossier_id}/thread`)
        if (!ignore) setThread(data)
      } catch {
        // history is non-critical; leave the thread empty on failure
      }
    })()
    return () => {
      ignore = true
    }
  }, [dossier.dossier_id])

  async function handleSend() {
    if (draft.trim() === '' || sending) return
    const text = draft.trim()
    setThread((prev) => [...prev, { role: 'user', text, sources_used: [], _pending: true }])
    setDraft('')
    setSendError('')
    setSending(true)
    try {
      const updated = await apiPost(`/api/dossiers/${dossier.dossier_id}/thread`, { message: text })
      setThread(updated)
    } catch (err) {
      setThread((prev) => prev.filter((m) => !m._pending))
      setSendError(err.message || 'Failed to send')
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-muted mt-7 pt-5 border-t border-line mb-2">
        Thread
      </h3>
      <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
        {thread.map((msg, i) => {
          const isUser = msg.role === 'user'
          return (
            <div key={i} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm break-words whitespace-pre-line ${
                  isUser
                    ? `bg-ink text-surface rounded-2xl${msg._pending ? ' opacity-70' : ''}`
                    : 'bg-surface text-ink border border-line rounded-2xl'
                }`}
              >
                {isUser ? msg.text : renderTextWithCitations(msg.text, onOpenSource)}
              </div>
              {!isUser && Array.isArray(msg.sources_used) && msg.sources_used.length > 0 ? (
                <p className="text-[11px] text-faint mt-0.5">
                  Cites {msg.sources_used.length} sources
                </p>
              ) : null}
            </div>
          )
        })}
      </div>

      {sendError ? (
        <p className="text-sm text-red-600 dark:text-red-400 break-words mt-2">{sendError}</p>
      ) : null}

      <textarea
        rows={2}
        maxLength={500}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Ask a follow-up..."
        aria-label="Follow-up question"
        className="w-full bg-bg border border-line rounded-full px-5 py-3 text-sm text-ink placeholder:text-faint focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/20 resize-none mt-3"
      />
      <div className="flex items-center justify-between gap-3 mt-2 flex-wrap">
        <span className="text-xs text-faint">{draft.length}/500</span>
        <button
          type="button"
          onClick={handleSend}
          disabled={draft.trim() === '' || sending}
          className="inline-flex items-center gap-2 bg-neutral-900 text-white rounded-full px-4 py-2 text-sm font-semibold transition duration-200 ease-out hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
        >
          {sending ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  )
}

function SourceDrawer({ n, dossier, onClose }) {
  useEffect(() => {
    if (n === null) return undefined
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [n, onClose])

  if (n === null) return null

  const source = findSource(dossier?.sources ?? [], n)

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[2px]" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-full bg-surface text-ink p-6 overflow-y-auto border-l border-line shadow-2xl sm:top-4 sm:right-4 sm:bottom-4 sm:h-auto sm:w-96 sm:rounded-3xl sm:border max-sm:top-auto max-sm:h-auto max-sm:max-h-[70dvh] max-sm:rounded-t-3xl max-sm:border-l-0 max-sm:border-t">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wide text-faint">Source {n}</span>
          <button
            type="button"
            aria-label="Close drawer"
            onClick={onClose}
            className="text-faint hover:text-ink transition duration-200 ease-out cursor-pointer"
          >
            ✕
          </button>
        </div>
        <h3 className="font-display text-lg font-semibold tracking-tight text-ink break-words mt-3">
          {source && source.title ? source.title : 'Untitled source'}
        </h3>
        <p className="text-sm text-muted whitespace-pre-line break-words mt-3">
          {source ? source.excerpt : ''}
        </p>
        {!source ? <p className="text-sm text-red-600 dark:text-red-400 mt-3">Not found.</p> : null}
        {source && source.url && /^https?:\/\//i.test(source.url) ? (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-4 text-sm font-medium text-accent-deep hover:underline transition duration-200 ease-out"
          >
            Open source ↗
          </a>
        ) : null}
      </div>
    </div>
  )
}

export default function ProjectPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [dossiers, setDossiers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [researching, setResearching] = useState(false)
  const [askError, setAskError] = useState('')

  const [selectedDossier, setSelectedDossier] = useState(null)
  const [openSourceN, setOpenSourceN] = useState(null)

  // Handoff from the home ask-box: the question rides in via router state and
  // pre-fills the composer. Consumed exactly once on mount (see effect below).
  const pendingQuestion = location.state?.pendingQuestion ?? null
  const [question, setQuestion] = useState(pendingQuestion ?? '')
  const handoffConsumedRef = useRef(false)

  useEffect(() => {
    let ignore = false
    setLoading(true)
    ;(async () => {
      try {
        const [projectData, dossierData] = await Promise.all([
          apiGet(`/api/projects/${id}`),
          apiGet(`/api/projects/${id}/dossiers`),
        ])
        if (!ignore) {
          setProject(projectData)
          setDossiers(dossierData)
          setError('')
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || 'Failed to load project')
        }
      } finally {
        if (!ignore) {
          setLoading(false)
        }
      }
    })()
    return () => {
      ignore = true
    }
  }, [id, reloadKey])

  function handleRetry() {
    setReloadKey((k) => k + 1)
  }

  // Shared research mutation used by both the composer form and the home
  // ask-box handoff. Returns true when a dossier was created.
  async function runResearch(text) {
    setResearching(true)
    setAskError('')
    try {
      const created = await apiPost(`/api/projects/${id}/research`, { question: text })
      setDossiers((prev) => [created, ...prev])
      return true
    } catch (err) {
      setAskError(err.message || 'Research failed')
      return false
    } finally {
      setResearching(false)
    }
  }

  async function handleResearch(e) {
    e.preventDefault()
    if (question.trim() === '' || researching) return
    const ok = await runResearch(question.trim())
    if (ok) setQuestion('')
  }

  // Auto-submit the handed-off question exactly once. The ref guard keeps
  // StrictMode's double effect invocation from firing two research POSTs, and
  // the router state is cleared so refresh/back cannot resubmit it.
  useEffect(() => {
    if (!pendingQuestion || handoffConsumedRef.current) return undefined
    handoffConsumedRef.current = true
    navigate(location.pathname, { replace: true, state: null })
    runResearch(pendingQuestion).then((ok) => {
      if (ok) setQuestion('')
    })
    return undefined
    // oxlint-disable-next-line react-hooks/exhaustive-deps -- deliberate consume-once-on-mount handoff
  }, [])

  const counterLong = question.length > 480

  return (
    <div className="min-h-dvh bg-bg">
      <ThemeToggle />
      <div className="max-w-6xl mx-auto w-full px-6 py-10">
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink transition duration-200 ease-out mt-1">
          ← All projects
        </Link>

        {loading ? (
          <div className="flex justify-center py-16">
            <p className="text-sm text-faint">Loading project...</p>
          </div>
        ) : error ? (
          <div className="rounded-2xl bg-red-50 border border-red-200 text-red-600 px-4 py-3 flex items-center justify-between gap-3 flex-wrap mt-4 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-400">
            <span className="break-words">{error}</span>
            <button
              onClick={handleRetry}
              className="rounded-full border border-red-200 bg-white px-4 py-1.5 text-sm font-medium text-red-600 hover:bg-red-100 transition duration-200 ease-out shrink-0 dark:border-red-500/30 dark:bg-transparent dark:text-red-400 dark:hover:bg-red-500/10"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            <header className="mt-4 mb-8">
              <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight text-ink break-words">
                {project ? project.title : `Project ${id}`}
              </h1>
              {project && project.logline ? (
                <p className="text-muted text-sm sm:text-base leading-relaxed break-words mt-2 max-w-2xl">
                  {project.logline}
                </p>
              ) : null}
              {project && project.genre ? (
                <div className="mt-3">
                  <span className="rounded-full bg-accent/20 text-accent-deep px-2.5 py-0.5 text-xs font-medium">
                    {project.genre}
                  </span>
                </div>
              ) : null}
            </header>

            <section className="bg-surface border border-line rounded-3xl p-4 sm:p-5 shadow-[0_1px_2px_rgba(23,23,23,0.04)] transition duration-200 ease-out focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/20 max-w-3xl">
              <form onSubmit={handleResearch}>
                <label htmlFor="research-question" className="block text-xs font-medium text-muted mb-1.5 px-2">
                  Ask a research question
                </label>
                <textarea
                  id="research-question"
                  maxLength={500}
                  rows={3}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask about the world of your script..."
                  className="w-full resize-y bg-transparent px-2 py-1.5 text-sm text-ink placeholder:text-faint focus:outline-none"
                />
                {askError ? (
                  <div className="rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm px-3.5 py-2.5 mx-2 mb-2 break-words dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-400">
                    {askError}
                  </div>
                ) : null}
                <div className="flex items-center justify-between gap-3 mt-1 flex-wrap">
                  <span className={`text-xs px-2 ${counterLong ? 'text-accent-deep' : 'text-faint'}`}>
                    {question.length}/500
                  </span>
                  <button
                    type="submit"
                    disabled={question.trim() === '' || researching}
                    className="inline-flex items-center gap-2 bg-neutral-900 text-white rounded-full px-5 py-2 text-sm font-semibold transition duration-200 ease-out hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
                  >
                    {researching ? (
                      <>
                        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white align-[-2px] dark:border-neutral-900/30 dark:border-t-neutral-900" />
                        Researching...
                      </>
                    ) : (
                      'Research'
                    )}
                  </button>
                </div>
              </form>
            </section>

            <div className="space-y-4 mt-8">
              {researching ? (
                <div aria-hidden="true" className="space-y-4">
                  {[0, 1].map((i) => (
                    <div key={i} className="bg-surface border border-line rounded-2xl p-5">
                      <div className="skeleton h-4 w-1/2 rounded-full" />
                      <div className="flex items-center gap-2 mt-3">
                        <div className="skeleton h-3 w-20 rounded-full" />
                        <div className="skeleton h-5 w-24 rounded-full" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
              {dossiers.length === 0 ? (
                <p className="text-center text-faint py-10">
                  No dossiers yet - ask your first question above
                </p>
              ) : (
                dossiers.map((d) => (
                  <DossierCard
                    key={d.dossier_id}
                    dossier={d}
                    selected={selectedDossier === d}
                    onSelect={() => setSelectedDossier(d)}
                  />
                ))
              )}
            </div>

            {selectedDossier ? (
              <div className="mt-4 max-w-3xl">
                <DossierView
                  dossier={selectedDossier}
                  onClose={() => setSelectedDossier(null)}
                  onOpenSource={setOpenSourceN}
                />
              </div>
            ) : null}

            <SourceDrawer
              n={openSourceN}
              dossier={selectedDossier}
              onClose={() => setOpenSourceN(null)}
            />
          </>
        )}
      </div>
    </div>
  )
}
