import { useState } from 'react'
import { X } from 'lucide-react'

export default function TagInput({ tags = [], onChange, placeholder = 'Type and press Enter' }) {
  const [input, setInput] = useState('')
  const addTag = () => { const v = input.trim(); if (v && !tags.includes(v)) onChange([...tags, v]); setInput('') }
  const removeTag = (i) => onChange(tags.filter((_, j) => j !== i))

  return (
    <div className="flex flex-wrap gap-1.5 p-2 border border-gray-300 rounded-lg min-h-[40px] bg-white focus-within:ring-1 focus-within:ring-gray-400">
      {tags.map((tag, i) => (
        <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 rounded-full text-sm text-gray-700">
          {tag}
          <button onClick={() => removeTag(i)} className="text-gray-400 hover:text-gray-600"><X size={12} /></button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag() } }}
        placeholder={tags.length === 0 ? placeholder : ''}
        className="flex-1 min-w-[120px] outline-none text-sm bg-transparent"
      />
    </div>
  )
}
