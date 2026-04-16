import { useState, useEffect } from 'react';

function Tag({ children, onRemove }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '0.75rem',
      padding: '3px 10px',
      background: '#e0e7ff',
      color: '#3730a3',
      borderRadius: '9999px',
      fontWeight: 500,
    }}>
      {children}
      {onRemove && (
        <button onClick={onRemove} style={{
          background: 'transparent', border: 'none', color: '#3730a3',
          cursor: 'pointer', padding: 0, fontSize: '0.875rem', lineHeight: 1,
        }}>×</button>
      )}
    </span>
  );
}

function SourceBadge({ source }) {
  const config = {
    instagram: { label: 'Instagram', color: '#e1306c' },
    whatsapp: { label: 'WhatsApp', color: '#25d366' },
    manual: { label: 'Manual', color: '#64748b' },
    livechat: { label: 'Live Chat', color: '#0ea5e9' },
  };
  const c = config[source] || { label: source, color: '#64748b' };
  return (
    <span style={{
      fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px',
      background: c.color + '20', color: c.color, fontWeight: 500,
    }}>{c.label}</span>
  );
}

export default function CustomersPage() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [selected, setSelected] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [conversations, setConversations] = useState([]);

  const load = async () => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (sourceFilter) params.append('source', sourceFilter);
    try {
      const resp = await fetch(`/api/v1/customers/?${params}`);
      setCustomers(await resp.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [search, sourceFilter]);

  const openCustomer = async (customer) => {
    setSelected(customer);
    try {
      const resp = await fetch(`/api/v1/customers/${customer.id}/conversations`);
      setConversations(await resp.json());
    } catch (e) { setConversations([]); }
  };

  const saveCustomer = async (customer) => {
    const resp = await fetch(`/api/v1/customers/${customer.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(customer),
    });
    const updated = await resp.json();
    setSelected(updated);
    load();
  };

  const deleteCustomer = async (id) => {
    if (!confirm('Delete this customer?')) return;
    await fetch(`/api/v1/customers/${id}`, { method: 'DELETE' });
    setSelected(null);
    load();
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Customers</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Unified customer database across all channels</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            padding: '0.5rem 1rem', background: '#000', color: '#fff',
            borderRadius: '0.5rem', border: 'none', fontSize: '0.875rem', cursor: 'pointer',
          }}
        >+ Add Customer</button>
      </div>

      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <input
          type="text"
          placeholder="Search by name, handle, email, phone..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1, padding: '0.5rem 1rem', fontSize: '0.875rem',
            border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
          }}
        />
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          style={{
            padding: '0.5rem 1rem', fontSize: '0.875rem',
            border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
          }}
        >
          <option value="">All sources</option>
          <option value="instagram">Instagram</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="manual">Manual</option>
          <option value="livechat">Live Chat</option>
        </select>
      </div>

      {customers.length === 0 ? (
        <div style={{
          color: '#9ca3af', padding: '3rem', textAlign: 'center',
          border: '1px dashed #e5e7eb', borderRadius: '0.75rem',
        }}>
          No customers yet. They will appear here when they message you, or you can add them manually.
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '1.5rem' }}>
          {/* List */}
          <div style={{ flex: 1, maxWidth: '500px' }}>
            {customers.map((c) => (
              <div
                key={c.id}
                onClick={() => openCustomer(c)}
                style={{
                  padding: '1rem',
                  border: '1px solid',
                  borderColor: selected?.id === c.id ? '#000' : '#e5e7eb',
                  borderRadius: '0.75rem',
                  marginBottom: '0.5rem',
                  cursor: 'pointer',
                  background: '#fff',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>
                    {c.display_name || c.handle || 'Unnamed'}
                  </div>
                  <SourceBadge source={c.source} />
                </div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  {c.handle && `@${c.handle} · `}
                  {c.email && `${c.email} · `}
                  {c.phone && `${c.phone} · `}
                  {c.total_messages} messages
                </div>
                {c.tags && c.tags.length > 0 && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {c.tags.map((t, i) => <Tag key={i}>{t}</Tag>)}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Detail */}
          <div style={{ flex: 1.2 }}>
            {!selected ? (
              <div style={{ color: '#9ca3af', padding: '2rem', textAlign: 'center' }}>
                Select a customer to view details
              </div>
            ) : (
              <CustomerDetail
                customer={selected}
                conversations={conversations}
                onSave={saveCustomer}
                onDelete={() => deleteCustomer(selected.id)}
              />
            )}
          </div>
        </div>
      )}

      {showCreate && (
        <CreateCustomerModal
          onClose={() => setShowCreate(false)}
          onCreate={async (data) => {
            const resp = await fetch('/api/v1/customers/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data),
            });
            const created = await resp.json();
            setShowCreate(false);
            load();
            openCustomer(created);
          }}
        />
      )}
    </div>
  );
}

function CustomerDetail({ customer, conversations, onSave, onDelete }) {
  const [editing, setEditing] = useState(null);
  const [tagInput, setTagInput] = useState('');

  useEffect(() => { setEditing(customer); }, [customer]);

  if (!editing) return null;

  const update = (field, value) => setEditing({ ...editing, [field]: value });

  const addTag = () => {
    if (!tagInput.trim()) return;
    const newTags = [...(editing.tags || []), tagInput.trim()];
    setEditing({ ...editing, tags: newTags });
    setTagInput('');
  };

  const removeTag = (i) => {
    const newTags = (editing.tags || []).filter((_, idx) => idx !== i);
    setEditing({ ...editing, tags: newTags });
  };

  const hasChanges = JSON.stringify(editing) !== JSON.stringify(customer);

  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#fff', padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Customer Details</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {hasChanges && (
            <button onClick={() => onSave(editing)} style={{
              padding: '4px 12px', fontSize: '0.75rem', background: '#000',
              color: '#fff', borderRadius: '9999px', border: 'none', cursor: 'pointer',
            }}>Save</button>
          )}
          <button onClick={onDelete} style={{
            padding: '4px 12px', fontSize: '0.75rem', background: '#fff',
            color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', cursor: 'pointer',
          }}>Delete</button>
        </div>
      </div>

      <Field label="Display name" value={editing.display_name} onChange={(v) => update('display_name', v)} />
      <Field label="Handle / Username" value={editing.handle} onChange={(v) => update('handle', v)} prefix="@" />
      <Field label="Email" value={editing.email} onChange={(v) => update('email', v)} />
      <Field label="Phone" value={editing.phone} onChange={(v) => update('phone', v)} />

      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>TAGS</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '6px' }}>
          {(editing.tags || []).map((t, i) => <Tag key={i} onRemove={() => removeTag(i)}>{t}</Tag>)}
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          <input
            type="text"
            placeholder="Add tag..."
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') addTag(); }}
            style={{
              flex: 1, padding: '4px 10px', fontSize: '0.75rem',
              border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
            }}
          />
        </div>
      </div>

      <Field label="Notes" value={editing.notes} onChange={(v) => update('notes', v)} textarea />

      {(editing.instagram_sender_id || editing.whatsapp_phone) && (
        <div style={{ marginBottom: '1rem', fontSize: '0.75rem', color: '#6b7280' }}>
          {editing.instagram_sender_id && <div>IG Sender ID: {editing.instagram_sender_id}</div>}
          {editing.whatsapp_phone && <div>WhatsApp: {editing.whatsapp_phone}</div>}
          <div>Source: {editing.source}</div>
        </div>
      )}

      {conversations.length > 0 && (
        <div style={{ marginTop: '1.5rem', borderTop: '1px solid #e5e7eb', paddingTop: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>
            CONVERSATIONS ({conversations.length})
          </div>
          {conversations.map((c) => (
            <div key={c.id} style={{
              padding: '0.5rem 0.75rem', border: '1px solid #e5e7eb',
              borderRadius: '0.5rem', marginBottom: '0.5rem', fontSize: '0.8rem',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{c.channel} · {c.message_count} messages</span>
                <span style={{ fontWeight: 500 }}>Score: {c.intent_score}</span>
              </div>
              <div style={{ color: '#6b7280', fontSize: '0.7rem', marginTop: '2px' }}>
                Stage: {c.stage} · Last: {c.last_message_at ? new Date(c.last_message_at).toLocaleString() : 'never'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Field({ label, value, onChange, prefix, textarea }) {
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px', textTransform: 'uppercase' }}>
        {label}
      </div>
      {textarea ? (
        <textarea
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          style={{
            width: '100%', padding: '6px 10px', fontSize: '0.875rem',
            border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none', resize: 'vertical',
          }}
        />
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {prefix && <span style={{ color: '#9ca3af' }}>{prefix}</span>}
          <input
            type="text"
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            style={{
              flex: 1, padding: '6px 10px', fontSize: '0.875rem',
              border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none',
            }}
          />
        </div>
      )}
    </div>
  );
}

function CreateCustomerModal({ onClose, onCreate }) {
  const [data, setData] = useState({
    display_name: '',
    handle: '',
    email: '',
    phone: '',
    source: 'manual',
    instagram_sender_id: '',
    whatsapp_phone: '',
    notes: '',
    tags: [],
  });

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: '#fff', borderRadius: '0.75rem', padding: '1.5rem',
        width: '500px', maxHeight: '90vh', overflowY: 'auto',
      }}>
        <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: '1rem' }}>Add Customer</h2>

        <Field label="Display name *" value={data.display_name} onChange={(v) => setData({ ...data, display_name: v })} />
        <Field label="Handle / Username" value={data.handle} onChange={(v) => setData({ ...data, handle: v })} prefix="@" />
        <Field label="Email" value={data.email} onChange={(v) => setData({ ...data, email: v })} />
        <Field label="Phone" value={data.phone} onChange={(v) => setData({ ...data, phone: v })} />

        <div style={{ marginBottom: '0.75rem' }}>
          <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px', textTransform: 'uppercase' }}>Source</div>
          <select
            value={data.source}
            onChange={(e) => setData({ ...data, source: e.target.value })}
            style={{
              width: '100%', padding: '6px 10px', fontSize: '0.875rem',
              border: '1px solid #e5e7eb', borderRadius: '0.5rem', outline: 'none',
            }}
          >
            <option value="manual">Manual</option>
            <option value="instagram">Instagram</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="livechat">Live Chat</option>
          </select>
        </div>

        {data.source === 'instagram' && (
          <Field label="Instagram Sender ID" value={data.instagram_sender_id} onChange={(v) => setData({ ...data, instagram_sender_id: v })} />
        )}
        {data.source === 'whatsapp' && (
          <Field label="WhatsApp Phone" value={data.whatsapp_phone} onChange={(v) => setData({ ...data, whatsapp_phone: v })} />
        )}

        <Field label="Notes" value={data.notes} onChange={(v) => setData({ ...data, notes: v })} textarea />

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.5rem' }}>
          <button onClick={onClose} style={{
            padding: '6px 16px', fontSize: '0.875rem', background: '#fff',
            border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
          }}>Cancel</button>
          <button
            onClick={() => onCreate(data)}
            disabled={!data.display_name && !data.handle}
            style={{
              padding: '6px 16px', fontSize: '0.875rem', background: '#000', color: '#fff',
              border: 'none', borderRadius: '9999px', cursor: 'pointer',
              opacity: (!data.display_name && !data.handle) ? 0.4 : 1,
            }}
          >Create</button>
        </div>
      </div>
    </div>
  );
}
