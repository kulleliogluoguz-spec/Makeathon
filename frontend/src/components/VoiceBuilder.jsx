import { useState, useEffect, useRef, useCallback } from 'react'
import { Mic, X, Minus, Keyboard, Volume2, VolumeX, Loader2, Check, Sparkles } from 'lucide-react'

const API = '/api/v1/voice-builder'

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) throw new Error('Request failed')
  return res.json()
}

// status: idle | speaking | listening | transcribing | processing | extracted | done
export default function VoiceBuilder({ personaId, persona, onFieldsExtracted }) {
  const [open, setOpen] = useState(false)
  const [minimized, setMinimized] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [question, setQuestion] = useState(null)
  const [step, setStep] = useState(1)
  const [total, setTotal] = useState(15)
  const [status, setStatus] = useState('idle')
  const [transcript, setTranscript] = useState('')
  const [extracted, setExtracted] = useState(null)
  const [lang, setLang] = useState('en')
  const [muted, setMuted] = useState(false)
  const [showTextInput, setShowTextInput] = useState(false)
  const [textInput, setTextInput] = useState('')
  const [completed, setCompleted] = useState(false)

  const sessionRef = useRef(null)
  const questionRef = useRef(null)
  const recorderRef = useRef(null)
  const audioRef = useRef(null)
  const chunksRef = useRef([])

  const setQuestionSync = (q) => { questionRef.current = q; setQuestion(q) }
  const setSessionSync = (s) => { sessionRef.current = s; setSessionId(s) }

  // --- Recording via MediaRecorder + Whisper STT ---
  const stopRecording = useCallback(() => {
    if (recorderRef.current && recorderRef.current.state === 'recording') {
      recorderRef.current.stop()
    }
  }, [])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      chunksRef.current = []

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        if (blob.size < 100) { setStatus('idle'); return }

        // Transcribe via Whisper
        setStatus('transcribing')
        try {
          const formData = new FormData()
          formData.append('file', blob, 'audio.webm')
          formData.append('language', lang)
          const resp = await fetch('/api/v1/stt/transcribe', { method: 'POST', body: formData })
          if (!resp.ok) throw new Error()
          const { text } = await resp.json()
          setTranscript(text)
          processAnswer(text)
        } catch {
          setStatus('idle')
        }
      }

      recorderRef.current = recorder
      recorder.start()
      setStatus('listening')
      setTranscript('')
    } catch {
      setStatus('idle')
    }
  }, [lang])

  // --- TTS via ElevenLabs ---
  const speakQuestion = useCallback(async (text) => {
    if (muted) { setStatus('idle'); return }
    setStatus('speaking')
    try {
      const voiceId = persona?.voice_id || 'EXAVITQu4vr4xnSDxMaL' // fallback: Sarah
      const resp = await fetch('/api/v1/tts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          voice_id: voiceId,
          model_id: persona?.voice_model || 'eleven_turbo_v2',
          stability: persona?.voice_stability ?? 0.5,
          similarity_boost: persona?.voice_similarity ?? 0.75,
          style: persona?.voice_style ?? 0.0,
        }),
      })
      if (!resp.ok) throw new Error()
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { setStatus('idle'); URL.revokeObjectURL(url); audioRef.current = null }
      audio.onerror = () => { setStatus('idle'); audioRef.current = null }
      audio.play()
    } catch {
      // Fallback to browser TTS if ElevenLabs fails
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        const utterance = new SpeechSynthesisUtterance(text)
        utterance.lang = lang === 'tr' ? 'tr-TR' : 'en-US'
        utterance.onend = () => setStatus('idle')
        utterance.onerror = () => setStatus('idle')
        window.speechSynthesis.speak(utterance)
      } else {
        setStatus('idle')
      }
    }
  }, [muted, persona, lang])

  // --- Session management ---
  const startSession = useCallback(async () => {
    const data = await api('/start', {
      method: 'POST',
      body: JSON.stringify({ persona_id: personaId, language: lang }),
    })
    setSessionSync(data.session_id)
    setQuestionSync(data.first_question)
    setStep(data.current_step)
    setTotal(data.total_questions)
    setCompleted(false)
    setExtracted(null)
    speakQuestion(data.first_question.text)
  }, [personaId, lang, speakQuestion])

  const handleOpen = useCallback(() => {
    setOpen(true)
    setMinimized(false)
    if (!sessionRef.current) startSession()
  }, [startSession])

  // --- Process answer via backend ---
  const processAnswer = useCallback(async (text) => {
    const sid = sessionRef.current
    const q = questionRef.current
    if (!sid || !q) return
    setStatus('processing')
    try {
      const data = await api('/answer', {
        method: 'POST',
        body: JSON.stringify({ session_id: sid, question_id: q.id, transcript: text }),
      })

      if (data.clarification_needed) {
        setQuestionSync(data.clarification_question)
        setStep(data.current_step)
        speakQuestion(data.clarification_question.text)
        return
      }

      if (data.extracted_fields && Object.keys(data.extracted_fields).length > 0) {
        setExtracted(data.extracted_fields)
        onFieldsExtracted(data.extracted_fields)
        setStatus('extracted')
        if (q.field_group) {
          setTimeout(() => {
            const el = document.getElementById(`section-${q.field_group}`)
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }, 300)
        }
      }

      setTimeout(() => {
        if (data.completed || !data.next_question) {
          setCompleted(true)
          setStatus('done')
          setQuestionSync(null)
        } else {
          setQuestionSync(data.next_question)
          setStep(data.current_step)
          setExtracted(null)
          speakQuestion(data.next_question.text)
        }
      }, 2000)
    } catch {
      setStatus('idle')
    }
  }, [onFieldsExtracted, speakQuestion])

  const handleSkip = useCallback(async () => {
    const sid = sessionRef.current
    const q = questionRef.current
    if (!sid || !q) return
    stopRecording()
    const data = await api('/skip', {
      method: 'POST',
      body: JSON.stringify({ session_id: sid, question_id: q.id }),
    })
    if (data.completed || !data.next_question) {
      setCompleted(true)
      setStatus('done')
      setQuestionSync(null)
    } else {
      setQuestionSync(data.next_question)
      setStep(data.current_step)
      setExtracted(null)
      speakQuestion(data.next_question.text)
    }
  }, [stopRecording, speakQuestion])

  const handleTextSubmit = useCallback(() => {
    if (!textInput.trim()) return
    const text = textInput.trim()
    setTranscript(text)
    setTextInput('')
    setShowTextInput(false)
    processAnswer(text)
  }, [textInput, processAnswer])

  const handleMicToggle = useCallback(() => {
    if (status === 'listening') {
      stopRecording()
    } else if (status === 'idle') {
      startRecording()
    }
  }, [status, startRecording, stopRecording])

  const handleClose = () => {
    stopRecording()
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
    setOpen(false)
    setMinimized(false)
  }

  const progressPct = ((step - 1) / total) * 100

  // --- Floating button (collapsed) ---
  if (!open) {
    return (
      <button
        onClick={handleOpen}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-black text-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-800 transition-all group"
        title="Build persona with voice"
      >
        <Mic size={22} strokeWidth={1.5} />
        <span className="absolute -top-8 right-0 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          Build persona with voice
        </span>
        <span className="absolute inset-0 rounded-full border-2 border-black animate-ping opacity-20" />
      </button>
    )
  }

  // --- Minimized pill ---
  if (minimized) {
    return (
      <button
        onClick={() => setMinimized(false)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2 bg-black text-white rounded-full shadow-lg text-sm font-medium hover:bg-gray-800"
      >
        <Mic size={14} /> Step {step}/{total}
      </button>
    )
  }

  // --- Expanded panel ---
  return (
    <div className="fixed bottom-6 right-6 z-50 w-[380px] bg-white rounded-xl shadow-xl border border-gray-200 flex flex-col" style={{ maxHeight: '500px' }}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-900">Voice Persona Builder</h3>
          <div className="flex items-center gap-1">
            <button onClick={() => setMuted(!muted)} className="p-1 text-gray-400 hover:text-gray-600" title={muted ? 'Unmute agent' : 'Mute agent'}>
              {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
            </button>
            <button onClick={() => setMinimized(true)} className="p-1 text-gray-400 hover:text-gray-600"><Minus size={14} /></button>
            <button onClick={handleClose} className="p-1 text-gray-400 hover:text-gray-600"><X size={14} /></button>
          </div>
        </div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-gray-500">Step {step} of {total}</span>
          <div className="flex items-center gap-1">
            {['en', 'tr'].map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className={`px-2 py-0.5 rounded text-[10px] font-medium ${lang === l ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500'}`}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full bg-gray-900 rounded-full transition-all duration-500" style={{ width: `${progressPct}%` }} />
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 px-4 py-4 overflow-y-auto min-h-[200px]">
        {completed ? (
          <div className="text-center py-6 space-y-4">
            <div className="w-12 h-12 bg-green-50 rounded-full flex items-center justify-center mx-auto">
              <Check size={24} strokeWidth={1.5} className="text-green-600" />
            </div>
            <div>
              <div className="text-sm font-semibold text-gray-900">Persona complete!</div>
              <div className="text-xs text-gray-500 mt-1">All fields have been filled from your answers.</div>
            </div>
            <div className="space-y-2">
              <button
                onClick={() => { onFieldsExtracted({ _generate: true }); handleClose() }}
                className="w-full py-2 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800 flex items-center justify-center gap-1.5"
              >
                <Sparkles size={14} /> Generate System Prompt
              </button>
              <button onClick={handleClose} className="w-full py-2 border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50">
                Review & Edit
              </button>
            </div>
          </div>
        ) : (
          <>
            {question && <p className="text-sm text-gray-800 leading-relaxed mb-4">{question.text}</p>}

            <div className="flex items-center gap-2 mb-3">
              {status === 'listening' && (
                <>
                  <span className="flex items-center gap-1.5 text-xs text-green-600">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" /> Listening...
                  </span>
                  <div className="flex items-end gap-0.5 h-4">
                    {[1,2,3,4].map((i) => (
                      <div key={i} className="w-1 bg-green-400 rounded-full animate-pulse" style={{ height: `${8 + Math.random() * 8}px`, animationDelay: `${i * 0.1}s` }} />
                    ))}
                  </div>
                </>
              )}
              {status === 'speaking' && (
                <span className="flex items-center gap-1.5 text-xs text-blue-600">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" /> Speaking...
                </span>
              )}
              {status === 'transcribing' && (
                <span className="flex items-center gap-1.5 text-xs text-purple-600">
                  <Loader2 size={12} className="animate-spin" /> Transcribing...
                </span>
              )}
              {status === 'processing' && (
                <span className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Loader2 size={12} className="animate-spin" /> Processing...
                </span>
              )}
              {status === 'extracted' && (
                <span className="flex items-center gap-1.5 text-xs text-green-600">
                  <Check size={12} /> Got it!
                </span>
              )}
            </div>

            {transcript && status !== 'extracted' && (
              <div className="text-xs text-gray-400 italic mb-3">"{transcript}"</div>
            )}

            {extracted && (
              <div className="bg-green-50 rounded-lg p-3 mb-3 space-y-1">
                {Object.entries(extracted).map(([key, val]) => {
                  const display = Array.isArray(val) ? val.join(', ') : typeof val === 'object' ? JSON.stringify(val).substring(0, 60) + '...' : String(val)
                  return (
                    <div key={key} className="flex items-center gap-1.5 text-xs">
                      <Check size={10} className="text-green-600 shrink-0" />
                      <span className="text-green-800 font-medium">{key.replace(/_/g, ' ')}:</span>
                      <span className="text-green-700 truncate">{display}</span>
                    </div>
                  )
                })}
              </div>
            )}

            {showTextInput && (
              <div className="flex gap-2 mb-3">
                <input
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleTextSubmit()}
                  placeholder="Type your answer..."
                  className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
                  autoFocus
                />
                <button onClick={handleTextSubmit} className="px-3 py-1.5 bg-black text-white rounded-lg text-sm">Send</button>
              </div>
            )}
          </>
        )}
      </div>

      {!completed && question && (
        <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={handleSkip} className="text-xs text-gray-500 hover:text-gray-700">Skip</button>
            <button onClick={() => setShowTextInput(!showTextInput)} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
              <Keyboard size={12} /> Type instead
            </button>
          </div>
          <button
            onClick={handleMicToggle}
            disabled={status === 'processing' || status === 'speaking' || status === 'extracted' || status === 'transcribing'}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
              status === 'listening'
                ? 'bg-red-500 text-white ring-4 ring-red-200 animate-pulse'
                : status === 'processing' || status === 'transcribing'
                ? 'bg-gray-200 text-gray-400'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {status === 'processing' || status === 'transcribing' ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <Mic size={20} strokeWidth={1.5} />
            )}
          </button>
        </div>
      )}
    </div>
  )
}
