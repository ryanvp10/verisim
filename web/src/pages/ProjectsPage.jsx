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
      className="bg-[#171a21] rounded-xl p-4 border border-white/10 hover:border-[#d97706]/60 transition break-words cursor-pointer text-left"
    >
      <h2 className="font-display text-lg text-[#f7f4ec] break-words">{project.title}</h2>
      {project.logline ? (
        <p className="text-sm text-gray-400 line-clamp-3 break-words mt-1">{project.logline}</p>
      ) : null}
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        {project.genre ? (
          <span className="rounded-full bg-[#d97706]/15 text-[#d97706] px-2 py-0.5 text-xs">
            {project.genre}
          </span>
        ) : null}
        <span className="text-xs text-gray-500">{project.dossier_count} dossiers</span>
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
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4">
      <form
        onSubmit={handleSubmit}
        className="bg-[#171a21] rounded-xl p-5 w-full max-w-md border border-white/10"
      >
        <h2 className="font-display text-xl text-[#f7f4ec] mb-4">New Project</h2>

        <label htmlFor="np-title" className="block text-xs text-gray-400 mb-1">
          Title
        </label>
        <input
          id="np-title"
          type="text"
          required
          maxLength={120}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 mb-3 focus:outline-none focus:border-[#d97706]/60"
        />

        <label htmlFor="np-logline" className="block text-xs text-gray-400 mb-1">
          Logline
        </label>
        <textarea
          id="np-logline"
          maxLength={500}
          rows={3}
          value={logline}
          onChange={(e) => setLogline(e.target.value)}
          className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 mb-3 focus:outline-none focus:border-[#d97706]/60 resize-y"
        />

        <label htmlFor="np-genre" className="block text-xs text-gray-400 mb-1">
          Genre
        </label>
        <input
          id="np-genre"
          type="text"
          maxLength={40}
          value={genre}
          onChange={(e) => setGenre(e.target.value)}
          className="w-full bg-black/30 border border-white/10 rounded-lg px-3 py-2 text-sm text-gray-200 mb-4 focus:outline-none focus:border-[#d97706]/60"
        />

        {error ? (
          <div className="rounded-lg bg-red-500/10 border border-red-500/40 text-red-300 text-sm px-3 py-2 mb-4 break-words">
            {error}
          </div>
        ) : null}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={handleCancel}
            disabled={submitting}
            className="rounded-lg px-3 py-2 text-sm text-gray-300 hover:text-gray-100 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim() || submitting}
            className="bg-[#d97706] text-black rounded-lg px-3 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
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

  return (
    <div className="min-h-dvh bg-[#0f1115] p-6 max-w-6xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="font-display text-2xl text-[#f7f4ec]">Projects</h1>
        <button
          onClick={() => setModalOpen(true)}
          className="bg-[#d97706] text-black rounded-lg px-3 py-2 text-sm font-medium"
        >
          + New Project
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <p className="text-gray-400">Loading projects...</p>
        </div>
      ) : error ? (
        <div className="rounded-xl bg-red-500/10 border border-red-500/40 text-red-300 px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <span className="break-words">{error}</span>
          <button
            onClick={handleRetry}
            className="rounded-lg border border-red-500/40 px-3 py-1.5 text-sm text-red-200 hover:bg-red-500/20 transition shrink-0"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {(projects || []).map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}

      {modalOpen ? <NewProjectModal onClose={() => setModalOpen(false)} /> : null}
    </div>
  )
}
