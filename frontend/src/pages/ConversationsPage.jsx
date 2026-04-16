import { useState, useEffect } from 'react';

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
  const [loading, setLoading] = useState(true);

  const loadConversations = async () => {
    try {
      const resp = await fetch('/api/v1/dashboard/conversations/');
      const data = await resp.json();
      setConversations(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => {
    loadConversations();
    const interval = setInterval(loadConversations, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const openDetail = async (id) => {
    setSelected(id);
    try {
      const resp = await fetch(`/api/v1/dashboard/conversations/${id}`);
      const data = await resp.json();
      setDetail(data);
    } catch (e) { console.error(e); }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>Conversations</h1>
      <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '2rem' }}>
        Live view of all customer conversations with intent scoring
      </p>

      {loading ? (
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

                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>CONVERSATION ({detail.messages?.length || 0} msgs)</div>
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
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
