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
    </div>
  );
}
