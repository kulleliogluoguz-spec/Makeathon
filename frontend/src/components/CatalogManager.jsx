import { useState, useEffect } from 'react';

export default function CatalogManager({ personaId }) {
  const [catalogs, setCatalogs] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const loadCatalogs = async () => {
    if (!personaId) return;
    try {
      const resp = await fetch(`/api/v1/catalogs/?persona_id=${personaId}`);
      const data = await resp.json();
      setCatalogs(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { loadCatalogs(); }, [personaId]);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !personaId) return;
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('persona_id', personaId);
      const resp = await fetch('/api/v1/catalogs/upload', {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText);
      }
      await loadCatalogs();
    } catch (e) {
      setError(e.message || 'Upload failed');
    }
    setUploading(false);
    e.target.value = '';
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this catalog?')) return;
    await fetch(`/api/v1/catalogs/${id}`, { method: 'DELETE' });
    await loadCatalogs();
  };

  const handleToggle = async (id, enabled) => {
    await fetch(`/api/v1/catalogs/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !enabled }),
    });
    await loadCatalogs();
  };

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <label style={{
          display: 'inline-block',
          padding: '0.5rem 1rem',
          background: '#000',
          color: '#fff',
          borderRadius: '0.5rem',
          cursor: uploading ? 'wait' : 'pointer',
          opacity: uploading ? 0.5 : 1,
          fontSize: '0.875rem',
        }}>
          {uploading ? 'Uploading & parsing...' : '+ Upload Catalog (PDF, Excel, CSV)'}
          <input
            type="file"
            accept=".pdf,.xlsx,.xls,.csv"
            onChange={handleUpload}
            disabled={uploading}
            style={{ display: 'none' }}
          />
        </label>
      </div>

      {error && (
        <div style={{ color: '#dc2626', fontSize: '0.875rem', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {catalogs.length === 0 ? (
        <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>
          No catalogs uploaded yet.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {catalogs.map((c) => (
            <div
              key={c.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 1rem',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                background: c.enabled ? '#fff' : '#f9fafb',
              }}
            >
              <div>
                <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                  {c.original_filename}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  {c.product_count} products · {c.file_type.toUpperCase()}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => handleToggle(c.id, c.enabled)}
                  style={{
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.75rem',
                    borderRadius: '9999px',
                    border: '1px solid #e5e7eb',
                    background: c.enabled ? '#10b981' : '#fff',
                    color: c.enabled ? '#fff' : '#000',
                    cursor: 'pointer',
                  }}
                >
                  {c.enabled ? 'Enabled' : 'Disabled'}
                </button>
                <button
                  onClick={() => handleDelete(c.id)}
                  style={{
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.75rem',
                    borderRadius: '9999px',
                    border: '1px solid #e5e7eb',
                    background: '#fff',
                    color: '#dc2626',
                    cursor: 'pointer',
                  }}
                >
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
