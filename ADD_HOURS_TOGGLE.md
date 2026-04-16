Add a master ON/OFF toggle for business hours. When OFF, the AI responds 24/7 regardless of working hours settings.

RULES: Do NOT rewrite files. Do NOT push to git. Only make these specific changes.

1. In frontend/src/pages/SettingsPage.jsx, find the "Working Hours" section header. Add a toggle RIGHT NEXT to the h2 title, same pattern as the "Outside Hours Auto-Reply" enabled toggle:

```jsx
<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
  <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Working Hours</h2>
  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem', cursor: 'pointer' }}>
    <span style={{ color: settings.outside_hours_enabled ? '#10b981' : '#94a3b8', fontWeight: 500 }}>
      {settings.outside_hours_enabled ? 'Active' : 'Disabled (24/7)'}
    </span>
    <input
      type="checkbox"
      checked={settings.outside_hours_enabled}
      onChange={(e) => setSettings({ ...settings, outside_hours_enabled: e.target.checked })}
      style={{ width: '18px', height: '18px', cursor: 'pointer' }}
    />
  </label>
</div>
```

Replace the existing plain `<h2>Working Hours</h2>` with this block. Do NOT change anything else in the section.

2. When outside_hours_enabled is false, gray out the entire working hours grid (days, times) to visually indicate it's disabled. Wrap the days grid in a div:

```jsx
<div style={{ opacity: settings.outside_hours_enabled ? 1 : 0.3, pointerEvents: settings.outside_hours_enabled ? 'auto' : 'none' }}>
  {/* existing DAYS.map(...) block stays here unchanged */}
</div>
```

3. No backend change needed — the backend already checks `outside_hours_enabled` in `is_within_business_hours()`. When it's False, the function returns `(True, "")` meaning "open", so AI responds normally 24/7.

That is ALL. Only SettingsPage.jsx changes, nothing else.

DO NOT push to git.
