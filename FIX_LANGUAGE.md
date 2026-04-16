The AI still sometimes responds in Turkish when the customer writes in English. Fix this.

In all 3 files (instagram.py, messenger.py, livechat.py), find the language_instruction variable. Replace it with this stronger version AND move it to the END of full_system_prompt:

```python
language_instruction = "\n\n=== ABSOLUTE LANGUAGE RULE (OVERRIDE EVERYTHING ABOVE) ===\nYou MUST respond in the EXACT SAME language the customer's LAST message is written in. Detect the language of their latest message and match it precisely. If their last message is in English, you respond ONLY in English. If Turkish, ONLY Turkish. If German, ONLY German. This rule overrides ALL other instructions including the persona language setting. NEVER respond in a different language than the customer's last message. This is NON-NEGOTIABLE.\n==="
```

Make sure it is appended LAST:

```python
full_system_prompt = system_prompt + products_text + scoring_context + quick_replies_text + language_instruction
```

NOT first. The last instruction in a system prompt has the strongest effect on LLM behavior.

Do this in all 3 files:
1. backend/app/api/instagram.py
2. backend/app/api/messenger.py
3. backend/app/api/livechat.py

Do NOT change anything else. Do NOT push to git.
