Add automatic translation / multilingual support. The AI should ALWAYS respond in the same language the customer writes in. If customer writes Turkish, respond Turkish. German? German. French? French.

This requires NO new files. Just update the system prompts in 3 files.

RULES: Do NOT rewrite files. Do NOT push to git. Only change the specific lines mentioned.

1. In backend/app/api/instagram.py, find where full_system_prompt is built. Add this text to the BEGINNING of the system prompt (before persona + products + scoring):

```python
language_instruction = "\n\nCRITICAL LANGUAGE RULE: You MUST detect the language the customer is writing in and respond in EXACTLY the same language. If they write Turkish, respond in Turkish. If German, respond in German. If English, respond in English. If French, respond in French. NEVER switch languages unless the customer does. This is your highest priority rule.\n\n"

full_system_prompt = language_instruction + system_prompt + products_text + scoring_context + quick_replies_text
```

2. In backend/app/api/messenger.py, find where full_system_prompt is built. Add the same language_instruction at the beginning:

```python
language_instruction = "\n\nCRITICAL LANGUAGE RULE: You MUST detect the language the customer is writing in and respond in EXACTLY the same language. If they write Turkish, respond in Turkish. If German, respond in German. If English, respond in English. If French, respond in French. NEVER switch languages unless the customer does. This is your highest priority rule.\n\n"

full_system_prompt = language_instruction + system_prompt + products_text + scoring_context + quick_replies_text
```

3. In backend/app/api/livechat.py, find where full_prompt is built in generate_livechat_reply. Add the same:

```python
language_instruction = "\n\nCRITICAL LANGUAGE RULE: You MUST detect the language the customer is writing in and respond in EXACTLY the same language. If they write Turkish, respond in Turkish. If German, respond in German. If English, respond in English. If French, respond in French. NEVER switch languages unless the customer does. This is your highest priority rule.\n\n"

full_prompt = language_instruction + system_prompt + products_text + scoring_context
```

That is ALL. 3 lines added to 3 files. Nothing else changes.

Test: Send "Merhaba, ne satıyorsunuz?" on Instagram → AI responds in Turkish.
Then send "What do you sell?" → AI responds in English.
Then send "Was verkaufen Sie?" → AI responds in German.

Do NOT push to git.
