import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, UserCircle } from 'lucide-react'
import Modal from '../components/Modal'
import { listPersonas, createPersona } from '../lib/api'

const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-400'

function TraitBar({ label, value }) {
  const pct = Math.max(0, Math.min(100, value))
  const color = pct <= 33 ? 'bg-blue-400' : pct <= 66 ? 'bg-yellow-400' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-16 truncate">{label}</span>
      <div className="flex-1 h-1.5 rounded-full bg-gray-200">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-gray-500 w-5 text-right">{value}</span>
    </div>
  )
}

export default function PersonaListPage() {
  const navigate = useNavigate()
  const [personas, setPersonas] = useState([])
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')

  useEffect(() => { listPersonas().then(setPersonas) }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    const p = await createPersona({ name: newName.trim() })
    setShowCreate(false)
    setNewName('')
    navigate(`/personas/${p.id}`)
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-900">Personas</h1>
        <button onClick={() => setShowCreate(true)} className="px-4 py-1.5 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800">
          + Create Persona
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {personas.map((p) => (
          <button
            key={p.id}
            onClick={() => navigate(`/personas/${p.id}`)}
            className="text-left p-5 rounded-xl border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all bg-white"
          >
            <div className="flex items-center gap-3 mb-3">
              {p.avatar_url ? (
                <img src={p.avatar_url} className="w-10 h-10 rounded-full object-cover" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-500 text-sm font-bold">
                  {(p.display_name || p.name || '?')[0].toUpperCase()}
                </div>
              )}
              <div>
                <h3 className="text-sm font-semibold text-gray-900">{p.display_name || p.name}</h3>
                <p className="text-xs text-gray-500">{p.role_title || 'No role'}{p.company_name ? ` at ${p.company_name}` : ''}</p>
              </div>
            </div>
            <div className="space-y-1">
              <TraitBar label="Friendly" value={p.friendliness} />
              <TraitBar label="Formal" value={p.formality} />
              <TraitBar label="Empathy" value={p.empathy} />
            </div>
          </button>
        ))}
        <button
          onClick={() => setShowCreate(true)}
          className="p-5 rounded-xl border-2 border-dashed border-gray-300 text-gray-400 hover:border-gray-400 hover:text-gray-600 transition-colors flex flex-col items-center justify-center gap-2 min-h-[160px]"
        >
          <Plus size={24} strokeWidth={1.5} />
          <span className="text-sm font-medium">Create Persona</span>
        </button>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Persona">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Persona Name</label>
            <input value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleCreate()} placeholder="e.g. Friendly Sales Rep" className={inputCls} autoFocus />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
            <button onClick={handleCreate} className="px-4 py-2 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800">Create</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
