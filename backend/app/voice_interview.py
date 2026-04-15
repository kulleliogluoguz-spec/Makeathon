"""
Interview flow definition — the sequence of questions and
how to extract persona fields from spoken answers.
"""

INTERVIEW_QUESTIONS = [
    {
        "id": "identity_name",
        "text": "Let's build your agent's persona! First, what name should your agent use when introducing itself?",
        "text_tr": "Agentinizin personasini olusturalim! Once, agentiniz kendini tanitirken hangi ismi kullansin?",
        "field_group": "identity",
        "target_fields": ["display_name"],
        "extraction_prompt": 'Extract the agent\'s display name from the user\'s answer. Return JSON: {"display_name": "..."}',
    },
    {
        "id": "identity_role",
        "text": "What is {display_name}'s role or job title? And which company does {display_name} work for?",
        "text_tr": "{display_name}'in rolu veya is unvani ne? Ve hangi sirkette calisiyor?",
        "field_group": "identity",
        "target_fields": ["role_title", "company_name"],
        "extraction_prompt": 'Extract the role title and company name. Return JSON: {"role_title": "...", "company_name": "..."}',
    },
    {
        "id": "identity_background",
        "text": "Tell me a bit about {display_name}'s background and expertise. What are they an expert in? How many years of experience?",
        "text_tr": "{display_name}'in gecmisi ve uzmanligi hakkinda biraz bilgi verin. Neyde uzman? Kac yillik deneyimi var?",
        "field_group": "identity",
        "target_fields": ["background_story", "expertise_areas"],
        "extraction_prompt": 'Extract background story as a paragraph and expertise areas as a list. Return JSON: {"background_story": "...", "expertise_areas": ["..."]}',
    },
    {
        "id": "personality_overview",
        "text": "How would you describe {display_name}'s personality? For example: friendly or reserved? Formal or casual? Patient or quick? Humorous or serious?",
        "text_tr": "{display_name}'in kisligini nasil tanimlarsiniz? Ornegin: samimi mi mesafeli mi? Resmi mi rahat mi? Sabirli mi hizli mi? Esprili mi ciddi mi?",
        "field_group": "personality",
        "target_fields": ["friendliness", "formality", "patience", "humor", "enthusiasm", "directness", "empathy", "assertiveness"],
        "extraction_prompt": 'Based on the personality description, assign values from 0-100 for each trait. Very friendly=85, somewhat formal=55, very patient=90, etc. Return JSON: {"friendliness": 85, "formality": 55, "patience": 90, "humor": 40, "enthusiasm": 70, "directness": 50, "empathy": 75, "assertiveness": 60}',
    },
    {
        "id": "communication_style",
        "text": "How should {display_name} speak? Should the language be simple or technical? Short sentences or longer explanations? What tone should they use?",
        "text_tr": "{display_name} nasil konusmali? Dil basit mi teknik mi olsun? Kisa cumleler mi uzun aciklamalar mi? Hangi tonu kullanmali?",
        "field_group": "communication",
        "target_fields": ["speaking_style", "vocabulary_level", "sentence_length", "tone_description"],
        "extraction_prompt": 'Extract communication preferences. vocabulary_level must be one of: simple, professional, technical, academic. sentence_length must be one of: short, medium, long, varied. Return JSON: {"speaking_style": "...", "vocabulary_level": "professional", "sentence_length": "medium", "tone_description": "..."}',
    },
    {
        "id": "example_phrases",
        "text": "Can you give me 3 or 4 example phrases that {display_name} would typically say? Things like greetings or common responses.",
        "text_tr": "{display_name}'in tipik olarak soyleyecegi 3-4 ornek cumle verebilir misiniz?",
        "field_group": "phrases",
        "target_fields": ["example_phrases", "custom_greetings"],
        "extraction_prompt": 'Extract example phrases and greetings as separate lists. Return JSON: {"example_phrases": ["..."], "custom_greetings": ["..."]}',
    },
    {
        "id": "forbidden_phrases",
        "text": "Are there any phrases or words that {display_name} should NEVER use? Things that would be unprofessional or off-brand?",
        "text_tr": "{display_name}'in asla kullanmamasi gereken cumleler veya kelimeler var mi?",
        "field_group": "phrases",
        "target_fields": ["forbidden_phrases"],
        "extraction_prompt": 'Extract forbidden phrases as a list. Return JSON: {"forbidden_phrases": ["..."]}',
    },
    {
        "id": "response_rules",
        "text": "Some quick rules: Should {display_name} ask only one question at a time? Should it confirm understanding before answering? Should it always end with a question? Keep responses short - how many sentences max?",
        "text_tr": "Birkac hizli kural: {display_name} ayni anda tek bir soru mu sorsun? Cevaplamadan once anladigini teyit etsin mi? Her zaman bir soruyla mi bitirsin? Yanitlar kisa olsun - en fazla kac cumle?",
        "field_group": "response_rules",
        "target_fields": ["response_guidelines"],
        "extraction_prompt": 'Extract response rules. Return JSON: {"response_guidelines": {"max_response_sentences": 3, "ask_one_question_at_a_time": true, "always_confirm_understanding": true, "use_caller_name": true, "avoid_jargon": true, "end_with_question": true, "acknowledge_before_responding": true}}',
    },
    {
        "id": "emotional_frustrated",
        "text": "How should {display_name} handle a frustrated or angry caller? What about a confused caller?",
        "text_tr": "{display_name} sinirli veya kizgin bir arayani nasil ele almali? Peki kafasi karismis bir arayan?",
        "field_group": "emotional",
        "target_fields": ["emotional_responses"],
        "extraction_prompt": 'Extract emotional response strategies for frustrated, angry, and confused callers. Return JSON: {"emotional_responses": {"frustrated_caller": "...", "angry_caller": "...", "confused_caller": "..."}}',
    },
    {
        "id": "emotional_others",
        "text": "What about when the caller is happy and everything is going well? Or when they go silent? Or when they seem impatient?",
        "text_tr": "Peki arayan mutlu oldugunda? Ya da sessiz kaldiginda? Ya da sabirsiz olup hizli cevap istediginde?",
        "field_group": "emotional",
        "target_fields": ["emotional_responses"],
        "extraction_prompt": 'Extract emotional response strategies for happy, silent, and impatient callers. Return JSON: {"emotional_responses": {"happy_caller": "...", "silent_caller": "...", "impatient_caller": "..."}}',
    },
    {
        "id": "escalation",
        "text": "When should {display_name} hand off to a human? For example: after how many failed attempts? On which sensitive topics like complaints, legal issues, or refunds?",
        "text_tr": "{display_name} ne zaman bir insana devretmeli? Ornegin: kac basarisiz denemeden sonra? Sikayet, hukuki konular veya iadeler gibi hassas konularda mi?",
        "field_group": "escalation",
        "target_fields": ["escalation_triggers"],
        "extraction_prompt": 'Extract escalation triggers. Return JSON: {"escalation_triggers": [{"trigger": "repeated_confusion", "threshold": 3, "action": "transfer_to_human", "message": "..."}, {"trigger": "sensitive_topic", "keywords": [...], "action": "transfer_to_supervisor", "message": "..."}]}',
    },
    {
        "id": "safety",
        "text": "Are there topics {display_name} should never discuss? Things it should never promise? Should it tell callers it is an AI?",
        "text_tr": "{display_name}'in asla tartismamasi gereken konular var mi? Asla vaat etmemesi gereken seyler? Arayanlara bir yapay zeka oldugunu soylemeli mi?",
        "field_group": "safety",
        "target_fields": ["safety_rules"],
        "extraction_prompt": 'Extract safety rules. Return JSON: {"safety_rules": {"never_discuss": [...], "never_promise": [...], "always_disclaim": "...", "pii_handling": "...", "out_of_scope_response": "..."}}',
    },
    {
        "id": "custom_instructions",
        "text": "Any final special instructions for {display_name}? Anything specific about your product, offers, or things the agent should always mention?",
        "text_tr": "{display_name} icin son ozel talimatlar var mi? Urdununuz veya agentin her zaman bahsetmesi gereken seyler hakkinda spesifik bir sey?",
        "field_group": "custom",
        "target_fields": ["custom_instructions"],
        "extraction_prompt": 'Extract any custom instructions as free text. Return JSON: {"custom_instructions": "..."}',
    },
    {
        "id": "language_preference",
        "text": "Last question: what language should {display_name} primarily speak in? Turkish, English, or another language?",
        "text_tr": "Son soru: {display_name} oncelikli olarak hangi dilde konusmali?",
        "field_group": "language",
        "target_fields": ["language"],
        "extraction_prompt": 'Extract the language preference. Return the ISO code. Return JSON: {"language": "tr"}',
    },
    {
        "id": "filler_words",
        "text": "What filler or acknowledgment words should {display_name} use while listening? Things like 'I see', 'sure', 'understood' - in the chosen language.",
        "text_tr": "Dinlerken {display_name} hangi dolgu veya onaylama kelimelerini kullansin? 'Anliyorum', 'evet', 'tabii' gibi.",
        "field_group": "phrases",
        "target_fields": ["filler_words"],
        "extraction_prompt": 'Extract filler/backchannel words as a list. Return JSON: {"filler_words": ["..."]}',
    },
]


def get_question(index: int, context: dict, language: str = "en") -> dict | None:
    """Get question at index with template variables filled in."""
    if index < 0 or index >= len(INTERVIEW_QUESTIONS):
        return None

    q = INTERVIEW_QUESTIONS[index].copy()
    display_name = context.get("display_name", "your agent")

    text_key = "text_tr" if language == "tr" else "text"
    q["text"] = q[text_key].replace("{display_name}", display_name)
    q.pop("text_tr", None)

    return q
