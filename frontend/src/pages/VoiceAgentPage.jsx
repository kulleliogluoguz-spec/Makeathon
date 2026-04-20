import { useState, useEffect, useRef } from 'react';
import { Conversation } from '@11labs/client';

export default function VoiceAgentPage() {
  const [isActive, setIsActive] = useState(false);
  const [status, setStatus] = useState('idle');
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const widgetRef = useRef(null);
  const filterIntervalRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const applyPhoneFilter = () => {
    // Find audio elements created by ElevenLabs SDK and apply phone filter
    const interval = setInterval(() => {
      const audioEls = document.querySelectorAll('audio');
      audioEls.forEach(el => {
        if (el.dataset.filtered) return;
        el.dataset.filtered = 'true';

        try {
          if (!window.__filterCtx) {
            window.__filterCtx = new (window.AudioContext || window.webkitAudioContext)();
          }
          const ctx = window.__filterCtx;
          const source = ctx.createMediaElementSource(el);

          // Telephone bandpass: 300Hz - 3400Hz
          const highpass = ctx.createBiquadFilter();
          highpass.type = 'highpass';
          highpass.frequency.value = 300;
          highpass.Q.value = 0.5;

          const lowpass = ctx.createBiquadFilter();
          lowpass.type = 'lowpass';
          lowpass.frequency.value = 3400;
          lowpass.Q.value = 0.5;

          // Compress like phone line
          const compressor = ctx.createDynamicsCompressor();
          compressor.threshold.value = -15;
          compressor.ratio.value = 3;

          // Slightly quieter (distant feel)
          const gain = ctx.createGain();
          gain.gain.value = 0.8;

          // Add very subtle noise/crackle
          const noiseGain = ctx.createGain();
          noiseGain.gain.value = 0.008;
          const noiseBuffer = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
          const noiseData = noiseBuffer.getChannelData(0);
          for (let i = 0; i < noiseData.length; i++) {
            noiseData[i] = (Math.random() * 2 - 1);
            if (i > 0) noiseData[i] = noiseData[i] * 0.1 + noiseData[i-1] * 0.9;
          }
          const noiseSource = ctx.createBufferSource();
          noiseSource.buffer = noiseBuffer;
          noiseSource.loop = true;
          noiseSource.connect(noiseGain);
          noiseGain.connect(ctx.destination);
          noiseSource.start();

          // Chain: source → highpass → lowpass → compressor → gain → speakers
          source.connect(highpass);
          highpass.connect(lowpass);
          lowpass.connect(compressor);
          compressor.connect(gain);
          gain.connect(ctx.destination);

          console.log('Phone filter applied to audio element');
        } catch(e) {
          console.log('Could not apply phone filter:', e);
        }
      });
    }, 500);

    // Stop checking after 30 seconds
    setTimeout(() => clearInterval(interval), 30000);

    return interval;
  };

  const startConversation = async () => {
    setIsActive(true);
    setStatus('connecting');

    // Subtle office background audio
    if (!window.__ambientAudio) {
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const gain = ctx.createGain();
        gain.gain.value = 0.25;
        gain.connect(ctx.destination);

        const bufferSize = ctx.sampleRate * 20;
        const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
        const data = buffer.getChannelData(0);

        // Gentle room tone
        for (let i = 0; i < bufferSize; i++) {
          data[i] = (Math.random() * 2 - 1) * 0.003;
          if (i > 0) data[i] = data[i] * 0.03 + data[i-1] * 0.97;
        }

        // Rare quiet keyboard clicks
        for (let j = 0; j < 8; j++) {
          const pos = Math.floor(Math.random() * (bufferSize - 200));
          for (let k = 0; k < 3; k++) {
            const clickPos = pos + k * Math.floor(Math.random() * 2000 + 1500);
            if (clickPos + 150 < bufferSize) {
              for (let s = 0; s < 150; s++) {
                data[clickPos + s] += (Math.random() * 2 - 1) * 0.002 * Math.exp(-s * 0.1);
              }
            }
          }
        }

        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.loop = true;
        source.connect(gain);
        source.start();
        window.__ambientAudio = { ctx, gain, source };
      } catch(e) {}
    } else {
      // Resume if already exists
      window.__ambientAudio.gain.gain.linearRampToValueAtTime(0.25, window.__ambientAudio.ctx.currentTime + 0.5);
    }
    await initConversation();

    // Apply telephone filter to make it sound like a real phone call
    filterIntervalRef.current = applyPhoneFilter();
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
    if (filterIntervalRef.current) clearInterval(filterIntervalRef.current);
    if (widgetRef.current) {
      await widgetRef.current.endSession();
    }
    if (window.__ambientAudio) {
      window.__ambientAudio.gain.gain.linearRampToValueAtTime(0, window.__ambientAudio.ctx.currentTime + 1);
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
