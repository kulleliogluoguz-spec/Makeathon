Quick replies are stored in one language but must work in ALL languages. When a customer asks in German and the quick reply answer is in Turkish, the AI should translate the answer to German automatically.

Fix: Update the quick replies prompt in all 3 files. Do NOT change any other code. Do NOT push to git.

In instagram.py, messenger.py, and livechat.py — find where quick_replies_text is built. Replace the prompt text with:

```python
quick_replies_text = ""
try:
    from app.models.quick_reply import QuickReply
    async with async_session() as session:
        qr_result = await session.execute(select(QuickReply))
        qr_list = qr_result.scalars().all()
        if qr_list:
            quick_replies_text = "\n\n## PREDEFINED Q&A\nBelow are predefined question-answer pairs. When the customer asks about any of these topics, use the provided answer as your source of truth. IMPORTANT: The answers below may be written in a different language than the customer is using. You MUST translate the answer into the customer's language while keeping the exact same meaning and information. Do NOT change the facts — only translate.\n\n"
            for qr in qr_list:
                quick_replies_text += f"QUESTION: {qr.title}\nANSWER: {qr.content}\n\n"
except Exception as e:
    print(f"Quick replies load error: {e}")
```

The key change is this instruction: "The answers below may be written in a different language than the customer is using. You MUST translate the answer into the customer's language while keeping the exact same meaning and information."

Do this in all 3 files. Do NOT change anything else. Do NOT push to git.
