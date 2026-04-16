import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { UserCircle, Bot, MessageSquare } from 'lucide-react'
import PersonaListPage from './pages/PersonaListPage'
import PersonaEditorPage from './pages/PersonaEditorPage'
import AgentListPage from './pages/AgentListPage'
import ConversationsPage from './pages/ConversationsPage'

function TopNav() {
  return (
    <header className="h-14 border-b border-gray-200 bg-white px-6 flex items-center justify-between shrink-0">
      <NavLink to="/personas" className="flex items-center gap-2 text-gray-900 font-semibold text-lg">
        <UserCircle size={22} strokeWidth={1.5} />
        Persona Builder
      </NavLink>
      <nav className="flex items-center gap-1">
        <NavLink to="/personas" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <UserCircle size={16} strokeWidth={1.5} /> Personas
        </NavLink>
        <NavLink to="/agents" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <Bot size={16} strokeWidth={1.5} /> Agents
        </NavLink>
        <NavLink to="/conversations" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <MessageSquare size={16} strokeWidth={1.5} /> Conversations
        </NavLink>
      </nav>
      <div className="w-8 h-8 rounded-full bg-gray-200" />
    </header>
  )
}

export default function App() {
  return (
    <div className="h-screen flex flex-col bg-white">
      <TopNav />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/personas" replace />} />
          <Route path="/personas" element={<PersonaListPage />} />
          <Route path="/personas/:id" element={<PersonaEditorPage />} />
          <Route path="/agents" element={<AgentListPage />} />
          <Route path="/conversations" element={<ConversationsPage />} />
        </Routes>
      </main>
    </div>
  )
}
