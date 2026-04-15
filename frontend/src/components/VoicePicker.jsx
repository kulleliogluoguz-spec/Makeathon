import { useState, useEffect, useRef } from 'react'
import { Search, Play, Square, Check, Volume2 } from 'lucide-react'

export default function VoicePicker({ selectedVoiceId, voiceSettings, onVoiceSelect, onSettingsChange }) {
  const [voices, setVoices] = useState([])
  const [search, setSearch] = useState('')
  const [gender, setGender] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [playingId, setPlayingId] = useState(null)
  const [testPlaying, setTestPlaying] = useState(false)
  const audioRef = useRef(null)

  const settings = {
    model: voiceSettings?.model || 'eleven_turbo_v2',
    stability: voiceSettings?.stability ?? 0.5,
    similarity: voiceSettings?.similarity ?? 0.75,
    style: voiceSettings?.style ?? 0.0,
    speed: voiceSettings?.speed ?? 1.0,
  }

  useEffect(() => {
    const timeout = setTimeout(() => {
      setLoading(true)
      const params = new URLSearchParams()
      if (search) params.set('search', search)
      if (gender) params.set('gender', gender)
      if (category) params.set('category', category)
      fetch(`/api/v1/voices/?${params}`)
        .then((r) => r.json())
        .then((data) => { if (Array.isArray(data)) setVoices(data) })
        .catch(() => {})
        .finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(timeout)
  }, [search, gender, category])

  const playPreview = (previewUrl, voiceId) => {
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
    if (playingId === voiceId) { setPlayingId(null); return }
    const audio = new Audio(previewUrl)
    audioRef.current = audio
    setPlayingId(voiceId)
    audio.onended = () => { setPlayingId(null); audioRef.current = null }
    audio.onerror = () => { setPlayingId(null); audioRef.current = null }
    audio.play()
  }

  const testVoice = async () => {
    if (testPlaying) return
    if (!selectedVoiceId) return
    setTestPlaying(true)
    try {
      const resp = await fetch('/api/v1/tts/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: 'Hello! How can I help you today?',
          voice_id: selectedVoiceId,
          model_id: settings.model,
          stability: settings.stability,
          similarity_boost: settings.similarity,
          style: settings.style,
          speed: settings.speed,
        }),
      })
      if (!resp.ok) throw new Error()
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => { setTestPlaying(false); URL.revokeObjectURL(url) }
      audio.onerror = () => { setTestPlaying(false) }
      audio.play()
    } catch {
      setTestPlaying(false)
    }
  }

  const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-400'

  return (
    <div className="space-y-4">
      {/* Search & Filters */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search voices..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
          />
        </div>
        <select value={gender} onChange={(e) => setGender(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none">
          <option value="">All Genders</option>
          <option value="female">Female</option>
          <option value="male">Male</option>
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none">
          <option value="">All</option>
          <option value="premade">Premade</option>
          <option value="cloned">Cloned</option>
          <option value="generated">Generated</option>
        </select>
      </div>

      {/* Voice Grid */}
      {loading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Loading voices...</div>
      ) : voices.length === 0 ? (
        <div className="text-sm text-gray-400 py-8 text-center">No voices found. Check your ElevenLabs API key.</div>
      ) : (
        <div className="grid grid-cols-3 gap-2 max-h-[300px] overflow-y-auto pr-1">
          {voices.map((v) => {
            const isSelected = v.voice_id === selectedVoiceId
            return (
              <div
                key={v.voice_id}
                className={`p-3 rounded-lg border text-left transition-all ${
                  isSelected ? 'border-gray-900 bg-gray-50 ring-1 ring-gray-300' : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="text-xs font-semibold text-gray-900 truncate">{v.name}</div>
                <div className="text-[10px] text-gray-500 mt-0.5">
                  {[v.gender, v.age, v.accent].filter(Boolean).join(' · ') || v.category}
                </div>
                <div className="flex items-center gap-1.5 mt-2">
                  {v.preview_url && (
                    <button
                      onClick={() => playPreview(v.preview_url, v.voice_id)}
                      className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
                    >
                      {playingId === v.voice_id ? <Square size={8} /> : <Play size={8} />}
                      {playingId === v.voice_id ? 'Stop' : 'Play'}
                    </button>
                  )}
                  {isSelected ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-green-700 bg-green-50 rounded font-medium">
                      <Check size={8} /> Active
                    </span>
                  ) : (
                    <button
                      onClick={() => onVoiceSelect(v)}
                      className="px-2 py-0.5 text-[10px] text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
                    >
                      Select
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Voice Settings (shown when a voice is selected) */}
      {selectedVoiceId && (
        <div className="border border-gray-200 rounded-lg p-4 space-y-3">
          <div className="text-sm font-medium text-gray-700">Voice Settings</div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Model</label>
            <select
              value={settings.model}
              onChange={(e) => onSettingsChange({ voice_model: e.target.value })}
              className={inputCls}
            >
              <option value="eleven_turbo_v2">Turbo v2 (fast, conversational)</option>
              <option value="eleven_multilingual_v2">Multilingual v2 (highest quality)</option>
            </select>
          </div>
          {[
            { key: 'stability', label: 'Stability', field: 'voice_stability', min: 0, max: 1, step: 0.01 },
            { key: 'similarity', label: 'Similarity Boost', field: 'voice_similarity', min: 0, max: 1, step: 0.01 },
            { key: 'style', label: 'Style', field: 'voice_style', min: 0, max: 1, step: 0.01 },
            { key: 'speed', label: 'Speed', field: 'voice_speed', min: 0.5, max: 2, step: 0.1 },
          ].map((s) => (
            <div key={s.key} className="flex items-center gap-3">
              <label className="text-xs text-gray-500 w-28 shrink-0">{s.label}</label>
              <input
                type="range"
                min={s.min}
                max={s.max}
                step={s.step}
                value={settings[s.key]}
                onChange={(e) => onSettingsChange({ [s.field]: Number(e.target.value) })}
                className="flex-1 h-1.5 appearance-none rounded-full bg-gray-200 accent-gray-900 cursor-pointer"
              />
              <span className="text-xs text-gray-700 w-8 text-right">{settings[s.key]}</span>
            </div>
          ))}
          <button
            onClick={testVoice}
            disabled={testPlaying}
            className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded-full text-xs text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <Volume2 size={12} /> {testPlaying ? 'Playing...' : 'Test Voice'}
          </button>
        </div>
      )}
    </div>
  )
}
