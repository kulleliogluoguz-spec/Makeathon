import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Wand2, Eye, Copy, Trash2, Plus, X } from 'lucide-react'
import { t } from '../lib/i18n'
import TagInput from '../components/TagInput'
import Toggle from '../components/Toggle'
import Modal from '../components/Modal'
import VoiceBuilder from '../components/VoiceBuilder'
import VoicePicker from '../components/VoicePicker'
import CatalogManager from '../components/CatalogManager'
import { getPersona, updatePersona, generatePrompt, previewPrompt, duplicatePersona, deletePersona } from '../lib/api'

const inputCls = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-gray-400'

function Section({ id, title, description, children }) {
  return (
    <div id={id} className="bg-white border border-gray-200 rounded-xl p-6">
      <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      {description && <p className="text-sm text-gray-500 mt-1 mb-4">{description}</p>}
      {!description && <div className="mt-4" />}
      <div className="space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}

const traitMeta = [
  { key: 'friendliness', label: 'Friendliness', low: 'Cold & distant', high: 'Warm & welcoming' },
  { key: 'formality', label: 'Formality', low: 'Casual & relaxed', high: 'Formal & proper' },
  { key: 'assertiveness', label: 'Assertiveness', low: 'Passive & deferential', high: 'Assertive & commanding' },
  { key: 'empathy', label: 'Empathy', low: 'Detached & clinical', high: 'Deeply empathetic' },
  { key: 'humor', label: 'Humor', low: 'Serious, no humor', high: 'Very humorous & playful' },
  { key: 'patience', label: 'Patience', low: 'Impatient & rushed', high: 'Extremely patient' },
  { key: 'enthusiasm', label: 'Enthusiasm', low: 'Monotone & flat', high: 'Very enthusiastic' },
  { key: 'directness', label: 'Directness', low: 'Indirect & diplomatic', high: 'Very direct & blunt' },
]

const emotionDefaults = ['frustrated_caller', 'confused_caller', 'happy_caller', 'angry_caller', 'silent_caller', 'impatient_caller', 'sad_caller']

const triggerTypes = [
  { value: 'repeated_confusion', label: 'Repeated Confusion' },
  { value: 'explicit_request', label: 'Explicit Request' },
  { value: 'sensitive_topic', label: 'Sensitive Topic' },
  { value: 'high_emotion', label: 'High Emotion' },
]

const actionTypes = [
  { value: 'transfer_to_human', label: 'Transfer to Human' },
  { value: 'transfer_to_supervisor', label: 'Transfer to Supervisor' },
  { value: 'end_call', label: 'End Call' },
]

export default function PersonaEditorPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [original, setOriginal] = useState(null)
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [showPreview, setShowPreview] = useState(false)
  const [previewText, setPreviewText] = useState('')
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    getPersona(id).then((p) => { setOriginal(p); setForm(p) })
  }, [id])

  const set = useCallback((field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
    setDirty(true)
  }, [])

  const setGuideline = useCallback((key, value) => {
    setForm((prev) => ({ ...prev, response_guidelines: { ...(prev.response_guidelines || {}), [key]: value } }))
    setDirty(true)
  }, [])

  const setEmotion = useCallback((key, value) => {
    setForm((prev) => ({ ...prev, emotional_responses: { ...(prev.emotional_responses || {}), [key]: value } }))
    setDirty(true)
  }, [])

  const setSafety = useCallback((key, value) => {
    setForm((prev) => ({ ...prev, safety_rules: { ...(prev.safety_rules || {}), [key]: value } }))
    setDirty(true)
  }, [])

  const updateTrigger = useCallback((index, field, value) => {
    setForm((prev) => {
      const triggers = [...(prev.escalation_triggers || [])]
      triggers[index] = { ...triggers[index], [field]: value }
      return { ...prev, escalation_triggers: triggers }
    })
    setDirty(true)
  }, [])

  const addTrigger = useCallback(() => {
    setForm((prev) => ({
      ...prev,
      escalation_triggers: [...(prev.escalation_triggers || []), { trigger: 'explicit_request', action: 'transfer_to_human', message: '' }]
    }))
    setDirty(true)
  }, [])

  const removeTrigger = useCallback((index) => {
    setForm((prev) => ({
      ...prev,
      escalation_triggers: (prev.escalation_triggers || []).filter((_, i) => i !== index)
    }))
    setDirty(true)
  }, [])

  const addEmotion = useCallback(() => {
    const key = prompt('Emotion key (e.g. "nervous_caller"):')
    if (key && key.trim()) {
      setEmotion(key.trim(), '')
    }
  }, [setEmotion])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await updatePersona(id, form)
      setOriginal(updated)
      setForm(updated)
      setDirty(false)
    } finally {
      setSaving(false)
    }
  }

  const handleDiscard = () => {
    setForm(original)
    setDirty(false)
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      // Save first, then generate
      await updatePersona(id, form)
      const result = await generatePrompt(id)
      set('system_prompt', result.system_prompt)
      setDirty(true)
    } finally {
      setGenerating(false)
    }
  }

  const handlePreview = async () => {
    await updatePersona(id, form)
    const result = await previewPrompt(id)
    setPreviewText(result.system_prompt)
    setShowPreview(true)
  }

  const handleDuplicate = async () => {
    const copy = await duplicatePersona(id)
    navigate(`/personas/${copy.id}`)
  }

  const handleDelete = async () => {
    if (!confirm('Delete this persona?')) return
    await deletePersona(id)
    navigate('/personas')
  }

  const handleCopy = () => {
    if (form.system_prompt) navigator.clipboard.writeText(form.system_prompt)
  }

  if (!form) return <div className="p-8 text-gray-400">Loading...</div>

  const guidelines = form.response_guidelines || {}
  const emotions = form.emotional_responses || {}
  const safety = form.safety_rules || {}
  const triggers = form.escalation_triggers || []
  const promptWords = (form.system_prompt || '').split(/\s+/).filter(Boolean).length

  return (
    <div className="pb-20">
      <div className="max-w-4xl mx-auto py-6 px-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/personas')} className="text-gray-400 hover:text-gray-600"><ArrowLeft size={20} strokeWidth={1.5} /></button>
            <input value={form.display_name || form.name || ''} onChange={(e) => set('display_name', e.target.value)} className="text-xl font-bold text-gray-900 bg-transparent border-none outline-none" />
            {dirty && <span className="w-2 h-2 rounded-full bg-yellow-400" title="Unsaved changes" />}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleDuplicate} className="p-2 text-gray-400 hover:text-gray-600" title="Duplicate"><Copy size={18} strokeWidth={1.5} /></button>
            <button onClick={handleDelete} className="text-sm text-red-500 hover:text-red-700">Delete</button>
          </div>
        </div>

        <div className="space-y-6">
          {/* Section 1: Identity */}
          <Section id="section-identity" title={t('personas_editor_identity')} description="Who is this persona?">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Display Name"><input value={form.display_name || ''} onChange={(e) => set('display_name', e.target.value)} className={inputCls} /></Field>
              <Field label="Role Title"><input value={form.role_title || ''} onChange={(e) => set('role_title', e.target.value)} className={inputCls} /></Field>
              <Field label="Company Name"><input value={form.company_name || ''} onChange={(e) => set('company_name', e.target.value)} className={inputCls} /></Field>
            </div>
            <Field label="Description"><textarea value={form.description || ''} onChange={(e) => set('description', e.target.value)} rows={2} className={inputCls} /></Field>
            <Field label="Background Story"><textarea value={form.background_story || ''} onChange={(e) => set('background_story', e.target.value)} rows={4} className={inputCls} /></Field>
            <Field label="Expertise Areas"><TagInput tags={form.expertise_areas || []} onChange={(v) => set('expertise_areas', v)} /></Field>
          </Section>

          {/* Section: Voice */}
          <Section id="section-voice" title={t('personas_editor_voice')} description={t('personas_editor_voice_desc')}>
            <VoicePicker
              selectedVoiceId={form.voice_id}
              voiceSettings={{
                model: form.voice_model,
                stability: form.voice_stability,
                similarity: form.voice_similarity,
                style: form.voice_style,
                speed: form.voice_speed,
              }}
              onVoiceSelect={(voice) => {
                set('voice_id', voice.voice_id)
                setForm((prev) => ({
                  ...prev,
                  voice_id: voice.voice_id,
                  voice_name: voice.name,
                  voice_preview_url: voice.preview_url,
                }))
                setDirty(true)
              }}
              onSettingsChange={(s) => {
                setForm((prev) => ({ ...prev, ...s }))
                setDirty(true)
              }}
            />
          </Section>

          {/* Product Catalogs */}
          <Section id="section-catalogs" title={t('personas_editor_catalogs')} description={t('personas_editor_catalogs_desc')}>
            <CatalogManager personaId={id} />
          </Section>

          {/* Section 2: Personality Traits */}
          <Section id="section-personality" title={t('personas_editor_personality')} description="Configure personality on a 0-100 scale">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
              {traitMeta.map((t) => {
                const val = form[t.key] ?? 50
                const color = val <= 33 ? 'accent-blue-500' : val <= 66 ? 'accent-yellow-500' : 'accent-green-500'
                return (
                  <div key={t.key}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">{t.label}</span>
                      <span className="text-sm font-semibold text-gray-900">{val}</span>
                    </div>
                    <input type="range" min={0} max={100} value={val} onChange={(e) => set(t.key, Number(e.target.value))} className={`w-full h-1.5 appearance-none rounded-full bg-gray-200 cursor-pointer ${color}`} />
                    <div className="flex justify-between mt-0.5">
                      <span className="text-[10px] text-gray-400">{t.low}</span>
                      <span className="text-[10px] text-gray-400">{t.high}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </Section>

          {/* Section 3: Communication Style */}
          <Section id="section-communication" title={t('personas_editor_communication')}>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Vocabulary Level">
                <select value={form.vocabulary_level || 'professional'} onChange={(e) => set('vocabulary_level', e.target.value)} className={inputCls}>
                  <option value="simple">Simple</option>
                  <option value="professional">Professional</option>
                  <option value="technical">Technical</option>
                  <option value="academic">Academic</option>
                </select>
              </Field>
              <Field label="Sentence Length">
                <select value={form.sentence_length || 'medium'} onChange={(e) => set('sentence_length', e.target.value)} className={inputCls}>
                  <option value="short">Short</option>
                  <option value="medium">Medium</option>
                  <option value="long">Long</option>
                  <option value="varied">Varied</option>
                </select>
              </Field>
            </div>
            <Field label="Speaking Style"><textarea value={form.speaking_style || ''} onChange={(e) => set('speaking_style', e.target.value)} rows={2} className={inputCls} /></Field>
            <Field label="Tone Description"><textarea value={form.tone_description || ''} onChange={(e) => set('tone_description', e.target.value)} rows={2} className={inputCls} /></Field>
          </Section>

          {/* Section 4: Phrases */}
          <Section id="section-phrases" title={t('personas_editor_phrases')}>
            <Field label={<>Example Phrases <span className="text-xs text-gray-400 ml-1">({(form.example_phrases || []).length})</span></>}>
              <textarea value={(form.example_phrases || []).join('\n')} onChange={(e) => set('example_phrases', e.target.value.split('\n').filter(Boolean))} rows={4} className={inputCls} placeholder="One phrase per line" />
            </Field>
            <Field label="Forbidden Phrases"><TagInput tags={form.forbidden_phrases || []} onChange={(v) => set('forbidden_phrases', v)} placeholder="Add forbidden phrase" /></Field>
            <Field label={<>Custom Greetings <span className="text-xs text-gray-400 ml-1">({(form.custom_greetings || []).length})</span></>}>
              <textarea value={(form.custom_greetings || []).join('\n')} onChange={(e) => set('custom_greetings', e.target.value.split('\n').filter(Boolean))} rows={3} className={inputCls} placeholder="One greeting per line" />
            </Field>
            <Field label="Filler / Backchannel Words"><TagInput tags={form.filler_words || []} onChange={(v) => set('filler_words', v)} placeholder="e.g. evet, anliyorum" /></Field>
          </Section>

          {/* Section 5: Response Rules */}
          <Section id="section-response_rules" title={t('personas_editor_response_rules')} description="How the agent structures responses">
            <div className="space-y-3">
              <Toggle enabled={guidelines.ask_one_question_at_a_time ?? true} onChange={(v) => setGuideline('ask_one_question_at_a_time', v)} label="Ask only one question at a time" />
              <Toggle enabled={guidelines.always_confirm_understanding ?? true} onChange={(v) => setGuideline('always_confirm_understanding', v)} label="Always confirm understanding before moving on" />
              <Toggle enabled={guidelines.use_caller_name ?? true} onChange={(v) => setGuideline('use_caller_name', v)} label="Use the caller's name when known" />
              <Toggle enabled={guidelines.avoid_jargon ?? true} onChange={(v) => setGuideline('avoid_jargon', v)} label="Avoid technical jargon" />
              <Toggle enabled={guidelines.end_with_question ?? true} onChange={(v) => setGuideline('end_with_question', v)} label="End each response with a question" />
              <Toggle enabled={guidelines.acknowledge_before_responding ?? true} onChange={(v) => setGuideline('acknowledge_before_responding', v)} label="Acknowledge before responding" />
            </div>
            <Field label="Max Response Sentences">
              <input type="number" min={1} max={10} value={guidelines.max_response_sentences ?? 3} onChange={(e) => setGuideline('max_response_sentences', Number(e.target.value))} className={inputCls + ' w-24'} />
            </Field>
          </Section>

          {/* Section 6: Emotional Intelligence */}
          <Section id="section-emotional" title={t('personas_editor_emotional')} description="How to respond to different caller emotions">
            <div className="space-y-3">
              {Object.entries(emotions).map(([key, val]) => (
                <div key={key} className="border border-gray-200 rounded-lg p-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">{key.replace(/_/g, ' ')}</label>
                  <textarea value={val || ''} onChange={(e) => setEmotion(key, e.target.value)} rows={2} className={inputCls} />
                </div>
              ))}
            </div>
            <button onClick={addEmotion} className="text-sm text-gray-500 hover:text-gray-800 flex items-center gap-1"><Plus size={14} /> Add emotion</button>
          </Section>

          {/* Section 7: Escalation Rules */}
          <Section id="section-escalation" title={t('personas_editor_escalation')} description="When to transfer to a human agent">
            <div className="space-y-3">
              {triggers.map((t, i) => (
                <div key={i} className="border border-gray-200 rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="grid grid-cols-2 gap-3 flex-1">
                      <Field label="Trigger Type">
                        <select value={t.trigger || ''} onChange={(e) => updateTrigger(i, 'trigger', e.target.value)} className={inputCls}>
                          {triggerTypes.map((tt) => <option key={tt.value} value={tt.value}>{tt.label}</option>)}
                        </select>
                      </Field>
                      <Field label="Action">
                        <select value={t.action || 'transfer_to_human'} onChange={(e) => updateTrigger(i, 'action', e.target.value)} className={inputCls}>
                          {actionTypes.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                        </select>
                      </Field>
                    </div>
                    <button onClick={() => removeTrigger(i)} className="ml-3 text-gray-400 hover:text-red-500 mt-5"><Trash2 size={16} /></button>
                  </div>
                  {t.trigger === 'repeated_confusion' && (
                    <Field label="Threshold (attempts)">
                      <input type="number" value={t.threshold || 3} onChange={(e) => updateTrigger(i, 'threshold', Number(e.target.value))} className={inputCls + ' w-24'} />
                    </Field>
                  )}
                  {t.trigger === 'sensitive_topic' && (
                    <Field label="Keywords">
                      <TagInput tags={t.keywords || []} onChange={(v) => updateTrigger(i, 'keywords', v)} placeholder="Add keyword" />
                    </Field>
                  )}
                  <Field label="Transfer Message">
                    <input value={t.message || ''} onChange={(e) => updateTrigger(i, 'message', e.target.value)} className={inputCls} />
                  </Field>
                </div>
              ))}
            </div>
            <button onClick={addTrigger} className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-500 hover:border-gray-400 hover:text-gray-700 flex items-center justify-center gap-1">
              <Plus size={14} /> Add Escalation Rule
            </button>
          </Section>

          {/* Section 8: Safety & Boundaries */}
          <Section id="section-safety" title={t('personas_editor_safety')} description="Topics and promises to avoid">
            <Field label="Never Discuss"><TagInput tags={safety.never_discuss || []} onChange={(v) => setSafety('never_discuss', v)} placeholder="e.g. politics, religion" /></Field>
            <Field label="Never Promise"><TagInput tags={safety.never_promise || []} onChange={(v) => setSafety('never_promise', v)} placeholder="e.g. specific discounts" /></Field>
            <Field label="AI Disclaimer"><input value={safety.always_disclaim || ''} onChange={(e) => setSafety('always_disclaim', e.target.value)} className={inputCls} placeholder="I am an AI assistant." /></Field>
            <Field label="PII Handling Rules"><textarea value={safety.pii_handling || ''} onChange={(e) => setSafety('pii_handling', e.target.value)} rows={2} className={inputCls} /></Field>
            <Field label="Out of Scope Response"><textarea value={safety.out_of_scope_response || ''} onChange={(e) => setSafety('out_of_scope_response', e.target.value)} rows={2} className={inputCls} /></Field>
          </Section>

          {/* Section 9: Custom Instructions */}
          <Section id="section-custom" title={t('personas_editor_custom')} description="Any additional rules appended to the system prompt">
            <textarea value={form.custom_instructions || ''} onChange={(e) => set('custom_instructions', e.target.value)} rows={6} className={inputCls + ' font-mono text-xs'} placeholder="Additional rules and instructions..." />
          </Section>

          {/* Section 10: Generated System Prompt */}
          <Section id="section-language" title={t('personas_editor_system_prompt')}>
            <textarea
              value={form.system_prompt || ''}
              onChange={(e) => set('system_prompt', e.target.value)}
              rows={20}
              className={inputCls + ' font-mono text-xs min-h-[400px]'}
              placeholder="Click 'Generate from settings' to build the system prompt..."
            />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button onClick={handleGenerate} disabled={generating} className="flex items-center gap-1.5 px-4 py-2 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800 disabled:opacity-50">
                  <Wand2 size={14} strokeWidth={1.5} /> {generating ? 'Generating...' : t('personas_generate_prompt')}
                </button>
                <button onClick={handlePreview} className="flex items-center gap-1.5 px-4 py-2 border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50">
                  <Eye size={14} strokeWidth={1.5} /> Preview
                </button>
                <button onClick={handleCopy} className="flex items-center gap-1.5 px-4 py-2 border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50">
                  <Copy size={14} strokeWidth={1.5} /> Copy
                </button>
              </div>
              <span className="text-xs text-gray-400">{promptWords} words</span>
            </div>
          </Section>
        </div>
      </div>

      {/* Sticky Bottom Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-6 py-3 flex items-center justify-end gap-3 z-40">
        {dirty && <span className="flex items-center gap-1.5 text-sm text-yellow-600"><span className="w-2 h-2 rounded-full bg-yellow-400" /> Unsaved changes</span>}
        <button onClick={handleDiscard} disabled={!dirty} className="px-4 py-2 border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40">
          {t('personas_discard')}
        </button>
        <button onClick={handleSave} disabled={saving || !dirty} className="px-6 py-2 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800 disabled:opacity-50 flex items-center gap-1.5">
          <Save size={14} strokeWidth={1.5} /> {saving ? 'Saving...' : t('personas_save')}
        </button>
      </div>

      {/* Preview Modal */}
      <Modal open={showPreview} onClose={() => setShowPreview(false)} title="System Prompt Preview" wide>
        <pre className="whitespace-pre-wrap text-xs text-gray-800 font-mono bg-gray-50 p-4 rounded-lg max-h-[60vh] overflow-y-auto">{previewText}</pre>
        <div className="flex justify-between mt-4">
          <span className="text-xs text-gray-400">{previewText.split(/\s+/).filter(Boolean).length} words</span>
          <button onClick={() => { navigator.clipboard.writeText(previewText); setShowPreview(false) }} className="px-4 py-2 bg-black text-white rounded-full text-sm font-medium hover:bg-gray-800">
            Copy & Close
          </button>
        </div>
      </Modal>

      {/* Voice Builder Widget */}
      <VoiceBuilder
        personaId={id}
        persona={form}
        onFieldsExtracted={(fields) => {
          // Special signal to generate prompt
          if (fields._generate) {
            handleGenerate()
            return
          }
          // Merge extracted fields into form, handling nested objects
          setForm((prev) => ({
            ...prev,
            ...fields,
            ...(fields.response_guidelines && {
              response_guidelines: { ...(prev.response_guidelines || {}), ...fields.response_guidelines },
            }),
            ...(fields.emotional_responses && {
              emotional_responses: { ...(prev.emotional_responses || {}), ...fields.emotional_responses },
            }),
            ...(fields.safety_rules && {
              safety_rules: { ...(prev.safety_rules || {}), ...fields.safety_rules },
            }),
          }))
          setDirty(true)
        }}
      />
    </div>
  )
}
