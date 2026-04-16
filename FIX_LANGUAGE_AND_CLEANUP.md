3 changes. Do NOT rewrite files. Do NOT push to git.

## CHANGE 1 — Fix Turkish response to English messages

The problem is the persona's system_prompt is written in Turkish (because the persona was created in Turkish). When system_prompt is Turkish, the AI defaults to Turkish regardless of the language instruction.

Fix: In instagram.py, messenger.py, and livechat.py — add an EXPLICIT instruction in the user message itself, not just system prompt. The user message has even stronger effect than system prompt.

In all 3 files, find where the messages array is built for the LLM call. It looks like this:

```python
messages = [{"role": "system", "content": full_system_prompt}] + history
```

Replace with:

```python
# Add language detection instruction as the last user message context
last_user_msg = ""
for m in reversed(history):
    if m.get("role") == "user":
        last_user_msg = m.get("content", "")
        break

language_reminder = {"role": "user", "content": f"[SYSTEM NOTE: The customer's last message is: \"{last_user_msg}\". You MUST reply in the SAME language as this message. If this message is in English, reply in English. If Turkish, reply in Turkish. If German, reply in German. Detect the language and match it exactly.]"}

messages = [{"role": "system", "content": full_system_prompt}] + history + [language_reminder]
```

Do this in all 3 files:
1. backend/app/api/instagram.py
2. backend/app/api/messenger.py  
3. backend/app/api/livechat.py

## CHANGE 2 — Remove language field from persona editor

In the frontend PersonaEditorPage, find the "language" dropdown/select field (where user picks Turkish/English/German). Remove that field completely from the UI. If it's inside a section, just remove the language input — keep the rest of the section.

Also in the persona templates (backend/app/api/persona_templates.py), remove the "language": "tr" field from all 3 templates. This way personas are language-agnostic.

## CHANGE 3 — Remove Agents page, auto-activate all personas

The Agents page is unnecessary since personas are the main entity. Remove it:

1. In frontend/src/App.jsx:
   - DELETE the import for AgentListPage (or AgentsPage or whatever it's called)
   - DELETE the /agents Route
   - DELETE the "Agents" nav link from the navbar

2. That's it. The backend agent endpoints can stay (they don't hurt anything), just remove the frontend page and navigation.

Do NOT remove any backend files. Only frontend changes for the Agents removal.

Do NOT push to git.
