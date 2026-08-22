import { Fragment, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGet, apiPost, formatDate } from '../api.js'
import { parseCitations, findSource } from '../utils/citations.js'

function DossierCard({ dossier, selected, onSelect }) {
  const sourceCount = Array.isArray(dossier.sources) ? dossier.sources.length : 0
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full text-left bg-[#171a21] rounded-xl p-4 border ${selected ? 'border-[#d97706]' : 'border-white/10'} hover:border-[#d97706]/60 transition break-words cursor-pointer`}
    >
      <p className="font-medium text-[#f7f4ec] break-words">{dossier.question}</p>
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-xs text-gray-500">{formatDate(dossier.created_at)}</span>
        <span className="text-xs rounded-full bg-white/10 px-2 py-0.5 text-gray-300">
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
      className="align-super text-[11px] leading-none mx-0.5 px-1.5 py-0.5 rounded-md bg-[#d97706]/20 text-[#b45309] hover:bg-[#d97706]/40 transition cursor-pointer"
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
    <section className="bg-[#f7f4ec] text-[#1a1a1a] rounded-xl p-5 sm:p-6 border border-white/10 break-words">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <span className="text-xs uppercase tracking-wide text-[#7a6a55]">
          {formatDate(dossier.created_at)}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-xs uppercase tracking-wide text-[#7a6a55] hover:text-[#1a1a1a] transition cursor-pointer"
        >
          Close view
        </button>
      </div>

      <h2 className="font-display text-xl text-[#1a1a1a] break-words mt-2">{dossier.question}</h2>

      <h3 className="font-display text-sm uppercase tracking-wider text-[#7a6a55] mt-5 mb-2">Answer</h3>
      <p className="text-sm leading-relaxed break-words">
        {renderTextWithCitations(dossier.answer, onOpenSource)}
      </p>

      <h3 className="font-display text-sm uppercase tracking-wider text-[#7a6a55] mt-5 mb-2">
        Key Findings
      </h3>
      {findings.length === 0 ? (
        <p className="text-sm text-[#7a6a55]">No entries</p>
      ) : (
        <ul className="list-disc pl-5 space-y-1">
          {findings.map((f, i) => (
            <li key={i} className="break-words">
              {renderTextWithCitations(f, onOpenSource)}
            </li>
          ))}
        </ul>
      )}

      <h3 className="font-display text-sm uppercase tracking-wider text-[#7a6a55] mt-5 mb-2">
        Detailed Notes
      </h3>
      {notes.length === 0 ? (
        <p className="text-sm text-[#7a6a55]">No entries</p>
      ) : (
        <ul className="list-disc pl-5 space-y-1">
          {notes.map((note, i) => (
            <li key={i} className="break-words">
              {renderTextWithCitations(note, onOpenSource)}
            </li>
          ))}
        </ul>
      )}

      <h3 className="font-display text-sm uppercase tracking-wider text-[#7a6a55] mt-5 mb-2">Sources</h3>
      {sources.length === 0 ? (
        <p className="text-sm text-[#7a6a55]">No entries</p>
      ) : (
        <ol className="space-y-3">
          {sources.map((s, i) => (
            <li key={s.n ?? i} className="flex items-baseline gap-2">
              <span className="w-6 h-6 rounded-full bg-[#d97706]/15 text-[#b45309] text-xs flex items-center justify-center shrink-0">
                {s.n}
              </span>
              <span className="min-w-0">
                <span className="font-medium break-words">{s.title}</span>
                <span className="block text-sm text-[#5a4f42] break-words">{s.excerpt}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
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
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full sm:w-96 max-w-full bg-[#171a21] text-gray-200 p-5 overflow-y-auto border-l border-white/10 max-sm:top-auto max-sm:h-auto max-sm:max-h-[70dvh] max-sm:rounded-t-2xl max-sm:border-l-0 max-sm:border-t">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase text-gray-500">Source {n}</span>
          <button
            type="button"
            aria-label="Close drawer"
            onClick={onClose}
            className="text-gray-500 hover:text-gray-200 transition cursor-pointer"
          >
            ✕
          </button>
        </div>
        <h3 className="font-display text-lg text-[#f7f4ec] break-words">
          {source && source.title ? source.title : 'Untitled source'}
        </h3>
        <p className="text-sm text-gray-400 whitespace-pre-line break-words mt-3">
          {source ? source.excerpt : ''}
        </p>
        {!source ? <p className="text-sm text-[#d97706] mt-3">Not found.</p> : null}
        {source && source.url ? (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-4 text-sm text-[#d97706] hover:underline"
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
  const [project, setProject] = useState(null)
  const [dossiers, setDossiers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  const [question, setQuestion] = useState('')
  const [researching, setResearching] = useState(false)
  const [askError, setAskError] = useState('')

  const [selectedDossier, setSelectedDossier] = useState(null)
  const [openSourceN, setOpenSourceN] = useState(null)

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

  async function handleResearch(e) {
    e.preventDefault()
    if (question.trim() === '' || researching) return
    setResearching(true)
    setAskError('')
    try {
      const created = await apiPost(`/api/projects/${id}/research`, { question: question.trim() })
      setDossiers((prev) => [created, ...prev])
      setQuestion('')
      setAskError('')
    } catch (err) {
      setAskError(err.message || 'Research failed')
    } finally {
      setResearching(false)
    }
  }

  const counterLong = question.length > 480

  return (
    <div className="min-h-dvh bg-[#0f1115] p-6 max-w-6xl mx-auto w-full">
      <Link to="/" className="text-sm text-gray-400 hover:text-gray-200 transition">
        ← All projects
      </Link>

      {loading ? (
        <div className="flex justify-center py-16">
          <p className="text-gray-400">Loading project...</p>
        </div>
      ) : error ? (
        <div className="rounded-xl bg-red-500/10 border border-red-500/40 text-red-300 px-4 py-3 flex items-center justify-between gap-3 flex-wrap mt-4">
          <span className="break-words">{error}</span>
          <button
            onClick={handleRetry}
            className="rounded-lg border border-red-500/40 px-3 py-1.5 text-sm text-red-200 hover:bg-red-500/20 transition shrink-0"
          >
            Retry
          </button>
        </div>
      ) : (
        <>
          <header className="mt-2 mb-6">
            <h1 className="font-display text-2xl text-[#f7f4ec] break-words">
              {project ? project.title : `Project ${id}`}
            </h1>
            {project && project.logline ? (
              <p className="text-gray-400 text-sm break-words mt-1">{project.logline}</p>
            ) : null}
            {project && project.genre ? (
              <div className="mt-2">
                <span className="rounded-full bg-[#d97706]/15 text-[#d97706] px-2 py-0.5 text-xs">
                  {project.genre}
                </span>
              </div>
            ) : null}
          </header>

          <section className="bg-[#171a21] border border-white/10 rounded-xl p-4">
            <form onSubmit={handleResearch}>
              <label htmlFor="research-question" className="block text-xs text-gray-400 mb-1">
                Ask a research question
              </label>
              <textarea
                id="research-question"
                maxLength={500}
                rows={3}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask about the world of your script..."
                className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 mb-3 focus:outline-none focus:border-[#d97706]/60 resize-y"
              />
              {askError ? (
                <div className="rounded-lg bg-red-500/10 border border-red-500/40 text-red-300 text-sm px-3 py-2 mb-3 break-words">
                  {askError}
                </div>
              ) : null}
              <div className="flex items-center justify-between gap-3 mt-2 flex-wrap">
                <span className={`text-xs ${counterLong ? 'text-[#d97706]' : 'text-gray-500'}`}>
                  {question.length}/500
                </span>
                <button
                  type="submit"
                  disabled={question.trim() === '' || researching}
                  className="inline-flex items-center gap-2 bg-[#d97706] text-black rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {researching ? (
                    <>
                      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-black/30 border-t-black align-[-2px]" />
                      Researching...
                    </>
                  ) : (
                    'Research'
                  )}
                </button>
              </div>
            </form>
          </section>

          <div className="space-y-3 mt-6">
            {dossiers.length === 0 ? (
              <p className="text-center text-gray-500 py-8">
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
            <div className="mt-3">
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
  )
}
