import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGet, apiPost, formatDate } from '../api.js'

function DossierCard({ dossier }) {
  const sourceCount = Array.isArray(dossier.sources) ? dossier.sources.length : 0
  return (
    <button
      type="button"
      className="w-full text-left bg-[#171a21] rounded-xl p-4 border border-white/10 hover:border-[#d97706]/60 transition break-words cursor-pointer"
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
              dossiers.map((d) => <DossierCard key={d.dossier_id} dossier={d} />)
            )}
          </div>
        </>
      )}
    </div>
  )
}
