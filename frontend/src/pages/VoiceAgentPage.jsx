import { useState, useEffect, useRef } from 'react';
import { Conversation } from '@11labs/client';

export default function VoiceAgentPage() {
  const [isActive, setIsActive] = useState(false);
  const [status, setStatus] = useState('idle');
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const widgetRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startConversation = async () => {
    setIsActive(true);
    setStatus('connecting');
    await initConversation();
  };

  const initConversation = async () => {
    try {
      const conversation = await Conversation.startSession({
        agentId: 'agent_6701kpnen0hjfbnrn8arhahca07v',
        onConnect: () => {
          setStatus('connected');
          console.log('ElevenLabs connected');
        },
        onDisconnect: () => {
          setStatus('ended');
          setIsActive(false);
          console.log('ElevenLabs disconnected');
        },
        onMessage: (message) => {
          if (message.source === 'user') {
            setMessages(prev => [...prev, { role: 'user', text: message.message }]);
          } else if (message.source === 'ai') {
            setMessages(prev => [...prev, { role: 'ai', text: message.message }]);
          }
        },
        onModeChange: (mode) => {
          if (mode.mode === 'listening') setStatus('listening');
          else if (mode.mode === 'speaking') setStatus('speaking');
          else if (mode.mode === 'thinking') setStatus('thinking');
        },
        onError: (error) => {
          console.error('ElevenLabs error:', error);
          setStatus('error');
        },
      });

      widgetRef.current = conversation;
    } catch (e) {
      console.error('Failed to start conversation:', e);
      setStatus('error');

      // Fallback: open in new tab
      window.open('https://elevenlabs.io/app/talk-to?agent_id=agent_6701kpnen0hjfbnrn8arhahca07v&branch_id=agtbrch_4501kpnen1d1fd2r1j0vww1sm7hd', '_blank');
      setIsActive(false);
    }
  };

  const endConversation = async () => {
    if (widgetRef.current) {
      await widgetRef.current.endSession();
    }
    setIsActive(false);
    setStatus('idle');
  };

  const statusText = {
    idle: 'Click to start a conversation',
    connecting: 'Connecting...',
    connected: 'Connected — start talking',
    listening: 'Listening...',
    thinking: 'Thinking...',
    speaking: 'Speaking...',
    ended: 'Conversation ended',
    error: 'Connection error',
  };

  const statusColor = {
    idle: '#6b7280',
    connecting: '#f59e0b',
    connected: '#10b981',
    listening: '#ef4444',
    thinking: '#3b82f6',
    speaking: '#10b981',
    ended: '#6b7280',
    error: '#ef4444',
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '700px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Voice Agent</h1>
        <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Talk to the AI sales agent in real-time</p>
      </div>

      {/* Mic/Call Button */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
        {!isActive ? (
          <button onClick={startConversation} style={{
            width: '120px', height: '120px', borderRadius: '50%',
            background: '#f0fdf4', border: '3px solid #10b981',
            cursor: 'pointer', fontSize: '2.5rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.3s',
            boxShadow: '0 0 0 0 rgba(16,185,129,0.3)',
          }}
            onMouseEnter={(e) => e.target.style.boxShadow = '0 0 0 12px rgba(16,185,129,0.15)'}
            onMouseLeave={(e) => e.target.style.boxShadow = '0 0 0 0 rgba(16,185,129,0.3)'}
          >
            📞
          </button>
        ) : (
          <button onClick={endConversation} style={{
            width: '120px', height: '120px', borderRadius: '50%',
            background: status === 'listening' ? '#fef2f2' : status === 'speaking' ? '#f0fdf4' : status === 'thinking' ? '#eff6ff' : '#f9fafb',
            border: `3px solid ${statusColor[status] || '#e5e7eb'}`,
            cursor: 'pointer', fontSize: '2.5rem',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.3s',
            animation: status === 'listening' ? 'pulse 1.5s ease-in-out infinite' : 'none',
          }}>
            {status === 'listening' ? '🎙️' : status === 'speaking' ? '🔊' : status === 'thinking' ? '🤔' : '📞'}
          </button>
        )}
      </div>
      <style>{`@keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.3); } 50% { box-shadow: 0 0 0 15px rgba(239,68,68,0); } }`}</style>

      {/* Status */}
      <div style={{ textAlign: 'center', fontSize: '0.9rem', color: statusColor[status], marginBottom: '1.5rem', fontWeight: 500 }}>
        {statusText[status]}
      </div>

      {/* Conversation Transcript */}
      <div style={{
        background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem',
        padding: '1rem', minHeight: '300px', maxHeight: '500px', overflowY: 'auto',
      }}>
        {messages.length === 0 && (
          <div style={{ color: '#9ca3af', textAlign: 'center', padding: '3rem 1rem', fontSize: '0.9rem' }}>
            {isActive ? 'Start talking — the agent is listening...' : 'Click the phone button to start a conversation'}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            marginBottom: '1rem', display: 'flex',
            justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              maxWidth: '80%', padding: '10px 14px', borderRadius: '12px',
              background: m.role === 'user' ? '#000' : '#f3f4f6',
              color: m.role === 'user' ? '#fff' : '#1f2937',
              fontSize: '0.9rem', lineHeight: 1.5,
            }}>
              {m.text}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* End/Reset */}
      <div style={{ textAlign: 'center', marginTop: '1rem', display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
        {isActive && (
          <button onClick={endConversation} style={{
            padding: '8px 20px', background: '#ef4444', color: '#fff',
            border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer',
          }}>End Call</button>
        )}
        {messages.length > 0 && (
          <button onClick={() => setMessages([])} style={{
            padding: '8px 20px', background: '#fff', color: '#374151',
            border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer',
          }}>Clear Transcript</button>
        )}
      </div>
    </div>
  );
}
