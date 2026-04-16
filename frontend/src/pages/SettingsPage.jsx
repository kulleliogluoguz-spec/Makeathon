import { useState, useEffect } from 'react';

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
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Settings</h1>
      <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '2rem' }}>
        Business hours, auto-reply, and archive settings
      </p>

      {/* Working Hours */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>Working Hours</h2>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '4px' }}>TIMEZONE</label>
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
      </section>

      {/* Outside Hours Message */}
      <section style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Outside Hours Auto-Reply</h2>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.875rem' }}>
            <input
              type="checkbox"
              checked={settings.outside_hours_enabled}
              onChange={(e) => setSettings({ ...settings, outside_hours_enabled: e.target.checked })}
            />
            Enabled
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
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem' }}>Holidays</h2>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '0.75rem' }}>
          <input
            type="date"
            value={holidayInput}
            onChange={(e) => setHolidayInput(e.target.value)}
            style={{ padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}
          />
          <button onClick={addHoliday} style={{ padding: '6px 12px', background: '#000', color: '#fff', border: 'none', borderRadius: '0.5rem', fontSize: '0.875rem', cursor: 'pointer' }}>Add</button>
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
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '0.75rem' }}>Auto-Archive</h2>
        <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.75rem' }}>
          Automatically archive customers with no activity after this many hours. Set 0 to disable.
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="number"
            value={settings.auto_archive_hours}
            onChange={(e) => setSettings({ ...settings, auto_archive_hours: e.target.value })}
            min="0"
            style={{ width: '80px', padding: '6px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}
          />
          <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>hours of inactivity</span>
        </div>
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
        {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}
      </button>
    </div>
  );
}
