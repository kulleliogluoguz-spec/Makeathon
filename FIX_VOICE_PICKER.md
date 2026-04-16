2 things to fix:

1. Remove ALL Content-Security-Policy headers and meta tags from the project. CSP is blocking voice preview audio and ElevenLabs API calls. Search for "Content-Security-Policy" in all frontend files and remove it:

Run: grep -rn "Content-Security-Policy" frontend/ --include="*.html" --include="*.js" --include="*.jsx" --include="*.ts"

Delete any CSP meta tag in index.html. Delete any CSP header in vite.config.js server.headers. We do not need CSP in development.

2. Fix the VoicePicker Play and Select buttons so they actually work:

Play button: When clicked, it should play the voice preview_url audio. The code should be:
const audio = new Audio(voice.preview_url);
audio.play();

Make sure preview_url is coming from the API response. Check that the /api/v1/voices/ endpoint returns preview_url for each voice.

Select button: When clicked, it should call onSelect(voice) prop which updates the persona state in PersonaEditorPage with voice_id, voice_name, voice_preview_url. The selected voice card should show a visual indicator (black border or "Selected" badge).

After fixing, verify:
- Click Play on any voice card -> audio plays from ElevenLabs
- Click Select on any voice card -> card shows as selected, persona.voice_id is updated

DO NOT rewrite any component. Only fix the specific issues. DO NOT touch backend. DO NOT push to git.
