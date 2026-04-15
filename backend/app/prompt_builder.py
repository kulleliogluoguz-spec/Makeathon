"""
Core system prompt builder. Takes a Persona object and produces a
production-quality system prompt that any LLM can use.
"""

from app.models import Persona

TRAIT_LABELS = {
    "friendliness": ("cold and distant", "slightly warm", "somewhat friendly", "moderately friendly", "fairly friendly", "very friendly and warm", "extremely warm and welcoming"),
    "formality":    ("very casual and relaxed", "quite casual", "somewhat casual", "balanced in formality", "fairly formal", "very formal and proper", "extremely formal and ceremonious"),
    "assertiveness":("very passive and deferential", "quite passive", "somewhat passive", "balanced in assertiveness", "fairly assertive", "very assertive and confident", "extremely assertive and commanding"),
    "empathy":      ("detached and clinical", "slightly empathetic", "somewhat empathetic", "moderately empathetic", "fairly empathetic", "very empathetic and caring", "extremely empathetic and deeply caring"),
    "humor":        ("serious with no humor", "rarely humorous", "occasionally humorous", "moderately humorous", "fairly humorous", "very humorous and witty", "extremely humorous and playful"),
    "patience":     ("very impatient", "somewhat impatient", "occasionally patient", "moderately patient", "fairly patient", "very patient and understanding", "extremely patient and never rushed"),
    "enthusiasm":   ("monotone and flat", "slightly enthusiastic", "somewhat enthusiastic", "moderately enthusiastic", "fairly enthusiastic", "very enthusiastic and energetic", "extremely enthusiastic and vibrant"),
    "directness":   ("very indirect and diplomatic", "quite indirect", "somewhat indirect", "balanced between direct and diplomatic", "fairly direct", "very direct and straightforward", "extremely direct and blunt"),
}

LANGUAGE_NAMES = {
    "tr": "Turkish",
    "en": "English",
    "de": "German",
}


def _trait_description(trait_name: str, value: int) -> str:
    """Map 0-100 integer to a natural language description."""
    labels = TRAIT_LABELS.get(trait_name)
    if not labels:
        return ""
    if value <= 15:
        return labels[0]
    elif value <= 30:
        return labels[1]
    elif value <= 45:
        return labels[2]
    elif value <= 55:
        return labels[3]
    elif value <= 70:
        return labels[4]
    elif value <= 85:
        return labels[5]
    else:
        return labels[6]


def build_system_prompt(persona: Persona) -> str:
    """Build a comprehensive system prompt from all persona fields."""
    sections = []

    # === Identity ===
    identity_parts = []
    name = persona.display_name or persona.name
    role = persona.role_title or "voice assistant"
    company = f" at {persona.company_name}" if persona.company_name else ""
    identity_parts.append(f"You are {name}, a {role}{company}.")

    if persona.description:
        identity_parts.append(persona.description)
    if persona.background_story:
        identity_parts.append(f"\nBackground: {persona.background_story}")

    sections.append("## Identity\n" + "\n".join(identity_parts))

    # === Personality ===
    trait_lines = []
    for trait_name in ["friendliness", "formality", "assertiveness", "empathy", "humor", "patience", "enthusiasm", "directness"]:
        val = getattr(persona, trait_name, 50)
        desc = _trait_description(trait_name, val)
        trait_lines.append(f"- You are {desc} ({val}/100)")

    sections.append("## Personality\n" + "\n".join(trait_lines))

    # === Communication Style ===
    style_lines = []
    if persona.speaking_style:
        style_lines.append(f"- Speaking style: {persona.speaking_style}")
    style_lines.append(f"- Vocabulary: {persona.vocabulary_level} level")
    style_lines.append(f"- Sentence length: {persona.sentence_length}")
    if persona.tone_description:
        style_lines.append(f"- Tone: {persona.tone_description}")

    sections.append("## Communication Style\n" + "\n".join(style_lines))

    # === Response Rules ===
    guidelines = persona.response_guidelines or {}
    rule_lines = []
    max_sentences = guidelines.get("max_response_sentences", 3)
    rule_lines.append(f"- Keep responses to {max_sentences} sentences maximum")
    if guidelines.get("ask_one_question_at_a_time"):
        rule_lines.append("- Ask only one question at a time")
    if guidelines.get("always_confirm_understanding"):
        rule_lines.append("- Always confirm your understanding before moving on")
    if guidelines.get("use_caller_name"):
        rule_lines.append("- Use the caller's name when you know it")
    if guidelines.get("avoid_jargon"):
        rule_lines.append("- Avoid technical jargon; use simple, clear language")
    if guidelines.get("end_with_question"):
        rule_lines.append("- End each response with a question to keep the conversation flowing")
    if guidelines.get("acknowledge_before_responding"):
        rule_lines.append("- Always acknowledge what the caller said before responding")

    if rule_lines:
        sections.append("## Response Rules\n" + "\n".join(rule_lines))

    # === Expertise ===
    if persona.expertise_areas:
        sections.append("## Expertise\nYour areas of expertise: " + ", ".join(persona.expertise_areas) + ".")

    # === Example Phrases ===
    if persona.example_phrases:
        lines = ["Use phrases like these to guide your speaking style:"]
        for p in persona.example_phrases:
            lines.append(f'- "{p}"')
        sections.append("## Example Phrases\n" + "\n".join(lines))

    # === Forbidden Phrases ===
    if persona.forbidden_phrases:
        lines = ["NEVER use these phrases or anything similar:"]
        for p in persona.forbidden_phrases:
            lines.append(f'- "{p}"')
        sections.append("## Forbidden Phrases\n" + "\n".join(lines))

    # === Custom Greetings ===
    if persona.custom_greetings:
        lines = ["When starting a conversation, use one of these greetings:"]
        for g in persona.custom_greetings:
            lines.append(f'- "{g}"')
        sections.append("## Greetings\n" + "\n".join(lines))

    # === Filler / Backchannel Words ===
    if persona.filler_words:
        sections.append(
            "## Backchannel Words\n"
            "Use these words naturally to show you are listening: "
            + ", ".join(f'"{w}"' for w in persona.filler_words) + "."
        )

    # === Emotional Intelligence ===
    emotional = persona.emotional_responses or {}
    emo_lines = []
    for emotion, response in emotional.items():
        if response and response.strip():
            label = emotion.replace("_", " ")
            emo_lines.append(f"- When the caller seems {label}: {response}")
    if emo_lines:
        sections.append("## Emotional Intelligence\n" + "\n".join(emo_lines))

    # === Escalation Rules ===
    triggers = persona.escalation_triggers or []
    if triggers:
        esc_lines = ["Transfer to a human agent when:"]
        for t in triggers:
            trigger_type = t.get("trigger", "")
            action = t.get("action", "transfer_to_human")
            message = t.get("message", "")
            threshold = t.get("threshold")
            keywords = t.get("keywords", [])

            if trigger_type == "repeated_confusion" and threshold:
                esc_lines.append(f"- You have failed to resolve the issue after {threshold} attempts")
            elif trigger_type == "explicit_request":
                esc_lines.append("- The caller explicitly asks to speak to a human")
            elif trigger_type == "sensitive_topic" and keywords:
                esc_lines.append(f"- The conversation involves sensitive topics: {', '.join(keywords)}")
            elif trigger_type == "high_emotion":
                esc_lines.append("- The caller is very angry or emotionally distressed")
            else:
                esc_lines.append(f"- Trigger: {trigger_type}")

            if message:
                esc_lines.append(f'  When transferring, say: "{message}"')

            action_desc = action.replace("_", " ")
            esc_lines.append(f"  Action: {action_desc}")

        sections.append("## Escalation Rules\n" + "\n".join(esc_lines))

    # === Safety & Boundaries ===
    safety = persona.safety_rules or {}
    safety_lines = []
    never_discuss = safety.get("never_discuss", [])
    if never_discuss:
        safety_lines.append(f"- Never discuss: {', '.join(never_discuss)}")
    never_promise = safety.get("never_promise", [])
    if never_promise:
        safety_lines.append(f"- Never promise: {', '.join(never_promise)}")
    if safety.get("always_disclaim"):
        safety_lines.append(f"- Always disclose: {safety['always_disclaim']}")
    if safety.get("pii_handling"):
        safety_lines.append(f"- PII handling: {safety['pii_handling']}")
    if safety.get("out_of_scope_response"):
        safety_lines.append(f"- If asked about something outside your scope: {safety['out_of_scope_response']}")

    if safety_lines:
        sections.append("## Safety & Boundaries\n" + "\n".join(safety_lines))

    # === Custom Instructions ===
    if persona.custom_instructions and persona.custom_instructions.strip():
        sections.append("## Additional Instructions\n" + persona.custom_instructions.strip())

    # === Language ===
    lang_name = LANGUAGE_NAMES.get(persona.language, persona.language)
    sections.append(f"## Language\nRespond in {lang_name}. Use appropriate cultural norms and expressions for this language.")

    return "\n\n".join(sections)
