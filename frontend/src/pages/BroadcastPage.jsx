import { useState, useEffect } from 'react';
import { authFetch } from '../lib/auth';
import { t } from '../lib/i18n';

const STATUS_COLORS = {
  draft: { bg: '#f3f4f6', color: '#374151' },
  sending: { bg: '#fef3c7', color: '#92400e' },
  sent: { bg: '#d1fae5', color: '#065f46' },
  failed: { bg: '#fee2e2', color: '#991b1b' },
};

export default function BroadcastPage() {
  const [campaigns, setCampaigns] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', subject: '', message: '', channels: ['email'], recipient_filter: {} });
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);

  const load = async () => {
    try { const resp = await fetch('/api/v1/broadcasts/'); if (resp.ok) setCampaigns(await resp.json()); } catch (e) {}
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    const resp = await fetch('/api/v1/broadcasts/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) });
    if (resp.ok) {
      const campaign = await resp.json();
      setShowCreate(false);
      setForm({ name: '', subject: '', message: '', channels: ['email'], recipient_filter: {} });
      load();
      const prev = await fetch(`/api/v1/broadcasts/${campaign.id}/preview`);
      if (prev.ok) setPreview({ ...(await prev.json()), campaign_id: campaign.id });
    }
  };

  const sendCampaign = async (id) => {
    setSending(true);
    await fetch(`/api/v1/broadcasts/${id}/send`, { method: 'POST' });
    setSending(false);
    setPreview(null);
    load();
  };

  const deleteCampaign = async (id) => {
    if (!confirm('Delete this campaign?')) return;
    await fetch(`/api/v1/broadcasts/${id}`, { method: 'DELETE' });
    load();
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>{t('nav_broadcast')}</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Send campaigns via Email and Telegram to your customers</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          style={{ padding: '0.5rem 1rem', background: '#000', color: '#fff', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', cursor: 'pointer' }}>+ New Campaign</button>
      </div>

      {showCreate && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>New Campaign</h2>
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Campaign Name</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Spring Sale Announcement"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' }} />
          </div>
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Email Subject</label>
            <input type="text" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="e.g. New products just arrived!"
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' }} />
          </div>
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Message</label>
            <textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} rows={5} placeholder="Write your broadcast message here..."
              style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
          </div>
          <div style={{ marginBottom: '0.75rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Channels</label>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              {['email', 'telegram'].map(ch => (
                <label key={ch} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.channels.includes(ch)}
                    onChange={(e) => { const channels = e.target.checked ? [...form.channels, ch] : form.channels.filter(c => c !== ch); setForm({ ...form, channels }); }} />
                  {ch === 'email' ? 'Email' : 'Telegram'}
                </label>
              ))}
            </div>
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>Filter Recipients (optional)</label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <select value={form.recipient_filter.source || ''} onChange={(e) => setForm({ ...form, recipient_filter: { ...form.recipient_filter, source: e.target.value || undefined } })}
                style={{ padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.8rem', outline: 'none' }}>
                <option value="">All channels</option>
                <option value="instagram">Instagram only</option>
                <option value="messenger">Messenger only</option>
                <option value="telegram">Telegram only</option>
                <option value="livechat">Live Chat only</option>
                <option value="manual">Manual only</option>
              </select>
              <select value={form.recipient_filter.category || ''} onChange={(e) => setForm({ ...form, recipient_filter: { ...form.recipient_filter, category: e.target.value || undefined } })}
                style={{ padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.8rem', outline: 'none' }}>
                <option value="">All categories</option>
                <option value="high_sales_potential">High Sales Potential</option>
                <option value="sales_potential">Sales Potential</option>
                <option value="no_sales_potential">No Sales Potential</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={create} disabled={!form.name || !form.message}
              style={{ padding: '8px 20px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer', opacity: (!form.name || !form.message) ? 0.4 : 1 }}>Create & Preview</button>
            <button onClick={() => setShowCreate(false)}
              style={{ padding: '8px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {preview && (
        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>Preview</h3>
          <div style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>Total customers: <strong>{preview.total_customers}</strong></div>
          <div style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>Email recipients: <strong>{preview.email_recipients}</strong> · Telegram recipients: <strong>{preview.telegram_recipients}</strong></div>
          <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>
            First {Math.min(preview.customers?.length || 0, 10)}: {(preview.customers || []).slice(0, 10).map(c => c.display_name || c.email || 'Unknown').join(', ')}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button onClick={() => sendCampaign(preview.campaign_id)} disabled={sending}
              style={{ padding: '8px 20px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer', opacity: sending ? 0.5 : 1 }}>{sending ? 'Sending...' : 'Send Now'}</button>
            <button onClick={() => setPreview(null)}
              style={{ padding: '8px 20px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer' }}>Cancel</button>
          </div>
        </div>
      )}

      {campaigns.length === 0 && !showCreate ? (
        <div style={{ color: '#9ca3af', padding: '3rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.75rem' }}>
          No campaigns yet. Create one to start reaching your customers.
        </div>
      ) : (
        campaigns.map((c) => {
          const sc = STATUS_COLORS[c.status] || STATUS_COLORS.draft;
          return (
            <div key={c.id} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', marginBottom: '0.5rem', background: '#fff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{c.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '2px' }}>
                    {c.channels.map(ch => ch === 'email' ? 'Email' : 'Telegram').join(', ')} · {c.message.slice(0, 80)}{c.message.length > 80 ? '...' : ''}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '4px' }}>
                    {c.sent_at ? `Sent ${new Date(c.sent_at).toLocaleString()} · ${c.sent_count} delivered · ${c.failed_count} failed` : `Created ${new Date(c.created_at).toLocaleString()}`}
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.7rem', padding: '3px 10px', borderRadius: '9999px', background: sc.bg, color: sc.color, fontWeight: 600 }}>{c.status}</span>
                  {c.status === 'draft' && (
                    <button onClick={async () => { const prev = await fetch(`/api/v1/broadcasts/${c.id}/preview`); if (prev.ok) setPreview({ ...(await prev.json()), campaign_id: c.id }); }}
                      style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>Send</button>
                  )}
                  <button onClick={() => deleteCampaign(c.id)}
                    style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
