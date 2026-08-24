import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiGet, apiPost } from '../api.js'

function ProjectCard({ project }) {
  const navigate = useNavigate()
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/project/${project.id}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          navigate(`/project/${project.id}`)
        }
      }}
      className="bg-surface border border-line rounded-2xl p-5 transition duration-200 ease-out break-words cursor-pointer hover:-translate-y-0.5 hover:border-neutral-200 hover:shadow-[0_16px_40px_-24px_rgba(23,23,23,0.25)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
    >
      <h2 className="font-display text-lg font-semibold tracking-tight text-ink break-words">
        {project.title}
      </h2>
      {project.logline ? (
        <p className="text-sm text-muted line-clamp-3 break-words mt-1.5">{project.logline}</p>
      ) : null}
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        {project.genre ? (
          <span className="rounded-full bg-accent/20 text-accent-deep px-2.5 py-0.5 text-xs font-medium">
            {project.genre}
          </span>
        ) : null}
        <span className="rounded-full bg-accent/20 text-accent-deep px-2.5 py-0.5 text-xs font-medium">
          {project.dossier_count} dossiers
        </span>
      </div>
    </div>
  )
}

function NewProjectModal({ onClose }) {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [logline, setLogline] = useState('')
  const [genre, setGenre] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim() || submitting) return
    setSubmitting(true)
    setError('')
    try {
      const created = await apiPost('/api/projects', {
        title: title.trim(),
        logline: logline.trim(),
        genre: genre.trim(),
      })
      navigate(`/project/${created.id}`)
    } catch (err) {
      setError(err.message || 'Failed to create project')
      setSubmitting(false)
    }
  }

  function handleCancel() {
    setError('')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-[2px] flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="bg-surface rounded-3xl p-6 w-full max-w-md border border-line shadow-2xl"
      >
        <h2 className="font-display text-xl font-semibold tracking-tight text-ink mb-5">
          New Project
        </h2>

        <label htmlFor="np-title" className="block text-xs font-medium text-muted mb-1.5">
          Title
        </label>
        <input
          id="np-title"
          type="text"
          required
          maxLength={120}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full bg-bg border border-line rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder:text-faint mb-4 focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/20"
        />

        <label htmlFor="np-logline" className="block text-xs font-medium text-muted mb-1.5">
          Logline
        </label>
        <textarea
          id="np-logline"
          maxLength={500}
          rows={3}
          value={logline}
          onChange={(e) => setLogline(e.target.value)}
          className="w-full bg-bg border border-line rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder:text-faint mb-4 focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/20 resize-y"
        />

        <label htmlFor="np-genre" className="block text-xs font-medium text-muted mb-1.5">
          Genre
        </label>
        <input
          id="np-genre"
          type="text"
          maxLength={40}
          value={genre}
          onChange={(e) => setGenre(e.target.value)}
          className="w-full bg-bg border border-line rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder:text-faint mb-5 focus:outline-none focus:border-accent focus:ring-4 focus:ring-accent/20"
        />

        {error ? (
          <div className="rounded-xl bg-red-50 border border-red-200 text-red-600 text-sm px-3.5 py-2.5 mb-5 break-words">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={handleCancel}
            disabled={submitting}
            className="rounded-full px-4 py-2 text-sm font-medium text-muted hover:text-ink transition duration-200 ease-out disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim() || submitting}
            className="bg-neutral-900 text-white rounded-full px-4 py-2 text-sm font-semibold transition duration-200 ease-out hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Creating...' : 'Create'}
          </button>
        </div>
      </form>
    </div>
  )
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  const [askDraft, setAskDraft] = useState('')
  const [asking, setAsking] = useState(false)
  const [askError, setAskError] = useState('')

  useEffect(() => {
    let ignore = false
    ;(async () => {
      try {
        const data = await apiGet('/api/projects')
        if (!ignore) {
          setProjects(data)
          setError('')
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || 'Failed to load projects')
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
  }, [reloadKey])

  function handleRetry() {
    setLoading(true)
    setReloadKey((k) => k + 1)
  }

  // Home ask-box flow: create a project named from the question, then jump
  // straight into it with the question handed off via router state — the
  // project page runs the first research pass itself (see ProjectPage).
  async function handleHomeAsk(e) {
    e.preventDefault()
    const q = askDraft.trim()
    if (!q || asking) return
    setAsking(true)
    setAskError('')
    try {
      const created = await apiPost('/api/projects', {
        title: q.slice(0, 40),
        logline: '',
        genre: '',
      })
      navigate(`/project/${created.id}`, { state: { pendingQuestion: q } })
    } catch (err) {
      setAskError(err.message || 'Failed to start research')
      setAsking(false)
    }
  }

  return (
    <div className="min-h-dvh bg-bg">
      <div className="max-w-6xl mx-auto w-full px-6 py-12 sm:py-16">
        <section className="max-w-2xl mx-auto text-center">
          <span className="inline-flex items-center rounded-full border border-line bg-surface px-3 py-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted">
            Verisim Research
          </span>
          <h1 className="font-display mt-5 text-4xl md:text-5xl font-bold tracking-tight text-ink">
            Your script{'’'}s world,
            <br />
            researched.
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted max-w-xl mx-auto">
            Verisim turns scattered worldbuilding into cited dossiers, so screenwriters can write
            with confidence.
          </p>
        </section>

        <form onSubmit={handleHomeAsk} className="mt-8 max-w-2xl mx-auto">
          <div className="bg-surface border border-line rounded-full p-4 shadow-[0_1px_2px_rgba(23,23,23,0.04)] transition duration-200 ease-out focus-within:border-accent focus-within:ring-4 focus-within:ring-accent/20">
            <label htmlFor="home-question" className="sr-only">
              Ask a research question
            </label>
            <textarea
              id="home-question"
              rows={2}
              maxLength={500}
              value={askDraft}
              onChange={(e) => setAskDraft(e.target.value)}
              placeholder="e.g. What does a 1920s Paris police archive smell like?"
              className="w-full resize-y bg-transparent px-2 py-1.5 text-sm text-ink placeholder:text-faint focus:outline-none"
            />
            <div className="flex items-center justify-between gap-3 mt-2 flex-wrap">
              <span className={`text-xs ${askDraft.length > 480 ? 'text-accent-deep' : 'text-faint'}`}>
                {askDraft.length}/500
              </span>
              <button
                type="submit"
                disabled={askDraft.trim() === '' || asking}
                className="inline-flex items-center gap-2 bg-neutral-900 text-white rounded-full px-5 py-2 text-sm font-semibold transition duration-200 ease-out hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {asking ? (
                  <>
                    <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white align-[-2px]" />
                    Researching...
                  </>
                ) : (
                  'Research'
                )}
              </button>
            </div>
          </div>
          {askError ? (
            <div className="mt-3 rounded-2xl bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-3 break-words">
              {askError}
            </div>
          ) : null}
        </form>

        <div className="flex items-center justify-between mt-16 mb-6 flex-wrap gap-3">
          <h2 className="font-display text-xl font-semibold tracking-tight text-ink">
            Your projects
          </h2>
          <button
            onClick={() => setModalOpen(true)}
            className="border border-line bg-surface text-ink rounded-full px-4 py-2 text-sm font-medium transition duration-200 ease-out hover:border-neutral-300 hover:shadow-sm"
          >
            + New Project
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <p className="text-sm text-faint">Loading projects...</p>
          </div>
        ) : error ? (
          <div className="rounded-2xl bg-red-50 border border-red-200 text-red-600 px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
            <span className="break-words">{error}</span>
            <button
              onClick={handleRetry}
              className="rounded-full border border-red-200 bg-white px-4 py-1.5 text-sm font-medium text-red-600 hover:bg-red-100 transition duration-200 ease-out shrink-0"
            >
              Retry
            </button>
          </div>
        ) : projects && projects.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {projects.map((p) => (
              <ProjectCard key={p.id} project={p} />
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-dashed border-line px-6 py-14 text-center">
            <p className="text-sm text-muted">No projects yet.</p>
            <p className="text-sm text-faint mt-1">
              Ask your first question above and a project will start itself.
            </p>
          </div>
        )}

        {modalOpen ? <NewProjectModal onClose={() => setModalOpen(false)} /> : null}
      </div>
    </div>
  )
}
