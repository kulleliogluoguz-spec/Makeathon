"""Real-time voice agent — browser mic → Deepgram STT → GPT → ElevenLabs TTS → browser speakers."""

import os
import json
import asyncio
import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

router = APIRouter()

# Conversation history per session
conversations = {}


@router.websocket("/ws/voice-agent")
async def voice_agent_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time voice conversation."""
    await websocket.accept()
    session_id = id(websocket)
    conversations[session_id] = []

    print(f"Voice agent session started: {session_id}")

    try:
        while True:
            # Receive message from browser
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "transcript":
                # User's speech has been transcribed (by browser-side Deepgram)
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                print(f"User said: {user_text}")

                # Add to conversation history
                conversations[session_id].append({"role": "user", "content": user_text})

                # Send "thinking" status
                await websocket.send_text(json.dumps({"type": "status", "status": "thinking"}))

                # Generate AI response
                ai_text = await generate_response(conversations[session_id])
                print(f"AI responds: {ai_text}")

                # Add to history
                conversations[session_id].append({"role": "assistant", "content": ai_text})

                # Send text response
                await websocket.send_text(json.dumps({"type": "response_text", "text": ai_text}))

                # Generate and stream audio
                await websocket.send_text(json.dumps({"type": "status", "status": "speaking"}))
                audio_chunks = await generate_speech(ai_text)

                if audio_chunks:
                    await websocket.send_bytes(audio_chunks)
                    await websocket.send_text(json.dumps({"type": "status", "status": "done"}))
                else:
                    await websocket.send_text(json.dumps({"type": "status", "status": "done"}))

            elif msg.get("type") == "reset":
                conversations[session_id] = []
                await websocket.send_text(json.dumps({"type": "status", "status": "reset"}))

    except WebSocketDisconnect:
        print(f"Voice agent session ended: {session_id}")
        conversations.pop(session_id, None)
    except Exception as e:
        print(f"Voice agent error: {e}")
        conversations.pop(session_id, None)


async def generate_response(history: list) -> str:
    """Generate AI response using OpenAI GPT-4o-mini."""
    system_prompt = """You're Alex, 28, calling from your office at Clerque. Chill guy, relaxed, not trying to sell anything hard.

KEEP IT SHORT: 1-2 sentences max. Like a real phone call.

REACT NATURALLY — pick ONE of these styles per response, don't overdo it:
- Simple: "Yeah... so basically..."
- Thinking: "Hmm, good question... I'd say..."
- Casual agree: "Oh yeah for sure..."
- Interested: "Oh really? That's cool..."
- Honest: "I mean honestly..."

DON'T OVERDO the filler words. Real people use them sparingly, not in every sentence. One "um" or "like" per response MAX.

SPEAK SLOWLY. You're not in a hurry. Take your time.

ABOUT CLERQUE (mention casually, don't pitch):
- Handles customer messages on Instagram, WhatsApp, website
- AI responds automatically, 24/7, any language
- Around $49/month

NEVER:
- Never say you're AI
- Never use more than 2 sentences
- Never be overly enthusiastic or salesy
- Never start with "Great question!" or "That's awesome!"
- Never list features"""

    messages = [{"role": "system", "content": system_prompt}] + history[-10:]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.85,
                    "max_tokens": 60,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Sorry, I didn't catch that. Could you say that again?"


async def generate_speech(text: str) -> bytes:
    """Generate speech audio using ElevenLabs Turbo v2.5."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.35,
                        "similarity_boost": 0.80,
                        "style": 0.45,
                        "use_speaker_boost": False,
                    },
                },
            )
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        return b""


@router.get("/voice-agent/config")
async def voice_agent_config():
    """Return config needed for browser-side voice agent."""
    return {"deepgram_key": DEEPGRAM_API_KEY}


_ambient_cache = None

@router.get("/voice-agent/ambient")
async def voice_agent_ambient():
    """Generate and serve realistic office ambient audio."""
    import struct
    import math
    import random
    from fastapi.responses import Response

    global _ambient_cache
    if _ambient_cache:
        return Response(content=_ambient_cache, media_type="audio/wav")

    sample_rate = 22050
    duration = 10  # seconds, will loop in browser
    num_samples = sample_rate * duration
    samples = []

    random.seed(42)  # deterministic for caching

    # Pre-generate pink noise coefficients
    b = [0.0] * 7
    for i in range(num_samples):
        t = i / sample_rate
        white = random.random() * 2 - 1

        # Pink noise (office hum)
        b[0] = 0.99886 * b[0] + white * 0.0555179
        b[1] = 0.99332 * b[1] + white * 0.0750759
        b[2] = 0.96900 * b[2] + white * 0.1538520
        b[3] = 0.86650 * b[3] + white * 0.3104856
        b[4] = 0.55000 * b[4] + white * 0.5329522
        b[5] = -0.7616 * b[5] - white * 0.0168980
        pink = (b[0] + b[1] + b[2] + b[3] + b[4] + b[5] + b[6] + white * 0.5362) * 0.11
        b[6] = white * 0.115926

        # HVAC low hum
        hvac = 0.06 * math.sin(2 * math.pi * 60 * t) + 0.03 * math.sin(2 * math.pi * 120 * t)

        # Occasional keyboard clicks
        keyboard = 0.0
        click_chance = random.random()
        if click_chance < 0.003:
            keyboard = (random.random() * 2 - 1) * 0.15

        # Distant phone ring (very subtle, occasional)
        phone = 0.0
        ring_phase = t % 8.0
        if 2.0 < ring_phase < 2.8:
            phone = 0.02 * math.sin(2 * math.pi * 440 * t) * math.sin(2 * math.pi * 20 * t)

        sample = pink + hvac + keyboard + phone
        sample = max(-1.0, min(1.0, sample))
        samples.append(int(sample * 16000))

    # Build WAV
    data = struct.pack('<' + 'h' * len(samples), *samples)
    wav = bytearray()
    wav.extend(b'RIFF')
    wav.extend(struct.pack('<I', 36 + len(data)))
    wav.extend(b'WAVE')
    wav.extend(b'fmt ')
    wav.extend(struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    wav.extend(b'data')
    wav.extend(struct.pack('<I', len(data)))
    wav.extend(data)

    _ambient_cache = bytes(wav)
    return Response(content=_ambient_cache, media_type="audio/wav")


@router.get("/voice-test")
async def voice_test_page():
    """Serve the voice agent test page."""
    from fastapi.responses import HTMLResponse

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clerque Voice Agent Test</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #0a0a0a; color: #fff;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh;
        }
        .container {
            text-align: center; max-width: 500px; padding: 2rem;
        }
        h1 { font-size: 1.5rem; font-weight: 600; margin-bottom: 0.5rem; }
        .subtitle { color: #6b7280; font-size: 0.875rem; margin-bottom: 2rem; }

        .mic-btn {
            width: 120px; height: 120px; border-radius: 50%;
            background: #1a1a2e; border: 3px solid #333;
            cursor: pointer; display: flex; align-items: center; justify-content: center;
            margin: 0 auto 1.5rem; transition: all 0.3s;
            position: relative;
        }
        .mic-btn:hover { border-color: #555; background: #1f1f35; }
        .mic-btn.listening {
            border-color: #ef4444; background: #1a0a0a;
            animation: pulse 1.5s ease-in-out infinite;
        }
        .mic-btn.thinking { border-color: #3b82f6; background: #0a0a1a; }
        .mic-btn.speaking { border-color: #10b981; background: #0a1a0a; }

        .mic-icon { font-size: 2.5rem; }

        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
            50% { box-shadow: 0 0 0 20px rgba(239,68,68,0); }
        }

        .status {
            font-size: 0.9rem; color: #9ca3af; margin-bottom: 1.5rem;
            min-height: 1.5rem;
        }
        .status.listening { color: #ef4444; }
        .status.thinking { color: #3b82f6; }
        .status.speaking { color: #10b981; }

        .transcript {
            background: #111; border-radius: 12px; padding: 1.5rem;
            text-align: left; max-height: 400px; overflow-y: auto;
            margin-bottom: 1rem;
        }
        .msg { margin-bottom: 1rem; }
        .msg .role { font-size: 0.7rem; color: #6b7280; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 1px; }
        .msg .text { font-size: 0.9rem; line-height: 1.5; }
        .msg.user .text { color: #d1d5db; }
        .msg.ai .text { color: #10b981; }
        .msg.ai .role { color: #10b981; }

        .controls {
            display: flex; gap: 0.5rem; justify-content: center;
        }
        .btn {
            padding: 8px 20px; border-radius: 9999px; font-size: 0.8rem;
            border: 1px solid #333; background: #1a1a1a; color: #fff;
            cursor: pointer; transition: all 0.2s;
        }
        .btn:hover { background: #2a2a2a; border-color: #555; }

        .waveform {
            display: flex; align-items: center; justify-content: center;
            gap: 3px; height: 40px; margin-bottom: 1rem;
        }
        .waveform .bar {
            width: 4px; background: #ef4444; border-radius: 2px;
            animation: wave 0.5s ease-in-out infinite;
        }
        .waveform .bar:nth-child(1) { animation-delay: 0s; height: 10px; }
        .waveform .bar:nth-child(2) { animation-delay: 0.1s; height: 20px; }
        .waveform .bar:nth-child(3) { animation-delay: 0.2s; height: 30px; }
        .waveform .bar:nth-child(4) { animation-delay: 0.3s; height: 20px; }
        .waveform .bar:nth-child(5) { animation-delay: 0.4s; height: 10px; }

        @keyframes wave {
            0%, 100% { transform: scaleY(1); }
            50% { transform: scaleY(2); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Clerque Voice Agent</h1>
        <p class="subtitle">Click the microphone and start talking</p>

        <div id="waveform" class="waveform" style="display:none">
            <div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div><div class="bar"></div>
        </div>

        <div class="mic-btn" id="micBtn" onclick="toggleMic()">
            <span class="mic-icon">🎙️</span>
        </div>

        <div class="status" id="status">Click microphone to start</div>

        <div class="transcript" id="transcript"></div>

        <div class="controls">
            <button class="btn" onclick="resetConversation()">Reset</button>
        </div>
    </div>

    <script>
        const DEEPGRAM_API_KEY = '""" + DEEPGRAM_API_KEY + """';

        let ws = null;
        let mediaRecorder = null;
        let dgSocket = null;
        let isListening = false;
        let audioContext = null;
        let currentAudio = null;

        // Connect to backend WebSocket
        function connectWS() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/voice-agent`);

            ws.onmessage = async (event) => {
                if (event.data instanceof Blob) {
                    // Audio data from ElevenLabs
                    playAudio(event.data);
                } else {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'status') {
                        updateStatus(msg.status);
                    } else if (msg.type === 'response_text') {
                        addMessage('ai', msg.text);
                    }
                }
            };

            ws.onclose = () => {
                setTimeout(connectWS, 2000);
            };
        }

        function toggleMic() {
            if (isListening) {
                stopListening();
            } else {
                startListening();
            }
        }

        async function startListening() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

                // Connect to Deepgram for real-time STT
                dgSocket = new WebSocket(
                    `wss://api.deepgram.com/v1/listen?model=nova-2&language=en&smart_format=true&endpointing=300&utterance_end_ms=1000`,
                    ["token", DEEPGRAM_API_KEY]
                );

                dgSocket.onopen = () => {
                    console.log('Deepgram connected');

                    // Stream microphone audio to Deepgram
                    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                    mediaRecorder.ondataavailable = (e) => {
                        if (dgSocket && dgSocket.readyState === WebSocket.OPEN && e.data.size > 0) {
                            dgSocket.send(e.data);
                        }
                    };
                    mediaRecorder.start(100); // Send chunks every 100ms
                };

                let finalTranscript = '';
                let utteranceTimer = null;

                dgSocket.onmessage = (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'Results') {
                        const transcript = data.channel?.alternatives?.[0]?.transcript || '';
                        const isFinal = data.is_final;
                        const speechFinal = data.speech_final;

                        if (transcript && isFinal) {
                            finalTranscript += (finalTranscript ? ' ' : '') + transcript;
                        }

                        // When speech ends (utterance complete), send to AI
                        if (speechFinal && finalTranscript.trim()) {
                            clearTimeout(utteranceTimer);
                            const textToSend = finalTranscript.trim();
                            finalTranscript = '';

                            addMessage('user', textToSend);

                            // Stop listening while AI responds
                            stopRecording();

                            // Send to backend
                            if (ws && ws.readyState === WebSocket.OPEN) {
                                ws.send(JSON.stringify({ type: 'transcript', text: textToSend }));
                            }
                        }
                    }

                    if (data.type === 'UtteranceEnd') {
                        if (finalTranscript.trim()) {
                            clearTimeout(utteranceTimer);
                            const textToSend = finalTranscript.trim();
                            finalTranscript = '';

                            addMessage('user', textToSend);
                            stopRecording();

                            if (ws && ws.readyState === WebSocket.OPEN) {
                                ws.send(JSON.stringify({ type: 'transcript', text: textToSend }));
                            }
                        }
                    }
                };

                dgSocket.onerror = (e) => console.error('Deepgram error:', e);
                dgSocket.onclose = () => console.log('Deepgram closed');

                isListening = true;
                updateStatus('listening');
                document.getElementById('micBtn').classList.add('listening');
                document.getElementById('waveform').style.display = 'flex';

            } catch (e) {
                console.error('Mic error:', e);
                updateStatus('Microphone access denied');
            }
        }

        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            if (dgSocket) {
                dgSocket.close();
                dgSocket = null;
            }
        }

        function stopListening() {
            stopRecording();
            isListening = false;
            document.getElementById('micBtn').classList.remove('listening', 'thinking', 'speaking');
            document.getElementById('waveform').style.display = 'none';
            updateStatus('Click microphone to start');
        }

        async function playAudio(blob) {
            try {
                if (!audioContext) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }
                const arrayBuffer = await blob.arrayBuffer();
                const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

                if (currentAudio) {
                    currentAudio.stop();
                }

                currentAudio = audioContext.createBufferSource();
                currentAudio.buffer = audioBuffer;
                currentAudio.connect(audioContext.destination);
                currentAudio.onended = () => {
                    // After AI finishes speaking, start listening again
                    updateStatus('listening');
                    document.getElementById('micBtn').classList.remove('thinking', 'speaking');
                    document.getElementById('micBtn').classList.add('listening');
                    startListening();
                };
                currentAudio.start();
            } catch (e) {
                console.error('Audio playback error:', e);
                // Fallback: start listening again
                startListening();
            }
        }

        function updateStatus(status) {
            const el = document.getElementById('status');
            const btn = document.getElementById('micBtn');
            const wave = document.getElementById('waveform');

            el.className = 'status ' + status;
            btn.classList.remove('listening', 'thinking', 'speaking');

            switch(status) {
                case 'listening':
                    el.textContent = 'Listening...';
                    btn.classList.add('listening');
                    wave.style.display = 'flex';
                    break;
                case 'thinking':
                    el.textContent = 'Thinking...';
                    btn.classList.add('thinking');
                    wave.style.display = 'none';
                    break;
                case 'speaking':
                    el.textContent = 'Speaking...';
                    btn.classList.add('speaking');
                    wave.style.display = 'none';
                    break;
                case 'done':
                    el.textContent = 'Your turn...';
                    break;
                case 'reset':
                    el.textContent = 'Conversation reset';
                    break;
                default:
                    el.textContent = status;
            }
        }

        function addMessage(role, text) {
            const div = document.getElementById('transcript');
            const msg = document.createElement('div');
            msg.className = 'msg ' + (role === 'user' ? 'user' : 'ai');
            msg.innerHTML = `<div class="role">${role === 'user' ? 'You' : 'Clerque AI'}</div><div class="text">${text}</div>`;
            div.appendChild(msg);
            div.scrollTop = div.scrollHeight;
        }

        function resetConversation() {
            document.getElementById('transcript').innerHTML = '';
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'reset' }));
            }
            stopListening();
        }

        // Initialize
        connectWS();
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)
