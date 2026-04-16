There are 2 bugs to fix. Do NOT rewrite any file. Only fix these specific issues:

BUG 1: Product images not being sent on Instagram. Check app/api/instagram.py:
- Print the LLM raw response to see if recommend_product_ids is returned
- Make sure the JSON parsing block is working (try/except around json.loads)
- Make sure send_instagram_image function is being called after send_reply
- Add this debug line after parsing: print(f"Recommend IDs: {recommend_product_ids}")
- Add this debug line before sending image: print(f"Sending image: {img_url}")

BUG 2: AI giving nonsensical responses. Check app/api/instagram.py:
- Print the full_system_prompt to see what the AI is receiving: print(f"System prompt length: {len(full_system_prompt)}")
- The system prompt might be too long or corrupted. Make sure scoring_context is not breaking the prompt.
- Make sure the CSAT detection block (checking for "1"-"5") comes BEFORE the AI reply generation, so rating messages dont confuse the AI
- Make sure conversation_history is not mixing up different senders

After adding debug prints, restart backend. Then send an Instagram DM asking about products. Paste the backend logs here so I can see whats happening.

Do NOT rewrite instagram.py. Only add debug prints and fix the specific bugs. Do NOT push to git.
