import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import { UserCircle, Bot, MessageSquare, Users, Settings, BarChart3 } from 'lucide-react'
import { t } from './lib/i18n'
import { isLoggedIn, getUser, clearAuth, isAdmin } from './lib/auth'
import LoginPage from './pages/LoginPage'
import UsersPage from './pages/UsersPage'
import PersonaListPage from './pages/PersonaListPage'
import PersonaEditorPage from './pages/PersonaEditorPage'
import AgentListPage from './pages/AgentListPage'
import ConversationsPage from './pages/ConversationsPage'
import CustomersPage from './pages/CustomersPage'
import SettingsPage from './pages/SettingsPage'
import AnalyticsPage from './pages/AnalyticsPage'

function TopNav() {
  return (
    <header className="h-14 border-b border-gray-200 bg-white px-6 flex items-center justify-between shrink-0">
      <NavLink to="/personas" className="flex items-center gap-2 text-gray-900 font-semibold text-lg">
        <UserCircle size={22} strokeWidth={1.5} />
        Persona Builder
      </NavLink>
      <nav className="flex items-center gap-1">
        <NavLink to="/personas" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <UserCircle size={16} strokeWidth={1.5} /> {t('nav_personas')}
        </NavLink>
        <NavLink to="/agents" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <Bot size={16} strokeWidth={1.5} /> {t('nav_agents')}
        </NavLink>
        <NavLink to="/conversations" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <MessageSquare size={16} strokeWidth={1.5} /> {t('nav_conversations')}
        </NavLink>
        <NavLink to="/customers" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <Users size={16} strokeWidth={1.5} /> {t('nav_customers')}
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <BarChart3 size={16} strokeWidth={1.5} /> {t('nav_analytics')}
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
          <Settings size={16} strokeWidth={1.5} /> {t('nav_settings')}
        </NavLink>
        {isAdmin() && (
          <NavLink to="/users" className={({ isActive }) => `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${isActive ? 'bg-gray-900 text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}>
            {t('nav_team')}
          </NavLink>
        )}
      </nav>
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-500">{getUser()?.display_name} ({getUser()?.role})</span>
        <button onClick={() => { clearAuth(); window.location.href = '/login'; }} className="px-3 py-1 text-xs border border-gray-200 rounded-full hover:bg-gray-50">{t('auth_logout')}</button>
      </div>
    </header>
  )
}

export default function App() {
  if (!isLoggedIn() && window.location.pathname !== '/login') {
    window.location.href = '/login';
    return null;
  }

  if (window.location.pathname === '/login') {
    return <Routes><Route path="/login" element={<LoginPage />} /></Routes>;
  }

  return (
    <div className="h-screen flex flex-col bg-white">
      <TopNav />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/personas" replace />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/personas" element={<PersonaListPage />} />
          <Route path="/personas/:id" element={<PersonaEditorPage />} />
          <Route path="/agents" element={<AgentListPage />} />
          <Route path="/conversations" element={<ConversationsPage />} />
          <Route path="/customers" element={<CustomersPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
