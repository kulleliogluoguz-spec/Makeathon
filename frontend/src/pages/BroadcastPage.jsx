import { useState, useEffect } from 'react';

export default function BroadcastPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', subject: '', message: '', channels: [], recipient_filter: {} });
  const [sending, setSending] = useState(null);
  const [preview, setPreview] = useState(null);

  const loadCampaigns = () => {
    fetch('/api/v1/broadcasts/').then(r => r.json()).then(setCampaigns).catch(() => {});
  };

  useEffect(() => { loadCampaigns(); }, []);

  const createCampaign = async () => {
    const resp = await fetch('/api/v1/broadcasts/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    if (resp.ok) {
      setShowForm(false);
      setForm({ name: '', subject: '', message: '', channels: [], recipient_filter: {} });
      loadCampaigns();
    }
  };

  const sendCampaign = async (id) => {
    setSending(id);
    await fetch(`/api/v1/broadcasts/${id}/send`, { method: 'POST' });
    setSending(null);
    loadCampaigns();
  };

  const deleteCampaign = async (id) => {
    await fetch(`/api/v1/broadcasts/${id}`, { method: 'DELETE' });
    loadCampaigns();
  };

  const previewRecipients = async (id) => {
    const resp = await fetch(`/api/v1/broadcasts/${id}/preview`);
    const data = await resp.json();
    setPreview(data);
  };

  const toggleChannel = (ch) => {
    setForm(f => ({
      ...f,
      channels: f.channels.includes(ch) ? f.channels.filter(c => c !== ch) : [...f.channels, ch],
    }));
  };

  const statusBadge = (status) => {
    const colors = { draft: '#6b7280', sending: '#f59e0b', sent: '#10b981' };
    return (
      <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px', background: `${colors[status] || '#6b7280'}20`, color: colors[status] || '#6b7280', fontWeight: 600, textTransform: 'uppercase' }}>
        {status}
      </span>
    );
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Broadcasts</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Send messages to multiple customers at once</p>
        </div>
        <button onClick={() => setShowForm(true)} style={{ padding: '8px 20px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer' }}>
          + New Campaign
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Create Campaign</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <input
              placeholder="Campaign name"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '0.9rem' }}
            />
            <input
              placeholder="Email subject (for email channel)"
              value={form.subject}
              onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '0.9rem' }}
            />
            <textarea
              placeholder="Message content..."
              value={form.message}
              onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
              rows={4}
              style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '0.9rem', resize: 'vertical' }}
            />
            <div>
              <p style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.5rem' }}>Channels:</p>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {['email', 'telegram'].map(ch => (
                  <button key={ch} onClick={() => toggleChannel(ch)} style={{
                    padding: '6px 14px', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer',
                    background: form.channels.includes(ch) ? '#000' : '#fff',
                    color: form.channels.includes(ch) ? '#fff' : '#374151',
                    border: '1px solid #e5e7eb',
                  }}>
                    {ch === 'email' ? '📧 Email' : '✈️ Telegram'}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.5rem' }}>Filter by source (optional):</p>
              <select
                value={form.recipient_filter.source || ''}
                onChange={e => setForm(f => ({ ...f, recipient_filter: { ...f.recipient_filter, source: e.target.value || undefined } }))}
                style={{ padding: '6px 12px', border: '1px solid #e5e7eb', borderRadius: '8px', fontSize: '0.85rem' }}
              >
                <option value="">All customers</option>
                <option value="instagram">Instagram</option>
                <option value="telegram">Telegram</option>
                <option value="messenger">Messenger</option>
                <option value="livechat">Live Chat</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              <button onClick={createCampaign} style={{ padding: '8px 20px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer' }}>
                Create Campaign
              </button>
              <button onClick={() => setShowForm(false)} style={{ padding: '8px 20px', background: '#fff', color: '#374151', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer' }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {preview && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Recipient Preview</h3>
            <button onClick={() => setPreview(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}>×</button>
          </div>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ background: '#f3f4f6', padding: '8px 14px', borderRadius: '8px', fontSize: '0.85rem' }}>
              Total: <strong>{preview.total_customers}</strong>
            </div>
            <div style={{ background: '#f3f4f6', padding: '8px 14px', borderRadius: '8px', fontSize: '0.85rem' }}>
              Email: <strong>{preview.email_recipients}</strong>
            </div>
            <div style={{ background: '#f3f4f6', padding: '8px 14px', borderRadius: '8px', fontSize: '0.85rem' }}>
              Telegram: <strong>{preview.telegram_recipients}</strong>
            </div>
          </div>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {preview.customers?.map(c => (
              <div key={c.id} style={{ fontSize: '0.8rem', padding: '4px 0', borderBottom: '1px solid #f3f4f6', display: 'flex', justifyContent: 'space-between' }}>
                <span>{c.display_name}</span>
                <span style={{ color: '#6b7280' }}>{c.email || c.source}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Campaign List */}
      {campaigns.length === 0 ? (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '3rem', textAlign: 'center', color: '#9ca3af', fontSize: '0.9rem' }}>
          No campaigns yet. Create one to send bulk messages to your customers.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {campaigns.map(c => (
            <div key={c.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{c.name}</span>
                  {statusBadge(c.status)}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                  {c.channels.map(ch => ch === 'email' ? '📧' : '✈️').join(' ')}
                  {c.status === 'sent' && ` · ${c.sent_count} sent · ${c.failed_count} failed`}
                  {c.sent_at && ` · ${new Date(c.sent_at).toLocaleDateString()}`}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button onClick={() => previewRecipients(c.id)} style={{ padding: '5px 12px', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.75rem', cursor: 'pointer', background: '#fff' }}>
                  Preview
                </button>
                {c.status === 'draft' && (
                  <button onClick={() => sendCampaign(c.id)} disabled={sending === c.id} style={{ padding: '5px 12px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.75rem', cursor: 'pointer' }}>
                    {sending === c.id ? 'Sending...' : 'Send'}
                  </button>
                )}
                <button onClick={() => deleteCampaign(c.id)} style={{ padding: '5px 12px', border: '1px solid #fecaca', borderRadius: '9999px', fontSize: '0.75rem', cursor: 'pointer', background: '#fff', color: '#ef4444' }}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
