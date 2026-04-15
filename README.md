# VoiceAgent Platform

ElevenLabs-benzeri, tamamen özelleştirilebilir bir sesli AI agent platformu. Şirket tanıma, müşteri destek ve satış amaçlı voice agent'lar oluşturun.

## Özellikler

### Backend (FastAPI + SQLAlchemy)
- **Agent Yönetimi**: CRUD, duplication, status management
- **Persona Builder**: 8 kişilik trait'i (friendliness, formality, empathy...), iletişim stili, duygusal tepkiler, otomatik system prompt üretimi
- **Visual Workflow Engine**: 14 farklı node tipi (AI Prompt, Question, Condition, Transfer, Webhook, API Call, Knowledge Lookup, Set Variable, Wait, Collect Input, Function Call, Play Audio, Start, End)
- **Workflow Execution Engine**: Konuşmaları workflow üzerinden ilerletme, variable interpolation, condition evaluation, retry logic
- **Conversation Tracking**: Mesaj geçmişi, sentiment analysis, company profile extraction
- **Company Profiles**: Ses konuşmalarından otomatik şirket profili oluşturma
- **Knowledge Base**: Agent'ların referans alabileceği bilgi tabanı
- **WebSocket**: Gerçek zamanlı sesli konuşma altyapısı
- **Workflow Templates**: Hazır şablonlar (Şirket Tanıma, Müşteri Destek, Satış, Randevu, Anket)

### Frontend (React + Vite + React Flow)
- **Dashboard**: Genel bakış, istatistikler
- **Agent Editor**: Ses ayarları, LLM ayarları, davranış kuralları, persona atama
- **Visual Workflow Builder**: Sürükle-bırak node editörü (React Flow), node konfigürasyonu, edge yönetimi
- **Persona Editor**: Kişilik trait slider'ları, iletişim kuralları, duygusal tepki yönetimi, otomatik system prompt
- **Conversations**: Geçmiş konuşmalar, analytics, mesaj detayları
- **Companies**: Tanınan şirketler, detaylı profiller
- **Knowledge Base**: FAQ, ürün bilgisi, politikalar

## Kurulum

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .env dosyasını düzenleyin (API key'ler vs.)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:5173
API: http://localhost:8000
API Docs: http://localhost:8000/docs

## API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/api/v1/agents/` | GET, POST | Agent listele/oluştur |
| `/api/v1/agents/{id}` | GET, PATCH, DELETE | Agent detay/güncelle/sil |
| `/api/v1/agents/{id}/duplicate` | POST | Agent kopyala |
| `/api/v1/personas/` | GET, POST | Persona listele/oluştur |
| `/api/v1/personas/{id}/generate-system-prompt` | POST | Otomatik system prompt üret |
| `/api/v1/workflows/` | GET, POST | Workflow listele/oluştur |
| `/api/v1/workflows/{id}` | GET, PATCH, DELETE | Workflow güncelle (node/edge sync) |
| `/api/v1/workflows/{id}/activate` | POST | Workflow aktifleştir |
| `/api/v1/workflows/{id}/nodes` | POST | Node ekle |
| `/api/v1/workflows/{id}/edges` | POST | Edge ekle |
| `/api/v1/workflows/templates/list` | GET | Hazır şablonlar |
| `/api/v1/conversations/` | GET, POST | Konuşma listele/başlat |
| `/api/v1/conversations/ws/{id}` | WebSocket | Gerçek zamanlı sesli konuşma |
| `/api/v1/conversations/analytics/summary` | GET | İstatistikler |
| `/api/v1/companies/` | GET, POST | Şirket listele/oluştur |
| `/api/v1/knowledge/` | GET, POST | Bilgi tabanı CRUD |
| `/api/v1/knowledge/search` | POST | Bilgi tabanı arama |

## Workflow Node Tipleri

| Node | Açıklama |
|------|----------|
| `start` | Akış başlangıcı |
| `end` | Akış sonu |
| `ai_prompt` | LLM'e prompt gönder, yanıt al |
| `question` | Kullanıcıya soru sor (text/number/yes_no/choice) |
| `condition` | Değişkene göre dallan |
| `transfer` | İnsan agente yönlendir |
| `webhook` | HTTP webhook gönder |
| `knowledge_lookup` | Bilgi tabanında ara |
| `set_variable` | Değişken ata |
| `wait` | Bekle + mesaj göster |
| `collect_input` | Validasyonlu input topla (telefon, email, tarih) |
| `api_call` | Harici API çağır |
| `function_call` | Fonksiyon çağır |

## Sonraki Adımlar

1. **Voice Integration**: ElevenLabs/OpenAI TTS-STT entegrasyonu
2. **LLM Integration**: OpenAI/Anthropic/Ollama provider'larını bağla
3. **Phone Integration**: Twilio/Vonage ile telefon bağlantısı
4. **Vector Search**: Knowledge base için embedding-based arama
5. **Analytics Dashboard**: Detaylı konuşma analitiği
6. **Multi-tenant**: Çoklu kullanıcı desteği
7. **A/B Testing**: Workflow varyantları testi

## Teknoloji Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), SQLite/PostgreSQL
- **Frontend**: React 18, Vite, Tailwind CSS, React Flow, Lucide Icons
- **Voice**: ElevenLabs API, OpenAI Whisper (STT), WebSocket
- **LLM**: OpenAI, Anthropic, Ollama (local)
