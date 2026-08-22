import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import ProjectsPage from './pages/ProjectsPage.jsx'

function ProjectPagePlaceholder() {
  const { id } = useParams()
  return (
    <div className="min-h-dvh bg-[#0f1115] p-6">
      <h1 className="font-display text-2xl text-[#f7f4ec]">Project {id}</h1>
      <p className="text-gray-400 mt-2">Project page coming soon.</p>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/project/:id" element={<ProjectPagePlaceholder />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
