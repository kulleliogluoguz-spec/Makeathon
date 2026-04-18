import { useState, useEffect } from 'react';
import { t } from '../lib/i18n';

const STYLES = [
  { value: 'modern', label: 'Modern', icon: '🎨' },
  { value: 'minimal', label: 'Minimal', icon: '✨' },
  { value: 'bold', label: 'Bold', icon: '💥' },
  { value: 'corporate', label: 'Corporate', icon: '🏢' },
  { value: 'creative', label: 'Creative', icon: '🌈' },
  { value: 'startup', label: 'Startup', icon: '🚀' },
];

const COLORS = [
  { value: 'auto', label: 'Auto' },
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
  { value: 'blue', label: 'Blue' },
  { value: 'green', label: 'Green' },
  { value: 'purple', label: 'Purple' },
  { value: 'red', label: 'Red' },
  { value: 'orange', label: 'Orange' },
];

export default function LandingPageCreatorPage() {
  const [tab, setTab] = useState('create');
  const [personas, setPersonas] = useState([]);
  const [savedPages, setSavedPages] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [refining, setRefining] = useState(false);
  const [currentPage, setCurrentPage] = useState(null);
  const [refineInput, setRefineInput] = useState('');
  const [previewMode, setPreviewMode] = useState('desktop');

  const [form, setForm] = useState({
    persona_id: '',
    customer_name: '',
    customer_company: '',
    customer_industry: '',
    customer_description: '',
    style: 'modern',
    color_scheme: 'auto',
    language: 'en',
    additional_instructions: '',
  });

  useEffect(() => {
    fetch('/api/v1/personas/').then(r => r.json()).then(setPersonas).catch(() => {});
    loadSaved();
  }, []);

  const loadSaved = async () => {
    try {
      const resp = await fetch('/api/v1/landing-pages/');
      if (resp.ok) setSavedPages(await resp.json());
    } catch (e) {}
  };

  const generate = async () => {
    setGenerating(true);
    try {
      const resp = await fetch('/api/v1/landing-pages/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await resp.json();
      if (data.html) {
        setCurrentPage({ id: data.id, html: data.html, name: data.name });
        loadSaved();
      } else {
        alert('Error: ' + (data.detail || 'Generation failed'));
      }
    } catch (e) { alert('Error: ' + e.message); }
    setGenerating(false);
  };

  const refine = async () => {
    if (!currentPage || !refineInput) return;
    setRefining(true);
    try {
      const resp = await fetch(`/api/v1/landing-pages/${currentPage.id}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instruction: refineInput }),
      });
      const data = await resp.json();
      if (data.html) {
        setCurrentPage({ ...currentPage, html: data.html });
        setRefineInput('');
      }
    } catch (e) { alert('Error: ' + e.message); }
    setRefining(false);
  };

  const downloadHTML = () => {
    if (!currentPage) return;
    const blob = new Blob([currentPage.html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${form.customer_company || 'landing-page'}.html`.replace(/\s+/g, '-').toLowerCase();
    a.click();
    URL.revokeObjectURL(url);
  };

  const openPreview = (pageId) => {
    window.open(`/api/v1/landing-pages/${pageId}/preview`, '_blank');
  };

  const deletePage = async (id) => {
    if (!confirm('Delete this landing page?')) return;
    await fetch(`/api/v1/landing-pages/${id}`, { method: 'DELETE' });
    loadSaved();
    if (currentPage?.id === id) setCurrentPage(null);
  };

  const loadPage = async (id) => {
    try {
      const resp = await fetch(`/api/v1/landing-pages/${id}`);
      const data = await resp.json();
      setCurrentPage({ id: data.id, html: data.html_content, name: data.name });
    } catch (e) {}
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Landing Page Creator</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>AI-powered custom landing pages for your customers</p>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={() => setTab('create')} style={{ padding: '6px 16px', fontSize: '0.85rem', borderRadius: '9999px', background: tab === 'create' ? '#000' : '#fff', color: tab === 'create' ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>Create</button>
          <button onClick={() => { setTab('saved'); loadSaved(); }} style={{ padding: '6px 16px', fontSize: '0.85rem', borderRadius: '9999px', background: tab === 'saved' ? '#000' : '#fff', color: tab === 'saved' ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>Saved ({savedPages.length})</button>
        </div>
      </div>

      {tab === 'create' && (
        <div style={{ display: 'grid', gridTemplateColumns: currentPage ? '380px 1fr' : '1fr', gap: '1.5rem' }}>
          {/* Left Panel — Form */}
          <div>
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Client Details</h2>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>YOUR PERSONA</label>
                <select value={form.persona_id} onChange={(e) => setForm({ ...form, persona_id: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.85rem', outline: 'none' }}>
                  <option value="">Select persona...</option>
                  {personas.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>CLIENT COMPANY NAME *</label>
                <input type="text" value={form.customer_company} onChange={(e) => setForm({ ...form, customer_company: e.target.value })}
                  placeholder="e.g. NovaTech Solutions" style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box' }} />
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>CLIENT CONTACT NAME</label>
                <input type="text" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
                  placeholder="e.g. Thomas Berger" style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box' }} />
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>INDUSTRY</label>
                <input type="text" value={form.customer_industry} onChange={(e) => setForm({ ...form, customer_industry: e.target.value })}
                  placeholder="e.g. SaaS, E-commerce, Restaurant" style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.85rem', outline: 'none', boxSizing: 'border-box' }} />
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>COMPANY DESCRIPTION</label>
                <textarea value={form.customer_description} onChange={(e) => setForm({ ...form, customer_description: e.target.value })}
                  placeholder="What does the client's company do?" rows={3}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.85rem', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
              </div>
            </div>

            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Design</h2>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '6px' }}>STYLE</label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
                  {STYLES.map(s => (
                    <button key={s.value} onClick={() => setForm({ ...form, style: s.value })}
                      style={{
                        padding: '8px', fontSize: '0.75rem', borderRadius: '0.5rem', cursor: 'pointer',
                        background: form.style === s.value ? '#000' : '#fff',
                        color: form.style === s.value ? '#fff' : '#374151',
                        border: '1px solid #e5e7eb', textAlign: 'center',
                      }}>{s.icon} {s.label}</button>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '6px' }}>COLOR SCHEME</label>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {COLORS.map(c => (
                    <button key={c.value} onClick={() => setForm({ ...form, color_scheme: c.value })}
                      style={{
                        padding: '4px 12px', fontSize: '0.75rem', borderRadius: '9999px', cursor: 'pointer',
                        background: form.color_scheme === c.value ? '#000' : '#fff',
                        color: form.color_scheme === c.value ? '#fff' : '#374151',
                        border: '1px solid #e5e7eb',
                      }}>{c.label}</button>
                  ))}
                </div>
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>LANGUAGE</label>
                <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.85rem', outline: 'none' }}>
                  <option value="en">English</option>
                  <option value="de">German</option>
                  <option value="tr">Turkish</option>
                  <option value="fr">French</option>
                  <option value="es">Spanish</option>
                </select>
              </div>

              <div style={{ marginBottom: '0.75rem' }}>
                <label style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>ADDITIONAL INSTRUCTIONS</label>
                <textarea value={form.additional_instructions} onChange={(e) => setForm({ ...form, additional_instructions: e.target.value })}
                  placeholder="e.g. Include a pricing section, use blue gradient hero..." rows={2}
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.85rem', outline: 'none', resize: 'vertical', boxSizing: 'border-box' }} />
              </div>
            </div>

            <button onClick={generate} disabled={generating || !form.customer_company}
              style={{
                width: '100%', padding: '12px', background: '#000', color: '#fff',
                border: 'none', borderRadius: '0.5rem', fontSize: '0.95rem', fontWeight: 600,
                cursor: generating ? 'wait' : 'pointer', opacity: (generating || !form.customer_company) ? 0.5 : 1,
              }}>
              {generating ? '🤖 Generating with Clerque AI...' : '🚀 Generate Landing Page'}
            </button>

            {/* Refine Chat */}
            {currentPage && (
              <div style={{ marginTop: '1rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1rem' }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>✏️ Refine with AI</h3>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input type="text" value={refineInput} onChange={(e) => setRefineInput(e.target.value)}
                    placeholder="e.g. Make the hero section bigger, change colors to blue..."
                    onKeyDown={(e) => { if (e.key === 'Enter') refine(); }}
                    style={{ flex: 1, padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.85rem', outline: 'none' }} />
                  <button onClick={refine} disabled={refining || !refineInput}
                    style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer', opacity: refining ? 0.5 : 1 }}>
                    {refining ? '...' : 'Refine'}</button>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel — Preview */}
          {currentPage && (
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', overflow: 'hidden' }}>
              {/* Preview toolbar */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem 1rem', borderBottom: '1px solid #e5e7eb', background: '#f9fafb' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button onClick={() => setPreviewMode('desktop')} style={{ padding: '4px 10px', fontSize: '0.7rem', borderRadius: '9999px', background: previewMode === 'desktop' ? '#000' : '#fff', color: previewMode === 'desktop' ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>🖥️ Desktop</button>
                  <button onClick={() => setPreviewMode('tablet')} style={{ padding: '4px 10px', fontSize: '0.7rem', borderRadius: '9999px', background: previewMode === 'tablet' ? '#000' : '#fff', color: previewMode === 'tablet' ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>📱 Tablet</button>
                  <button onClick={() => setPreviewMode('mobile')} style={{ padding: '4px 10px', fontSize: '0.7rem', borderRadius: '9999px', background: previewMode === 'mobile' ? '#000' : '#fff', color: previewMode === 'mobile' ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>📲 Mobile</button>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button onClick={() => openPreview(currentPage.id)}
                    style={{ padding: '4px 12px', fontSize: '0.7rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>↗ Full Preview</button>
                  <button onClick={downloadHTML}
                    style={{ padding: '4px 12px', fontSize: '0.7rem', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>⬇ Download HTML</button>
                </div>
              </div>

              {/* iframe Preview */}
              <div style={{ display: 'flex', justifyContent: 'center', padding: '1rem', background: '#f3f4f6', minHeight: '600px' }}>
                <iframe
                  srcDoc={currentPage.html}
                  style={{
                    width: previewMode === 'mobile' ? '375px' : previewMode === 'tablet' ? '768px' : '100%',
                    height: '700px',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    background: '#fff',
                    transition: 'width 0.3s',
                  }}
                  title="Landing Page Preview"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Saved Pages Tab */}
      {tab === 'saved' && (
        <div>
          {savedPages.length === 0 ? (
            <div style={{ color: '#9ca3af', padding: '3rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.75rem' }}>
              No landing pages yet. Create your first one!
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
              {savedPages.map(page => (
                <div key={page.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '4px' }}>{page.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '4px' }}>{page.customer_company}</div>
                  <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginBottom: '1rem' }}>
                    {page.style} · {new Date(page.created_at).toLocaleDateString()}
                  </div>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button onClick={() => { loadPage(page.id); setTab('create'); }}
                      style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>Edit</button>
                    <button onClick={() => openPreview(page.id)}
                      style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>Preview</button>
                    <button onClick={() => deletePage(page.id)}
                      style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer' }}>Delete</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
