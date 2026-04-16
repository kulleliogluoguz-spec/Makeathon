import { useState, useEffect } from 'react';
import { authFetch, isAdmin } from '../lib/auth';

const ROLE_COLORS = {
  admin: { bg: '#fef2f2', color: '#dc2626' },
  supervisor: { bg: '#eff6ff', color: '#2563eb' },
  agent: { bg: '#f0fdf4', color: '#16a34a' },
};

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [showInvite, setShowInvite] = useState(false);
  const [form, setForm] = useState({ email: '', password: '', display_name: '', role: 'agent' });
  const [error, setError] = useState('');
  const [teams, setTeams] = useState([]);
  const [showTeamForm, setShowTeamForm] = useState(false);
  const [teamForm, setTeamForm] = useState({ name: '', description: '', color: '#3b82f6' });
  const [editingTeam, setEditingTeam] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [perfPeriod, setPerfPeriod] = useState('month');

  const loadTeams = async () => {
    try { const resp = await authFetch('/api/v1/teams/'); if (resp.ok) setTeams(await resp.json()); } catch (e) {}
  };
  const loadPerformance = async () => {
    try { const resp = await authFetch(`/api/v1/agent-performance/?period=${perfPeriod}`); if (resp.ok) setPerformance(await resp.json()); } catch (e) {}
  };
  useEffect(() => { loadTeams(); loadPerformance(); }, [perfPeriod]);

  const load = async () => {
    try {
      const resp = await authFetch('/api/v1/auth/users');
      if (resp.ok) setUsers(await resp.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); }, []);

  const invite = async () => {
    setError('');
    const resp = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (!resp.ok) {
      const data = await resp.json();
      setError(data.detail || 'Error');
      return;
    }
    setShowInvite(false);
    setForm({ email: '', password: '', display_name: '', role: 'agent' });
    load();
  };

  const updateRole = async (userId, role) => {
    await authFetch(`/api/v1/auth/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    });
    load();
  };

  const toggleActive = async (userId, isActive) => {
    await authFetch(`/api/v1/auth/users/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_active: !isActive }),
    });
    load();
  };

  const deleteUser = async (userId) => {
    if (!confirm('Delete this user?')) return;
    await authFetch(`/api/v1/auth/users/${userId}`, { method: 'DELETE' });
    load();
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Team</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Manage users and roles</p>
        </div>
        <button
          onClick={() => setShowInvite(true)}
          style={{ padding: '0.5rem 1rem', background: '#000', color: '#fff', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', cursor: 'pointer' }}
        >+ Add User</button>
      </div>

      {users.map((u) => (
        <div key={u.id} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem',
          marginBottom: '0.5rem', background: '#fff', opacity: u.is_active ? 1 : 0.5,
        }}>
          <div>
            <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{u.display_name}</div>
            <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>{u.email}</div>
            <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '2px' }}>
              Last login: {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Never'}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <select
              value={u.role}
              onChange={(e) => updateRole(u.id, e.target.value)}
              style={{
                padding: '4px 10px', fontSize: '0.75rem', borderRadius: '9999px',
                border: '1px solid #e5e7eb', outline: 'none',
                background: ROLE_COLORS[u.role]?.bg || '#f3f4f6',
                color: ROLE_COLORS[u.role]?.color || '#374151',
                fontWeight: 600,
              }}
            >
              <option value="admin">Admin</option>
              <option value="supervisor">Supervisor</option>
              <option value="agent">Agent</option>
            </select>
            <button
              onClick={() => toggleActive(u.id, u.is_active)}
              style={{
                padding: '4px 10px', fontSize: '0.7rem', borderRadius: '9999px',
                background: u.is_active ? '#f0fdf4' : '#fef2f2',
                color: u.is_active ? '#16a34a' : '#dc2626',
                border: '1px solid #e5e7eb', cursor: 'pointer',
              }}
            >{u.is_active ? 'Active' : 'Inactive'}</button>
            <button
              onClick={() => deleteUser(u.id)}
              style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}
            >Delete</button>
          </div>
        </div>
      ))}

      {showInvite && (
        <div style={{ marginTop: '1rem', padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#f9fafb' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Add New User</h3>
          {error && <div style={{ color: '#dc2626', fontSize: '0.8rem', marginBottom: '0.5rem' }}>{error}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <input type="text" placeholder="Name" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
            <input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
            <input type="password" placeholder="Password (min 6)" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}>
              <option value="agent">Agent</option>
              <option value="supervisor">Supervisor</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={invite} disabled={!form.email || !form.password}
              style={{ padding: '8px 20px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer', opacity: (!form.email || !form.password) ? 0.4 : 1 }}>
              Create User</button>
            <button onClick={() => { setShowInvite(false); setError(''); }}
              style={{ padding: '8px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {/* Teams */}
      <div style={{ marginTop: '2.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Teams</h2>
          <button onClick={() => { setTeamForm({ name: '', description: '', color: '#3b82f6' }); setEditingTeam(null); setShowTeamForm(true); }}
            style={{ padding: '6px 14px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>+ Create Team</button>
        </div>
        {teams.map((team) => (
          <div key={team.id} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', marginBottom: '0.75rem', background: '#fff' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: team.color }} />
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{team.name}</span>
                <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>{(team.member_ids || []).length} members</span>
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button onClick={() => { setTeamForm({ name: team.name, description: team.description, color: team.color }); setEditingTeam(team.id); setShowTeamForm(true); }}
                  style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>Edit</button>
                <button onClick={async () => { if (confirm('Delete?')) { await authFetch(`/api/v1/teams/${team.id}`, { method: 'DELETE' }); loadTeams(); } }}
                  style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
              </div>
            </div>
            {team.description && <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.5rem' }}>{team.description}</div>}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {(team.member_ids || []).map((uid) => {
                const u = users.find(x => x.id === uid);
                return u ? (
                  <span key={uid} style={{ fontSize: '0.75rem', padding: '3px 10px', background: '#f3f4f6', borderRadius: '9999px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {u.display_name}
                    <button onClick={async () => { await authFetch(`/api/v1/teams/${team.id}/members/${uid}`, { method: 'DELETE' }); loadTeams(); }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: '0.8rem' }}>x</button>
                  </span>
                ) : null;
              })}
              <select onChange={async (e) => { if (!e.target.value) return; await authFetch(`/api/v1/teams/${team.id}/members`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: e.target.value }) }); e.target.value = ''; loadTeams(); }}
                style={{ fontSize: '0.75rem', padding: '3px 8px', border: '1px dashed #e5e7eb', borderRadius: '9999px', outline: 'none', color: '#9ca3af' }}>
                <option value="">+ Add member</option>
                {users.filter(u => !(team.member_ids || []).includes(u.id)).map(u => (
                  <option key={u.id} value={u.id}>{u.display_name}</option>
                ))}
              </select>
            </div>
          </div>
        ))}
        {showTeamForm && (
          <div style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#f9fafb', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <input type="text" placeholder="Team name" value={teamForm.name} onChange={(e) => setTeamForm({ ...teamForm, name: e.target.value })}
                style={{ flex: 1, padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }} />
              <input type="color" value={teamForm.color} onChange={(e) => setTeamForm({ ...teamForm, color: e.target.value })}
                style={{ width: '40px', height: '36px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', cursor: 'pointer' }} />
            </div>
            <input type="text" placeholder="Description (optional)" value={teamForm.description} onChange={(e) => setTeamForm({ ...teamForm, description: e.target.value })}
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', marginBottom: '0.75rem', boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={async () => { const method = editingTeam ? 'PATCH' : 'POST'; const url = editingTeam ? `/api/v1/teams/${editingTeam}` : '/api/v1/teams/'; await authFetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(teamForm) }); setShowTeamForm(false); loadTeams(); }}
                style={{ padding: '6px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>{editingTeam ? 'Save' : 'Create'}</button>
              <button onClick={() => setShowTeamForm(false)}
                style={{ padding: '6px 16px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>Cancel</button>
            </div>
          </div>
        )}
      </div>

      {/* Agent Performance */}
      {performance && (
        <div style={{ marginTop: '2.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Agent Performance</h2>
            <div style={{ display: 'flex', gap: '4px' }}>
              {['today', 'week', 'month'].map(p => (
                <button key={p} onClick={() => setPerfPeriod(p)}
                  style={{ padding: '4px 12px', fontSize: '0.75rem', borderRadius: '9999px', background: perfPeriod === p ? '#000' : '#fff', color: perfPeriod === p ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}</button>
              ))}
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ textAlign: 'left', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Agent</th>
                  <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Conversations</th>
                  <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Messages</th>
                  <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Resolved</th>
                  <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>Avg Intent</th>
                  <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>CSAT</th>
                  <th style={{ textAlign: 'center', padding: '8px', color: '#6b7280', fontWeight: 600 }}>High Intent</th>
                </tr>
              </thead>
              <tbody>
                {performance.agents.map((a) => (
                  <tr key={a.user_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px' }}>
                      <div style={{ fontWeight: 500 }}>{a.display_name}</div>
                      <div style={{ fontSize: '0.7rem', color: '#9ca3af' }}>{a.role}</div>
                    </td>
                    <td style={{ textAlign: 'center', padding: '8px', fontWeight: 600 }}>{a.total_conversations}</td>
                    <td style={{ textAlign: 'center', padding: '8px' }}>{a.total_messages}</td>
                    <td style={{ textAlign: 'center', padding: '8px' }}><span style={{ color: '#10b981', fontWeight: 600 }}>{a.resolved_conversations}</span></td>
                    <td style={{ textAlign: 'center', padding: '8px' }}>{a.avg_intent_score}</td>
                    <td style={{ textAlign: 'center', padding: '8px' }}>{a.avg_csat > 0 ? <span style={{ color: a.avg_csat >= 4 ? '#10b981' : '#f59e0b', fontWeight: 600 }}>{a.avg_csat} ({a.csat_count})</span> : '-'}</td>
                    <td style={{ textAlign: 'center', padding: '8px' }}><span style={{ color: '#3b82f6', fontWeight: 600 }}>{a.high_intent_count}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
