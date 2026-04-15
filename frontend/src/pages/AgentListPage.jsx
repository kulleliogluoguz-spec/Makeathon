import { useState, useEffect } from 'react'
import { Bot, Plus, Trash2, Edit3 } from 'lucide-react'
import Modal from '../components/Modal'
import { listAgents, createAgent, updateAgent, deleteAgent, listPersonas } from '../lib/api'

const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-400'

const statusColors = {
  active: 'bg-green-50 text-green-700',
  draft: 'bg-gray-100 text-gray-600',
  paused: 'bg-yellow-50 text-yellow-700',
}

export default function AgentListPage() {
  const [agents, setAgents] = useState([])
  const [personas, setPersonas] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({
    name: '', description: '', persona_id: '', status: 'draft',
    llm_provider: 'openai', llm_model: 'gpt-4o', llm_temperature: 0.7,
    first_message: '',
  })

  const load = () => { listAgents().then(setAgents); listPersonas().then(setPersonas) }
  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditing(null)
    setForm({ name: '', description: '', persona_id: '', status: 'draft', llm_provider: 'openai', llm_model: 'gpt-4o', llm_temperature: 0.7, first_message: '' })
    setShowModal(true)
  }

  const openEdit = (agent) => {
    setEditing(agent)
    setForm({
      name: agent.name, description: agent.description || '', persona_id: agent.persona_id || '',
      status: agent.status, llm_provider: agent.llm_provider, llm_model: agent.llm_model,
      llm_temperature: agent.llm_temperature, first_message: agent.first_message || '',
    })
    setShowModal(true)
  }

  const handleSave = async () => {
    const data = { ...form, persona_id: form.persona_id || null }
    if (editing) {
      await updateAgent(editing.id, data)
    } else {
      await createAgent(data)
    }
    setShowModal(false)
    load()
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this agent?')) return
    await deleteAgent(id)
    load()
  }

  const personaName = (pid) => {
    const p = personas.find((p) => p.id === pid)
    return p ? (p.display_name || p.name) : 'None'
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-900">Agents</h1>
        <button onClick={openCreate} className="flex items-center gap-1.5 px-4 py-1.5 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800">
          <Plus size={14} strokeWidth={1.5} /> Create Agent
        </button>
      </div>

      <div className="space-y-3">
        {agents.length === 0 ? (
          <div className="text-center py-12 text-gray-400 text-sm">No agents yet. Create one to get started.</div>
        ) : (
          agents.map((agent) => (
            <div key={agent.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                  <Bot size={18} strokeWidth={1.5} className="text-gray-500" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-gray-900">{agent.name}</div>
                  <div className="text-xs text-gray-500">
                    Persona: {personaName(agent.persona_id)} · {agent.llm_model}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[agent.status] || statusColors.draft}`}>
                  {agent.status}
                </span>
                <button onClick={() => openEdit(agent)} className="text-gray-400 hover:text-gray-600"><Edit3 size={16} strokeWidth={1.5} /></button>
                <button onClick={() => handleDelete(agent.id)} className="text-gray-400 hover:text-red-500"><Trash2 size={16} strokeWidth={1.5} /></button>
              </div>
            </div>
          ))
        )}
      </div>

      <Modal open={showModal} onClose={() => setShowModal(false)} title={editing ? 'Edit Agent' : 'Create Agent'}>
        <div className="space-y-4">
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputCls} /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Description</label><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} className={inputCls} /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Persona</label>
            <select value={form.persona_id} onChange={(e) => setForm({ ...form, persona_id: e.target.value })} className={inputCls}>
              <option value="">None</option>
              {personas.map((p) => <option key={p.id} value={p.id}>{p.display_name || p.name}</option>)}
            </select>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className={inputCls}>
              <option value="draft">Draft</option><option value="active">Active</option><option value="paused">Paused</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">LLM Provider</label>
              <select value={form.llm_provider} onChange={(e) => setForm({ ...form, llm_provider: e.target.value })} className={inputCls}>
                <option value="openai">OpenAI</option><option value="anthropic">Anthropic</option><option value="ollama">Ollama</option>
              </select>
            </div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Model</label><input value={form.llm_model} onChange={(e) => setForm({ ...form, llm_model: e.target.value })} className={inputCls} /></div>
          </div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label><input type="number" min={0} max={1} step={0.1} value={form.llm_temperature} onChange={(e) => setForm({ ...form, llm_temperature: Number(e.target.value) })} className={inputCls + ' w-24'} /></div>
          <div><label className="block text-sm font-medium text-gray-700 mb-1">First Message</label><textarea value={form.first_message} onChange={(e) => setForm({ ...form, first_message: e.target.value })} rows={2} className={inputCls} /></div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm text-gray-600">Cancel</button>
            <button onClick={handleSave} className="px-4 py-2 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800">{editing ? 'Update' : 'Create'}</button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
