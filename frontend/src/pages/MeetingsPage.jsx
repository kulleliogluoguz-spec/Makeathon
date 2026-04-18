import { useState, useEffect } from 'react';
import { t } from '../lib/i18n';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const STATUS_COLORS = {
  scheduled: '#3b82f6',
  completed: '#10b981',
  cancelled: '#94a3b8',
  no_show: '#ef4444',
};
const CHANNEL_ICONS = {
  linkedin: '💼',
  instagram: '📷',
  messenger: '💬',
  telegram: '✈️',
  phone: '📞',
  livechat: '💻',
};

export default function MeetingsPage() {
  const [meetings, setMeetings] = useState([]);
  const [selectedMeeting, setSelectedMeeting] = useState(null);
  const [currentMonth, setCurrentMonth] = useState(new Date());

  const load = async () => {
    const m = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}`;
    try {
      const resp = await fetch(`/api/v1/meetings/?month=${m}`);
      if (resp.ok) setMeetings(await resp.json());
    } catch (e) {}
  };

  useEffect(() => { load(); }, [currentMonth]);

  const getDaysInMonth = (date) => new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  const getFirstDayOfWeek = (date) => new Date(date.getFullYear(), date.getMonth(), 1).getDay();

  const daysInMonth = getDaysInMonth(currentMonth);
  const firstDay = getFirstDayOfWeek(currentMonth);

  const getMeetingsForDay = (day) => {
    const dateStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    return meetings.filter(m => m.scheduled_date && m.scheduled_date.startsWith(dateStr));
  };

  const prevMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  const nextMonth = () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Meetings</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Scheduled meetings from AI outreach calls</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button onClick={prevMonth} style={{ padding: '6px 12px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.5rem', cursor: 'pointer' }}>←</button>
          <span style={{ fontWeight: 600, fontSize: '1rem', minWidth: '150px', textAlign: 'center' }}>
            {currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </span>
          <button onClick={nextMonth} style={{ padding: '6px 12px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.5rem', cursor: 'pointer' }}>→</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selectedMeeting ? '1fr 1fr' : '1fr', gap: '1.5rem' }}>
        {/* Calendar */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '1px' }}>
            {DAYS.map(d => (
              <div key={d} style={{ padding: '8px', textAlign: 'center', fontSize: '0.75rem', fontWeight: 600, color: '#6b7280' }}>{d}</div>
            ))}
            {Array.from({ length: firstDay }, (_, i) => (
              <div key={`empty-${i}`} style={{ padding: '8px' }} />
            ))}
            {Array.from({ length: daysInMonth }, (_, i) => {
              const day = i + 1;
              const dayMeetings = getMeetingsForDay(day);
              const isToday = new Date().getDate() === day && new Date().getMonth() === currentMonth.getMonth() && new Date().getFullYear() === currentMonth.getFullYear();
              return (
                <div
                  key={day}
                  onClick={() => { if (dayMeetings.length > 0) setSelectedMeeting(dayMeetings[0]); }}
                  style={{
                    padding: '6px', minHeight: '70px', border: '1px solid #f3f4f6',
                    background: isToday ? '#eff6ff' : dayMeetings.length > 0 ? '#f0fdf4' : '#fff',
                    cursor: dayMeetings.length > 0 ? 'pointer' : 'default',
                    borderRadius: '4px',
                  }}
                >
                  <div style={{ fontSize: '0.8rem', fontWeight: isToday ? 700 : 400, color: isToday ? '#2563eb' : '#374151', marginBottom: '4px' }}>{day}</div>
                  {dayMeetings.map((m, mi) => (
                    <div key={mi} onClick={(e) => { e.stopPropagation(); setSelectedMeeting(m); }}
                      style={{
                        fontSize: '0.65rem', padding: '2px 4px', borderRadius: '3px', marginBottom: '2px',
                        background: STATUS_COLORS[m.status] || '#3b82f6', color: '#fff',
                        cursor: 'pointer', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                      }}>
                      {new Date(m.scheduled_date).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })} {m.customer_name.split(' ')[0]}
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>

        {/* Meeting Report */}
        {selectedMeeting && (
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', maxHeight: '80vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 600 }}>{selectedMeeting.customer_name}</h2>
                <p style={{ fontSize: '0.85rem', color: '#374151' }}>{selectedMeeting.customer_title} at {selectedMeeting.customer_company}</p>
              </div>
              <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                <span style={{ fontSize: '0.7rem', padding: '3px 10px', borderRadius: '9999px', background: STATUS_COLORS[selectedMeeting.status] + '20', color: STATUS_COLORS[selectedMeeting.status], fontWeight: 600 }}>
                  {selectedMeeting.status}
                </span>
                <button onClick={() => setSelectedMeeting(null)} style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: '#6b7280' }}>×</button>
              </div>
            </div>

            {/* Meeting Info */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '1.5rem', fontSize: '0.8rem' }}>
              <div style={{ padding: '8px', background: '#f9fafb', borderRadius: '0.375rem' }}>
                <span style={{ color: '#6b7280' }}>Date: </span>
                <strong>{new Date(selectedMeeting.scheduled_date).toLocaleString()}</strong>
              </div>
              <div style={{ padding: '8px', background: '#f9fafb', borderRadius: '0.375rem' }}>
                <span style={{ color: '#6b7280' }}>Duration: </span>
                <strong>{selectedMeeting.duration_minutes} min ({selectedMeeting.meeting_type})</strong>
              </div>
              <div style={{ padding: '8px', background: '#f9fafb', borderRadius: '0.375rem' }}>
                <span style={{ color: '#6b7280' }}>Source: </span>
                <strong>{CHANNEL_ICONS[selectedMeeting.source_channel] || '📞'} {selectedMeeting.source_channel}</strong>
              </div>
              <div style={{ padding: '8px', background: '#f9fafb', borderRadius: '0.375rem' }}>
                <span style={{ color: '#6b7280' }}>Contact: </span>
                <strong>{selectedMeeting.initial_contact_method.replace(/_/g, ' ')}</strong>
              </div>
              <div style={{ padding: '8px', background: '#f9fafb', borderRadius: '0.375rem' }}>
                <span style={{ color: '#6b7280' }}>Deal Value: </span>
                <strong style={{ color: '#10b981' }}>{selectedMeeting.estimated_deal_value || 'TBD'}</strong>
              </div>
              <div style={{ padding: '8px', background: '#f9fafb', borderRadius: '0.375rem' }}>
                {selectedMeeting.customer_phone && <span>📞 {selectedMeeting.customer_phone} </span>}
                {selectedMeeting.customer_email && <span>📧 {selectedMeeting.customer_email}</span>}
              </div>
            </div>

            {/* Conversation Summary */}
            <section style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem', color: '#1e40af' }}>📋 Conversation Summary</h3>
              <p style={{ fontSize: '0.8rem', color: '#374151', lineHeight: 1.6 }}>{selectedMeeting.conversation_summary}</p>
            </section>

            {/* Recommended Approach */}
            <section style={{ marginBottom: '1.5rem', background: '#f0fdf4', padding: '1rem', borderRadius: '0.5rem' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem', color: '#065f46' }}>🎯 Recommended Approach</h3>
              <pre style={{ fontSize: '0.8rem', color: '#374151', lineHeight: 1.6, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{selectedMeeting.recommended_approach}</pre>
            </section>

            {/* Talking Points */}
            {selectedMeeting.talking_points && selectedMeeting.talking_points.length > 0 && (
              <section style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>💡 Key Talking Points</h3>
                {selectedMeeting.talking_points.map((point, i) => (
                  <div key={i} style={{ fontSize: '0.8rem', padding: '6px 0', borderBottom: '1px solid #f3f4f6', color: '#374151', display: 'flex', gap: '6px' }}>
                    <span style={{ color: '#3b82f6', fontWeight: 600 }}>{i + 1}.</span> {point}
                  </div>
                ))}
              </section>
            )}

            {/* Customer Interests */}
            <section style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>🛒 Customer Interests</h3>
              <p style={{ fontSize: '0.8rem', color: '#374151' }}>{selectedMeeting.customer_interests}</p>
            </section>

            {/* Risk Factors */}
            {selectedMeeting.risk_factors && (
              <section style={{ marginBottom: '1.5rem', background: '#fef2f2', padding: '1rem', borderRadius: '0.5rem' }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem', color: '#991b1b' }}>⚠️ Risk Factors</h3>
                <p style={{ fontSize: '0.8rem', color: '#7f1d1d' }}>{selectedMeeting.risk_factors}</p>
              </section>
            )}

            {/* Call Transcript */}
            {selectedMeeting.call_transcript && (
              <section style={{ marginBottom: '1rem' }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>📞 AI Call Transcript ({selectedMeeting.call_duration_seconds}s)</h3>
                <pre style={{ fontSize: '0.75rem', color: '#374151', lineHeight: 1.6, whiteSpace: 'pre-wrap', fontFamily: 'inherit', background: '#f9fafb', padding: '1rem', borderRadius: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
                  {selectedMeeting.call_transcript}
                </pre>
              </section>
            )}

            {/* Status update */}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              {['scheduled', 'completed', 'cancelled', 'no_show'].map(s => (
                <button key={s} onClick={async () => {
                  await fetch(`/api/v1/meetings/${selectedMeeting.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: s }),
                  });
                  load();
                  setSelectedMeeting({ ...selectedMeeting, status: s });
                }}
                  style={{
                    padding: '4px 12px', fontSize: '0.7rem', borderRadius: '9999px', cursor: 'pointer',
                    background: selectedMeeting.status === s ? STATUS_COLORS[s] : '#fff',
                    color: selectedMeeting.status === s ? '#fff' : STATUS_COLORS[s],
                    border: `1px solid ${STATUS_COLORS[s]}`,
                  }}>{s}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
