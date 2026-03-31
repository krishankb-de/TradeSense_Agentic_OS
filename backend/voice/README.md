# TradeSense Voice Processing Module

This module provides Azure Speech Services integration for speech-to-text (STT) and text-to-speech (TTS) functionality optimized for field service environments.

## Features

### Speech-to-Text (STT)
- **Streaming transcription** with <500ms first-token latency
- **Continuous recognition** for long-form audio
- **Noise suppression** optimized for field environments
- **Automatic punctuation** and capitalization
- **Profanity filtering** (configurable)
- **Multi-language support** (20+ languages)

### Text-to-Speech (TTS)
- **Neural voice synthesis** with natural-sounding voices
- **Multiple neural voices** (21 en-US voices + international)
- **Voice customization** (pitch, rate, volume, style)
- **SSML support** for advanced control
- **Sub-second synthesis latency** (250-800ms typical)
- **Streaming synthesis** for long text

### Configuration

Set the following environment variables in your `.env` file:

```bash
# Azure Speech Services
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=eastus
AZURE_SPEECH_LANGUAGE=en-US
AZURE_SPEECH_VOICE=en-US-JennyNeural
USE_AZURE_SPEECH=true
```

### Quick Start

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Test Configuration

```bash
python backend/examples/test_azure_stt.py
```

#### 3. Start FastAPI Server

```bash
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Test API Endpoints

**Health Check:**
```bash
curl http://localhost:8000/api/v1/voice/health
```

**Transcribe Audio File:**
```bash
curl -X POST http://localhost:8000/api/v1/voice/transcribe \
  -F "audio=@test.wav" \
  -F "language=en-US"
```

**Get Supported Languages:**
```bash
curl http://localhost:8000/api/v1/voice/languages
```

### API Endpoints

#### `GET /api/v1/voice/health`
Health check endpoint for voice services.

**Response:**
```json
{
  "status": "healthy",
  "azure_speech_configured": true,
  "supported_languages": ["en-US", "es-ES", "fr-FR", ...]
}
```

#### `POST /api/v1/voice/transcribe`
Transcribe an audio file to text.

**Parameters:**
- `audio` (file): Audio file (WAV, MP3, OGG)
- `language` (string): Language code (default: "en-US")
- `enable_profanity_filter` (bool): Enable profanity filtering (default: true)
- `enable_dictation` (bool): Enable dictation mode (default: true)

**Response:**
```json
{
  "text": "Hello world, this is a test.",
  "confidence": 0.95,
  "duration": 2.5,
  "latency": 450.2,
  "language": "en-US"
}
```

#### `WS /api/v1/voice/transcribe/stream`
WebSocket endpoint for streaming audio transcription.

**Protocol:**
1. Client connects to WebSocket
2. Client sends audio chunks as binary data
3. Server sends back JSON messages:
   - `{"type": "partial", "text": "...", "confidence": 0.8}`
   - `{"type": "final", "text": "...", "confidence": 0.95}`
   - `{"type": "error", "message": "..."}`

**Example Client (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/voice/transcribe/stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'partial') {
    console.log('Partial:', data.text);
  } else if (data.type === 'final') {
    console.log('Final:', data.text);
  }
};

// Send audio chunks
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) => {
      ws.send(event.data);
    };
    mediaRecorder.start(100); // Send chunks every 100ms
  });
```

#### `GET /api/v1/voice/languages`
Get list of supported languages.

**Response:**
```json
{
  "languages": ["en-US", "en-GB", "es-ES", "fr-FR", ...],
  "default": "en-US"
}
```

#### `POST /api/v1/voice/synthesize`
Synthesize text to speech (returns metadata only).

**Request Body:**
```json
{
  "text": "Hello world",
  "voice_name": "en-US-JennyNeural",
  "style": "neutral",
  "pitch": "+0%",
  "rate": "+0%",
  "volume": "+0%"
}
```

**Response:**
```json
{
  "success": true,
  "duration": 1.45,
  "latency": 280.67,
  "voice_name": "en-US-JennyNeural",
  "audio_size": 5892,
  "error_message": null
}
```

#### `POST /api/v1/voice/synthesize/audio`
Synthesize text to speech and return audio data.

**Request Body:**
```json
{
  "text": "Hello world",
  "voice_name": "en-US-JennyNeural",
  "style": "cheerful",
  "pitch": "+5%",
  "rate": "+10%",
  "volume": "+0%"
}
```

**Response:**
- Content-Type: `audio/mpeg`
- Headers:
  - `X-Audio-Duration`: Audio duration in seconds
  - `X-Synthesis-Latency`: Processing latency in milliseconds
  - `X-Voice-Name`: Voice used for synthesis

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/voice/synthesize/audio \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice_name": "en-US-JennyNeural"}' \
  --output speech.mp3
```

#### `GET /api/v1/voice/voices`
Get list of available neural voices.

**Query Parameters:**
- `language` (optional): Filter by language code (e.g., "en-US")

**Response:**
```json
{
  "voices": [
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "en-US-AriaNeural",
    ...
  ],
  "default_voice": "en-US-JennyNeural",
  "language": "en-US"
}
```

### Python Usage

#### Single-Shot Transcription

```python
from voice.stt import create_azure_stt
from core.config import settings

# Create STT client
stt = create_azure_stt(
    subscription_key=settings.azure_speech_key,
    region=settings.azure_speech_region,
    language="en-US"
)

# Transcribe audio file
audio_config = stt.create_audio_config_from_file("audio.wav")
result = await stt.transcribe_once(audio_config=audio_config)

print(f"Transcription: {result.text}")
print(f"Confidence: {result.confidence}")
print(f"Duration: {result.duration}s")
```

#### Streaming Transcription

```python
from voice.stt import create_azure_stt

# Create STT client
stt = create_azure_stt(
    subscription_key="your_key",
    region="eastus",
    language="en-US"
)

# Define callbacks
def on_recognizing(evt):
    print(f"Partial: {evt.result.text}")

def on_recognized(evt):
    print(f"Final: {evt.result.text}")

# Start streaming
recognizer = await stt.transcribe_stream(
    callback_recognizing=on_recognizing,
    callback_recognized=on_recognized
)

# ... keep running ...

# Stop when done
stt.stop_recognition(recognizer)
```

### Supported Languages

The module supports 20+ languages including:
- English: en-US, en-GB, en-AU, en-CA, en-IN
- Spanish: es-ES, es-MX
- French: fr-FR, fr-CA
- German: de-DE
- Italian: it-IT
- Portuguese: pt-BR, pt-PT
- Chinese: zh-CN, zh-TW
- Japanese: ja-JP
- Korean: ko-KR
- Russian: ru-RU
- Arabic: ar-SA
- Hindi: hi-IN

### Performance Targets

- **First-token latency**: <500ms (target)
- **End-to-end latency**: <600ms (p95)
- **Turn-taking accuracy**: >95%
- **Noise robustness**: Optimized for 60dB+ environments

### Error Handling

The module includes comprehensive error handling:
- **Network errors**: Automatic retry with exponential backoff
- **Audio format errors**: Clear error messages
- **API quota errors**: Graceful degradation
- **Timeout handling**: Configurable timeouts

### Testing

Run the test suite:

```bash
pytest backend/tests/test_voice_stt.py -v
```

Run with coverage:

```bash
pytest backend/tests/test_voice_stt.py --cov=voice --cov-report=html
```

### Troubleshooting

**Issue: "Azure Speech Services is not enabled"**
- Solution: Set `USE_AZURE_SPEECH=true` in `.env`

**Issue: "Azure Speech Services credentials not configured"**
- Solution: Set `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in `.env`

**Issue: High latency (>500ms)**
- Check network connection to Azure
- Verify region is geographically close
- Consider using smaller audio chunks

**Issue: Poor transcription accuracy**
- Ensure audio quality is good (16kHz, 16-bit recommended)
- Check microphone placement
- Verify correct language is selected
- Enable dictation mode for better punctuation

### Cost Optimization

Azure Speech Services pricing (with GitHub Student Pack):
- **Free tier**: 5 audio hours/month
- **Student credit**: $100 credit (covers ~500 hours)
- **Pay-as-you-go**: $1/hour after free tier

Tips to minimize costs:
1. Use free tier for development
2. Enable caching for repeated queries
3. Use shorter audio chunks
4. Implement client-side VAD to reduce silence processing

### Next Steps

1. ✅ **Implemented TTS** (Text-to-Speech) in `backend/voice/tts.py`
2. Add VAD (Voice Activity Detection) for better turn-taking
3. Integrate with agent orchestration layer
4. Add voice biometrics for technician verification
5. Implement voice command recognition

### Documentation

- **STT Implementation**: See `backend/voice/IMPLEMENTATION_SUMMARY.md`
- **TTS Implementation**: See `backend/voice/TTS_IMPLEMENTATION.md`
- **API Reference**: See API endpoints section above

### References

- [Azure Speech Services Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/)
- [Azure Speech SDK for Python](https://docs.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/)
- [GitHub Student Pack](https://education.github.com/pack)
