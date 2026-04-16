import { useState, useEffect } from 'react';
import { t, getLang, setLang } from '../lib/i18n';

const DAYS = [
  { key: 'mon', label: 'Monday' },
  { key: 'tue', label: 'Tuesday' },
  { key: 'wed', label: 'Wednesday' },
  { key: 'thu', label: 'Thursday' },
  { key: 'fri', label: 'Friday' },
  { key: 'sat', label: 'Saturday' },
  { key: 'sun', label: 'Sunday' },
];

export default function SettingsPage() {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [holidayInput, setHolidayInput] = useState('');
  const [personas, setPersonas] = useState([]);
  const [selectedPersona, setSelectedPersona] = useState('');
  const [copied, setCopied] = useState(false);
  const [quickReplies, setQuickReplies] = useState([]);
  const [showQRForm, setShowQRForm] = useState(false);
  const [qrForm, setQrForm] = useState({ title: '', content: '', category: '', keywords: '' });
  const [editingQR, setEditingQR] = useState(null);

  const loadQR = async () => {
    fetch('/api/v1/quick-replies/').then(r => r.json()).then(setQuickReplies).catch(() => {});
  };
  useEffect(() => { loadQR(); }, []);

  useEffect(() => {
    fetch('/api/v1/personas/').then(r => r.json()).then(setPersonas).catch(() => {});
  }, []);

  useEffect(() => {
    fetch('/api/v1/settings/business-hours')
      .then(r => r.json())
      .then(setSettings)
      .catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    await fetch('/api/v1/settings/business-hours', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const updateDay = (day, field, value) => {
    setSettings(prev => ({
      ...prev,
      working_hours: {
        ...prev.working_hours,
        [day]: { ...prev.working_hours[day], [field]: value },
      },
    }));
  };

  const addHoliday = () => {
    if (!holidayInput) return;
    setSettings(prev => ({
      ...prev,
      holidays: [...(prev.holidays || []), holidayInput],
    }));
    setHolidayInput('');
  };

  const removeHoliday = (i) => {
    setSettings(prev => ({
      ...prev,
      holidays: (prev.holidays || []).filter((_, idx) => idx !== i),
    }));
  };

  if (!settings) return <div style={{ padding: '2rem' }}>Loading...</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>{t('settings_title')}</h1>
      <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '2rem' }}>
        {t('settings_subtitle')}
      </p>

      {/* Platform Language */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.5rem' }}>{t('settings_language')}</h2>
        <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>{t('settings_language_desc')}</p>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setLang('en')}
            style={{
              padding: '8px 24px', fontSize: '0.875rem', borderRadius: '9999px',
              background: getLang() === 'en' ? '#000' : '#fff',
              color: getLang() === 'en' ? '#fff' : '#374151',
              border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500,
            }}
          >English</button>
          <button
            onClick={() => setLang('tr')}
            style={{
              padding: '8px 24px', fontSize: '0.875rem', borderRadius: '9999px',
              background: getLang() === 'tr' ? '#000' : '#fff',
              color: getLang() === 'tr' ? '#fff' : '#374151',
              border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500,
            }}
          >Türkçe</button>
        </div>
      </section>

      {/* Working Hours */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>{t('settings_working_hours')}</h2>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', cursor: 'pointer' }}>
            <span style={{ color: settings.outside_hours_enabled ? '#10b981' : '#94a3b8', fontWeight: 500 }}>
              {settings.outside_hours_enabled ? t('settings_active') : t('settings_disabled_247')}
            </span>
            <input
              type="checkbox"
              checked={settings.outside_hours_enabled}
              onChange={(e) => setSettings({ ...settings, outside_hours_enabled: e.target.checked })}
              style={{ width: '18px', height: '18px', cursor: 'pointer' }}
            />
          </label>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>{t('settings_timezone')}</label>
          <select
            value={settings.timezone}
            onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
            style={{ padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }}
          >
            <option value="Europe/Berlin">Europe/Berlin (CET)</option>
            <option value="Europe/Istanbul">Europe/Istanbul (TRT)</option>
            <option value="Europe/London">Europe/London (GMT)</option>
            <option value="America/New_York">America/New York (EST)</option>
            <option value="UTC">UTC</option>
          </select>
        </div>

        <div style={{ opacity: settings.outside_hours_enabled ? 1 : 0.3, pointerEvents: settings.outside_hours_enabled ? 'auto' : 'none' }}>
        {DAYS.map(({ key, label }) => {
          const day = settings.working_hours?.[key] || { start: '09:00', end: '18:00', enabled: false };
          return (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <label style={{ width: '100px', fontSize: '0.875rem', fontWeight: 500 }}>{label}</label>
              <input
                type="checkbox"
                checked={day.enabled || false}
                onChange={(e) => updateDay(key, 'enabled', e.target.checked)}
              />
              <input
                type="time"
                value={day.start || '09:00'}
                onChange={(e) => updateDay(key, 'start', e.target.value)}
                disabled={!day.enabled}
                style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '0.375rem', fontSize: '0.875rem', opacity: day.enabled ? 1 : 0.4 }}
              />
              <span style={{ color: '#6b7280' }}>to</span>
              <input
                type="time"
                value={day.end || '18:00'}
                onChange={(e) => updateDay(key, 'end', e.target.value)}
                disabled={!day.enabled}
                style={{ padding: '4px 8px', border: '1px solid #e5e7eb', borderRadius: '0.375rem', fontSize: '0.875rem', opacity: day.enabled ? 1 : 0.4 }}
              />
            </div>
          );
        })}
        </div>
      </section>

      {/* Outside Hours Message */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>{t('settings_outside_hours')}</h2>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem' }}>
            <input
              type="checkbox"
              checked={settings.outside_hours_enabled}
              onChange={(e) => setSettings({ ...settings, outside_hours_enabled: e.target.checked })}
            />
            {t('settings_enabled')}
          </label>
        </div>
        <textarea
          value={settings.outside_hours_message}
          onChange={(e) => setSettings({ ...settings, outside_hours_message: e.target.value })}
          rows={3}
          style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', resize: 'vertical' }}
        />
      </section>

      {/* Holidays */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem' }}>{t('settings_holidays')}</h2>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '0.75rem' }}>
          <input
            type="date"
            value={holidayInput}
            onChange={(e) => setHolidayInput(e.target.value)}
            style={{ padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}
          />
          <button onClick={addHoliday} style={{ padding: '6px 12px', background: '#000', color: '#fff', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', cursor: 'pointer' }}>{t('settings_holiday_add')}</button>
        </div>
        <textarea
          value={settings.holiday_message}
          onChange={(e) => setSettings({ ...settings, holiday_message: e.target.value })}
          rows={2}
          placeholder="Holiday auto-reply message"
          style={{ width: '100%', padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', marginBottom: '0.5rem', resize: 'vertical' }}
        />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {(settings.holidays || []).map((h, i) => (
            <span key={i} style={{ fontSize: '0.75rem', padding: '4px 10px', background: '#fef3c7', color: '#92400e', borderRadius: '9999px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              {h}
              <button onClick={() => removeHoliday(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#92400e', fontSize: '0.875rem' }}>x</button>
            </span>
          ))}
        </div>
      </section>

      {/* Auto-Archive */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem' }}>{t('settings_auto_archive')}</h2>
        <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.75rem' }}>
          {t('settings_auto_archive_desc')}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="number"
            value={settings.auto_archive_hours}
            onChange={(e) => setSettings({ ...settings, auto_archive_hours: e.target.value })}
            min="0"
            style={{ width: '80px', padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}
          />
          <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>{t('settings_hours_inactivity')}</span>
        </div>
      </section>

      {/* CSAT Survey */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>{t('csat_title')}</h2>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', cursor: 'pointer' }}>
            <span style={{ fontWeight: 500 }}>{t('settings_enabled')}</span>
            <input type="checkbox" defaultChecked style={{ width: '18px', height: '18px' }} />
          </label>
        </div>
        <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
          After a conversation goes inactive, the system sends a satisfaction survey to the customer.
          They reply with 1-5 stars. Results appear in Analytics and Conversation details.
        </p>
        <p style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
          Currently active on: Instagram, Messenger. LiveChat widget shows rating UI automatically.
        </p>
      </section>

      {/* Quick Replies */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>{t('qr_title')}</h2>
            <p style={{ fontSize: '0.8rem', color: '#6b7280' }}>{t('qr_subtitle')}</p>
          </div>
          <button
            onClick={() => { setQrForm({ title: '', content: '', category: '', keywords: '' }); setEditingQR(null); setShowQRForm(true); }}
            style={{ padding: '6px 14px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}
          >{t('qr_add')}</button>
        </div>

        {quickReplies.length === 0 ? (
          <div style={{ color: '#9ca3af', fontSize: '0.875rem', padding: '1rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.5rem' }}>
            {t('qr_no_templates')}
          </div>
        ) : (
          quickReplies.map((qr) => (
            <div key={qr.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '0.75rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', marginBottom: '0.5rem' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{qr.title}</div>
                <div style={{ fontSize: '0.8rem', color: '#374151', marginTop: '2px' }}>{qr.content.slice(0, 120)}{qr.content.length > 120 ? '...' : ''}</div>
                <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '4px' }}>
                  {qr.category && `${qr.category} · `}{t('qr_keywords')}: {qr.keywords || 'none'} · {t('qr_used')} {qr.use_count}x
                </div>
              </div>
              <div style={{ display: 'flex', gap: '4px', marginLeft: '0.5rem' }}>
                <button onClick={() => { setQrForm({ title: qr.title, content: qr.content, category: qr.category, keywords: qr.keywords }); setEditingQR(qr.id); setShowQRForm(true); }}
                  style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>Edit</button>
                <button onClick={async () => { if (confirm('Delete?')) { await fetch(`/api/v1/quick-replies/${qr.id}`, { method: 'DELETE' }); loadQR(); } }}
                  style={{ padding: '3px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
              </div>
            </div>
          ))
        )}

        {showQRForm && (
          <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', background: '#f9fafb' }}>
            <div style={{ marginBottom: '0.5rem' }}>
              <input type="text" placeholder="Title (e.g. Return Policy)" value={qrForm.title} onChange={(e) => setQrForm({ ...qrForm, title: e.target.value })}
                style={{ width: '100%', padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }} />
            </div>
            <div style={{ marginBottom: '0.5rem' }}>
              <textarea placeholder="Full reply text..." value={qrForm.content} onChange={(e) => setQrForm({ ...qrForm, content: e.target.value })} rows={4}
                style={{ width: '100%', padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none', resize: 'vertical' }} />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <input type="text" placeholder="Category (optional)" value={qrForm.category} onChange={(e) => setQrForm({ ...qrForm, category: e.target.value })}
                style={{ flex: 1, padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }} />
              <input type="text" placeholder="Keywords: return,refund,exchange" value={qrForm.keywords} onChange={(e) => setQrForm({ ...qrForm, keywords: e.target.value })}
                style={{ flex: 1, padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }} />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={async () => {
                const method = editingQR ? 'PATCH' : 'POST';
                const url = editingQR ? `/api/v1/quick-replies/${editingQR}` : '/api/v1/quick-replies/';
                await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(qrForm) });
                setShowQRForm(false); setEditingQR(null); loadQR();
              }} disabled={!qrForm.title || !qrForm.content}
                style={{ padding: '6px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer', opacity: (!qrForm.title || !qrForm.content) ? 0.4 : 1 }}>
                {editingQR ? 'Save' : 'Create'}
              </button>
              <button onClick={() => { setShowQRForm(false); setEditingQR(null); }}
                style={{ padding: '6px 16px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>Cancel</button>
            </div>
          </div>
        )}
      </section>

      {/* Live Chat Widget */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.5rem' }}>{t('settings_livechat')}</h2>
        <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
          {t('settings_livechat_desc')}
        </p>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>{t('settings_persona')}</label>
          <select
            value={selectedPersona}
            onChange={(e) => setSelectedPersona(e.target.value)}
            style={{ width: '100%', padding: '6px 10px', fontSize: '0.875rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none' }}
          >
            <option value="">{t('settings_select_persona')}</option>
            {personas.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {selectedPersona && (
          <>
            <div style={{
              background: '#111', color: '#10b981', padding: '1rem',
              borderRadius: '0.5rem', fontFamily: 'monospace', fontSize: '0.75rem',
              overflowX: 'auto', marginBottom: '0.75rem', lineHeight: 1.5,
            }}>
              {`<script src="${window.location.origin}/widget/chat.js" data-persona-id="${selectedPersona}"></script>`}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`<script src="${window.location.origin}/widget/chat.js" data-persona-id="${selectedPersona}"></script>`);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                style={{
                  padding: '6px 16px', background: '#000', color: '#fff',
                  border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
                }}
              >{copied ? t('settings_copied') : t('settings_copy_code')}</button>
              <button
                onClick={() => {
                  var s = document.createElement('script');
                  s.src = '/widget/chat.js';
                  s.setAttribute('data-persona-id', selectedPersona);
                  document.body.appendChild(s);
                }}
                style={{
                  padding: '6px 16px', background: '#fff', color: '#000',
                  border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
                }}
              >{t('settings_test_widget')}</button>
            </div>
          </>
        )}
      </section>

      {/* Save */}
      <button
        onClick={save}
        disabled={saving}
        style={{
          padding: '0.75rem 2rem', background: '#000', color: '#fff',
          border: 'none', borderRadius: '0.5rem', fontSize: '1rem',
          cursor: saving ? 'wait' : 'pointer', opacity: saving ? 0.5 : 1,
        }}
      >
        {saving ? t('settings_saving') : saved ? t('settings_saved') : t('settings_save')}
      </button>
    </div>
  );
}
