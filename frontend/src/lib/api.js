const BASE = '/api/v1'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

// Personas
export const listPersonas = () => request('/personas/')
export const getPersona = (id) => request(`/personas/${id}`)
export const createPersona = (data) => request('/personas/', { method: 'POST', body: JSON.stringify(data) })
export const updatePersona = (id, data) => request(`/personas/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
export const deletePersona = (id) => request(`/personas/${id}`, { method: 'DELETE' })
export const generatePrompt = (id) => request(`/personas/${id}/generate-prompt`, { method: 'POST' })
export const previewPrompt = (id) => request(`/personas/${id}/preview-prompt`, { method: 'POST' })
export const duplicatePersona = (id) => request(`/personas/${id}/duplicate`, { method: 'POST' })

// Agents
export const listAgents = () => request('/agents/')
export const getAgent = (id) => request(`/agents/${id}`)
export const createAgent = (data) => request('/agents/', { method: 'POST', body: JSON.stringify(data) })
export const updateAgent = (id, data) => request(`/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
export const deleteAgent = (id) => request(`/agents/${id}`, { method: 'DELETE' })
export const assignPersona = (id, personaId) => request(`/agents/${id}/assign-persona`, { method: 'POST', body: JSON.stringify({ persona_id: personaId }) })
export const getAgentFullConfig = (id) => request(`/agents/${id}/full-config`)
