import { useState, useEffect } from 'react';
import { t } from '../lib/i18n';
import { authFetch, getUser } from '../lib/auth';
import { resetUnread } from '../lib/notifications';

const STAGE_COLORS = {
  awareness: '#94a3b8',
  interest: '#3b82f6',
  consideration: '#8b5cf6',
  decision: '#f59e0b',
  purchase: '#10b981',
  objection: '#ef4444',
  post_purchase: '#06b6d4',
};

const STAGE_LABELS = {
  awareness: 'Awareness',
  interest: 'Interest',
  consideration: 'Considering',
  decision: 'Deciding',
  purchase: 'Ready to Buy',
  objection: 'Objection',
  post_purchase: 'Post-Purchase',
};

function ScoreGauge({ score }) {
  const color = score >= 70 ? '#10b981' : score >= 40 ? '#f59e0b' : '#64748b';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div style={{ width: '60px', height: '6px', background: '#e5e7eb', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${score}%`, height: '100%', background: color, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontSize: '0.875rem', fontWeight: 600, color, minWidth: '36px' }}>{score}</span>
    </div>
  );
}

function StageBadge({ stage }) {
  const color = STAGE_COLORS[stage] || '#64748b';
  return (
    <span style={{
      fontSize: '0.75rem',
      fontWeight: 500,
      padding: '2px 10px',
      borderRadius: '9999px',
      background: color + '20',
      color: color,
    }}>
      {STAGE_LABELS[stage] || stage}
    </span>
  );
}

export default function ConversationsPage() {
  const [conversations, setConversations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [csatData, setCsatData] = useState(null);
  const [quickReplies, setQuickReplies] = useState([]);
  const [showQuickReplies, setShowQuickReplies] = useState(false);
  const [agents, setAgents] = useState([]);
  const [assignedFilter, setAssignedFilter] = useState('');

  useEffect(() => {
    authFetch('/api/v1/auth/users').then(r => r.ok ? r.json() : []).then(setAgents).catch(() => {});
  }, []);
  const [loading, setLoading] = useState(true);
  const [allCategories, setAllCategories] = useState([]);
  const [activeTag, setActiveTag] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);

  const doSearch = async () => {
    if (!searchQuery.trim()) { setSearchResults(null); return; }
    setSearching(true);
    try {
      const resp = await fetch(`/api/v1/dashboard/conversations/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchResults(await resp.json());
    } catch (e) { console.error(e); }
    setSearching(false);
  };

  const highlightMatch = (text, query) => {
    if (!query) return text;
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return text;
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + query.length);
    const after = text.slice(idx + query.length);
    return (
      <>{before}<span style={{ background: '#fef08a', fontWeight: 600 }}>{match}</span>{after}</>
    );
  };

  useEffect(() => {
    fetch('/api/v1/categories/').then(r => r.json()).then(setAllCategories).catch(() => {});
    resetUnread();
  }, []);

  const loadConversations = async () => {
    try {
      let params = activeTag ? `?tag=${activeTag}` : '';
      if (assignedFilter) params += `${params ? '&' : '?'}assigned_to=${assignedFilter}`;
      const resp = await fetch(`/api/v1/dashboard/conversations/${params}`);
      const data = await resp.json();
      setConversations(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 10000);
    return () => clearInterval(interval);
  }, [activeTag, assignedFilter]);

  const openDetail = async (id) => {
    setSelected(id);
    try {
      const resp = await fetch(`/api/v1/dashboard/conversations/${id}`);
      const data = await resp.json();
      setDetail(data);
      const csatResp = await fetch(`/api/v1/csat/conversation/${id}`);
      setCsatData(await csatResp.json());
      fetch('/api/v1/quick-replies/').then(r => r.json()).then(setQuickReplies).catch(() => {});
    } catch (e) { console.error(e); }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>{t('conversations_title')}</h1>
      <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '2rem' }}>
        {t('conversations_subtitle')}
      </p>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button onClick={() => setAssignedFilter('')} style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: '9999px', background: !assignedFilter ? '#000' : '#fff', color: !assignedFilter ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>All</button>
        <button onClick={() => setAssignedFilter(getUser()?.id || '')} style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: '9999px', background: assignedFilter === getUser()?.id ? '#000' : '#fff', color: assignedFilter === getUser()?.id ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer' }}>{t('conv_my_conversations')}</button>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder={t('conversations_search')}
          value={searchQuery}
          onChange={(e) => { setSearchQuery(e.target.value); if (!e.target.value) setSearchResults(null); }}
          onKeyDown={(e) => { if (e.key === 'Enter') doSearch(); }}
          style={{
            flex: 1, padding: '0.5rem 1rem', fontSize: '0.875rem',
            border: '1px solid #e5e7eb', borderRadius: '9999px', outline: 'none',
          }}
        />
        <button
          onClick={doSearch}
          disabled={searching}
          style={{
            padding: '0.5rem 1rem', background: '#000', color: '#fff',
            border: 'none', borderRadius: '9999px', fontSize: '0.875rem',
            cursor: searching ? 'wait' : 'pointer', opacity: searching ? 0.5 : 1,
          }}
        >{searching ? 'Searching...' : t('conversations_search_btn')}</button>
        {searchResults && (
          <button
            onClick={() => { setSearchResults(null); setSearchQuery(''); }}
            style={{
              padding: '0.5rem 1rem', background: '#fff', color: '#374151',
              border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer',
            }}
          >{t('conversations_clear')}</button>
        )}
      </div>

      {allCategories.length > 0 && (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <button
            onClick={() => setActiveTag('')}
            style={{
              fontSize: '0.75rem', padding: '4px 12px', borderRadius: '9999px',
              background: !activeTag ? '#000' : '#fff', color: !activeTag ? '#fff' : '#374151',
              border: '1px solid #e5e7eb', cursor: 'pointer',
            }}
          >All</button>
          {allCategories.map((c) => (
            <button
              key={c.id}
              onClick={() => setActiveTag(activeTag === c.slug ? '' : c.slug)}
              style={{
                fontSize: '0.75rem', padding: '4px 12px', borderRadius: '9999px',
                background: activeTag === c.slug ? c.color : '#fff',
                color: activeTag === c.slug ? '#fff' : '#374151',
                border: '1px solid #e5e7eb', cursor: 'pointer',
              }}
            >{c.name}</button>
          ))}
        </div>
      )}

      {searchResults ? (
        <div>
          <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '1rem' }}>
            {t('conversations_found')} "{searchResults.query}" {t('conversations_in')} {searchResults.total_conversations} {t('conversations_conversations')}
          </div>
          {searchResults.results.map((r) => (
            <div
              key={r.conversation_id}
              onClick={() => openDetail(r.conversation_id)}
              style={{
                padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem',
                marginBottom: '0.75rem', cursor: 'pointer', background: '#fff',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                  {r.channel === 'instagram' ? '📷' : '💬'} {r.sender_id.slice(0, 12)}...
                </span>
                <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                  {r.total_matches} match(es)
                </span>
              </div>
              {r.matching_messages.slice(0, 2).map((m, i) => (
                <div key={i} style={{
                  padding: '0.5rem', background: m.role === 'user' ? '#f3f4f6' : '#eff6ff',
                  borderRadius: '0.375rem', marginBottom: '0.25rem', fontSize: '0.8rem',
                }}>
                  <span style={{ fontSize: '0.65rem', color: '#6b7280' }}>
                    {m.role === 'user' ? 'CUSTOMER' : 'AI'}:
                  </span>{' '}
                  {highlightMatch(m.content, searchResults.query)}
                </div>
              ))}
            </div>
          ))}
        </div>
      ) : loading ? (
        <div style={{ color: '#9ca3af' }}>Loading...</div>
      ) : conversations.length === 0 ? (
        <div style={{ color: '#9ca3af', padding: '3rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.75rem' }}>
          No conversations yet. When customers DM your Instagram, they will appear here.
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '2rem' }}>
          {/* List */}
          <div style={{ flex: '1', maxWidth: '500px' }}>
            {conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => openDetail(c.id)}
                style={{
                  padding: '1rem',
                  border: '1px solid',
                  borderColor: selected === c.id ? '#000' : '#e5e7eb',
                  borderRadius: '0.75rem',
                  marginBottom: '0.75rem',
                  cursor: 'pointer',
                  background: '#fff',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.875rem' }}>
                      {c.channel === 'instagram' ? '📷' : '💬'} {c.sender_id.slice(0, 12)}...
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
                      {c.message_count} messages · {new Date(c.last_message_at).toLocaleString()}
                    </div>
                  </div>
                  <StageBadge stage={c.stage} />
                </div>
                <ScoreGauge score={c.intent_score} />
                {c.categories && c.categories.length > 0 && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {c.categories.map((slug) => {
                      const cat = allCategories.find(x => x.slug === slug);
                      if (!cat) return null;
                      return (
                        <span key={slug} style={{
                          fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px',
                          background: cat.color + '20', color: cat.color, fontWeight: 500,
                        }}>{cat.name}</span>
                      );
                    })}
                  </div>
                )}
                {c.signals && c.signals.length > 0 && (
                  <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {c.signals.slice(0, 3).map((s, i) => (
                      <span key={i} style={{ fontSize: '0.7rem', padding: '2px 6px', background: '#f3f4f6', borderRadius: '4px', color: '#4b5563' }}>
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Detail */}
          <div style={{ flex: '1.3' }}>
            {!detail ? (
              <div style={{ color: '#9ca3af', padding: '2rem', textAlign: 'center' }}>
                Select a conversation to view details
              </div>
            ) : (
              <div style={{ border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#fff', padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.125rem', fontWeight: 600 }}>Details</h2>
                  <StageBadge stage={detail.stage} />
                </div>

                {/* Assignment & Mode */}
                <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px' }}>{t('conv_assigned_to')}</div>
                    <select value={detail.assigned_to || ''} onChange={async (e) => { await authFetch(`/api/v1/conversations/${detail.id}/assign`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ agent_id: e.target.value }) }); openDetail(detail.id); }} style={{ width: '100%', padding: '4px 8px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.375rem', outline: 'none' }}>
                      <option value="">{t('conv_unassigned')}</option>
                      {agents.map(a => <option key={a.id} value={a.id}>{a.display_name} ({a.role})</option>)}
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px' }}>{t('conv_response_mode')}</div>
                    <select value={detail.response_mode || 'ai_auto'} onChange={async (e) => { await authFetch(`/api/v1/conversations/${detail.id}/set-mode`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode: e.target.value }) }); openDetail(detail.id); }} style={{ width: '100%', padding: '4px 8px', fontSize: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '0.375rem', outline: 'none', background: detail.response_mode === 'human_only' ? '#fef2f2' : detail.response_mode === 'ai_suggest' ? '#eff6ff' : '#f0fdf4' }}>
                      <option value="ai_auto">{t('conv_ai_auto')}</option>
                      <option value="ai_suggest">{t('conv_ai_suggest')}</option>
                      <option value="human_only">{t('conv_human_only')}</option>
                    </select>
                  </div>
                </div>

                {detail.escalated && (
                  <div style={{ padding: '0.5rem 0.75rem', background: '#fef3c7', borderRadius: '0.5rem', fontSize: '0.8rem', color: '#92400e', marginBottom: '1rem' }}>
                    {t('conv_escalated')}: {detail.escalation_reason}
                  </div>
                )}

                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>INTENT SCORE</div>
                  <ScoreGauge score={detail.intent_score} />
                  <div style={{ fontSize: '0.875rem', color: '#374151', marginTop: '0.75rem' }}>
                    {detail.score_breakdown}
                  </div>
                </div>

                {detail.signals && detail.signals.length > 0 && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>SIGNALS</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {detail.signals.map((s, i) => (
                        <span key={i} style={{ fontSize: '0.75rem', padding: '4px 10px', background: '#f3f4f6', borderRadius: '9999px', color: '#374151' }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginBottom: '1.5rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>NEXT ACTION</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>
                    {detail.next_action.replace(/_/g, ' ')}
                  </div>
                </div>

                {csatData && csatData.has_rating && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px' }}>{t('csat_customer_rating')}</div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {[1, 2, 3, 4, 5].map(s => (
                        <span key={s} style={{ fontSize: '1.25rem' }}>
                          {s <= csatData.rating ? '\u2B50' : '\u2606'}
                        </span>
                      ))}
                      <span style={{ marginLeft: '8px', fontSize: '0.875rem', fontWeight: 600 }}>
                        {csatData.rating}/5
                      </span>
                    </div>
                    {csatData.feedback && (
                      <div style={{ fontSize: '0.8rem', color: '#374151', marginTop: '4px' }}>
                        "{csatData.feedback}"
                      </div>
                    )}
                  </div>
                )}

                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                      CONVERSATION ({detail.messages?.length || 0} msgs)
                    </div>
                    <button
                      onClick={() => {
                        window.open(`/api/v1/dashboard/conversations/${detail.id}/export-pdf`, '_blank');
                      }}
                      style={{
                        padding: '3px 10px', fontSize: '0.7rem', background: '#fff',
                        border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
                        color: '#374151',
                      }}
                    >Export PDF</button>
                    <button
                      onClick={() => setShowQuickReplies(!showQuickReplies)}
                      style={{
                        padding: '3px 10px', fontSize: '0.7rem', background: showQuickReplies ? '#000' : '#fff',
                        color: showQuickReplies ? '#fff' : '#374151',
                        border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer',
                      }}
                    >{t('qr_button')}</button>
                  </div>
                  {showQuickReplies && quickReplies.length > 0 && (
                    <div style={{ marginBottom: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.75rem', maxHeight: '200px', overflowY: 'auto' }}>
                      {quickReplies.map((qr) => (
                        <div
                          key={qr.id}
                          onClick={async () => {
                            navigator.clipboard.writeText(qr.content);
                            await fetch(`/api/v1/quick-replies/${qr.id}/use`, { method: 'POST' });
                            alert('Copied to clipboard: ' + qr.title);
                          }}
                          style={{ padding: '8px', borderBottom: '1px solid #f3f4f6', cursor: 'pointer', fontSize: '0.8rem' }}
                          onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          <div style={{ fontWeight: 600, marginBottom: '2px' }}>{qr.title}</div>
                          <div style={{ color: '#6b7280', fontSize: '0.75rem' }}>{qr.content.slice(0, 100)}{qr.content.length > 100 ? '...' : ''}</div>
                        </div>
                      ))}
                    </div>
                  )}
                  {detail.pending_reply && (
                    <div style={{ marginBottom: '1rem', padding: '1rem', border: '2px solid #3b82f6', borderRadius: '0.5rem', background: '#eff6ff' }}>
                      <div style={{ fontSize: '0.75rem', color: '#2563eb', fontWeight: 600, marginBottom: '0.5rem' }}>{t('conv_pending_reply')}</div>
                      <textarea id="pending-reply-text" defaultValue={detail.pending_reply} rows={3} style={{ width: '100%', padding: '8px', border: '1px solid #bfdbfe', borderRadius: '0.375rem', fontSize: '0.85rem', outline: 'none', resize: 'vertical', marginBottom: '0.5rem', boxSizing: 'border-box' }} />
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button onClick={async () => { const text = document.getElementById('pending-reply-text').value; await authFetch(`/api/v1/conversations/${detail.id}/approve-reply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, product_ids: detail.pending_product_ids }) }); openDetail(detail.id); }} style={{ padding: '6px 16px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>{t('conv_approve_send')}</button>
                        <button onClick={async () => { await authFetch(`/api/v1/conversations/${detail.id}/approve-reply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: detail.pending_reply, product_ids: detail.pending_product_ids }) }); openDetail(detail.id); }} style={{ padding: '6px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>{t('conv_send_as_is')}</button>
                        <button onClick={async () => { await authFetch(`/api/v1/conversations/${detail.id}/set-mode`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode: 'human_only' }) }); openDetail(detail.id); }} style={{ padding: '6px 16px', background: '#fff', color: '#dc2626', border: '1px solid #fca5a5', borderRadius: '9999px', fontSize: '0.8rem', cursor: 'pointer' }}>{t('conv_discard_manual')}</button>
                      </div>
                    </div>
                  )}
                  <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '0.5rem', padding: '0.75rem' }}>
                    {(detail.messages || []).map((m, i) => (
                      <div key={i} style={{
                        marginBottom: '0.75rem',
                        padding: '0.5rem 0.75rem',
                        borderRadius: '0.5rem',
                        background: m.role === 'user' ? '#f3f4f6' : '#eff6ff',
                        fontSize: '0.875rem',
                      }}>
                        <div style={{ fontSize: '0.7rem', color: '#6b7280', marginBottom: '2px' }}>
                          {m.role === 'user' ? 'CUSTOMER' : 'AI'}
                        </div>
                        {m.content}
                      </div>
                    ))}
                  </div>
                  {(detail.response_mode === 'human_only' || detail.response_mode === 'ai_suggest') && (
                    <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
                      <input type="text" id="manual-reply-input" placeholder={t('conv_type_reply')} onKeyDown={async (e) => { if (e.key === 'Enter') { const text = e.target.value.trim(); if (!text) return; await authFetch(`/api/v1/conversations/${detail.id}/send-manual`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) }); e.target.value = ''; openDetail(detail.id); } }} style={{ flex: 1, padding: '8px 14px', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.85rem', outline: 'none' }} />
                      <button onClick={async () => { const input = document.getElementById('manual-reply-input'); const text = input.value.trim(); if (!text) return; await authFetch(`/api/v1/conversations/${detail.id}/send-manual`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) }); input.value = ''; openDetail(detail.id); }} style={{ padding: '8px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer' }}>{t('conv_send')}</button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
