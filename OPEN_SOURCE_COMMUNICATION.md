# Open-Source Communication Alternatives (No Twilio)

This document outlines free and open-source alternatives to Twilio for voice and messaging in TradeSense.

## Why Replace Twilio?

- **Cost**: Even with student credits, Twilio costs money after credits expire
- **Vendor Lock-in**: Proprietary platform
- **Privacy**: Data passes through Twilio servers
- **Open-Source Philosophy**: TradeSense aims for complete open-source stack

## Recommended Architecture (100% Free & Open-Source)

### Option 1: WebRTC + Jitsi (Recommended for MVP)

**Best for**: Web-based voice interactions, no phone numbers needed

#### Components:
1. **Jitsi Meet** (Open-source video conferencing)
   - Free and open-source
   - WebRTC-based
   - Self-hosted or use free jitsi.org
   - Perfect for technician-to-system voice communication

2. **Simple WebRTC** (For custom implementation)
   - Use browser's native WebRTC API
   - Connect directly to Azure Speech Services
   - No intermediary servers needed

#### Implementation:
```python
# backend/voice/webrtc_handler.py
from aiortc import RTCPeerConnection, RTCSessionDescription
from azure.cognitiveservices.speech import SpeechRecognizer

class WebRTCVoiceHandler:
    """Handle WebRTC voice connections"""
    
    async def handle_offer(self, offer):
        pc = RTCPeerConnection()
        
        @pc.on("track")
        async def on_track(track):
            if track.kind == "audio":
                # Stream audio to Azure Speech Services
                await self.process_audio_stream(track)
        
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        return answer
```

#### Pros:
- ✅ 100% free
- ✅ No phone numbers needed
- ✅ Works in browser
- ✅ Low latency
- ✅ Easy integration with Azure Speech

#### Cons:
- ❌ Requires internet connection
- ❌ No traditional phone system integration
- ❌ Users need web browser or app

---

### Option 2: FreeSWITCH + Free SIP Provider (For Phone System)

**Best for**: Traditional phone system integration with real phone numbers

#### Components:
1. **FreeSWITCH** (Open-source telephony platform)
   - Self-hosted PBX
   - SIP trunking
   - IVR capabilities
   - Call recording

2. **Free SIP Providers** (for phone numbers):
   - **VoIP.ms**: $0.85/month + $0.01/min
   - **Flowroute**: Pay-as-you-go, no monthly fee
   - **Bandwidth.com**: Free trial, then pay-as-you-go
   - **Anveo**: $0.50/month + usage

#### Docker Setup:
```yaml
# docker-compose.communication.yml
version: '3.8'

services:
  freeswitch:
    image: drachtio/drachtio-freeswitch-mrf:latest
    ports:
      - "5060:5060/udp"  # SIP
      - "5080:5080/tcp"  # WebSocket
      - "16384-16394:16384-16394/udp"  # RTP
    volumes:
      - ./freeswitch/config:/etc/freeswitch
      - ./freeswitch/recordings:/var/lib/freeswitch/recordings
    environment:
      - SIP_PROVIDER_HOST=sip.voip.ms
      - SIP_PROVIDER_USER=your_username
      - SIP_PROVIDER_PASSWORD=your_password
```

#### Implementation:
```python
# backend/voice/freeswitch_handler.py
from eventsocket import EventSocket

class FreeSwitchHandler:
    """Handle FreeSWITCH events and calls"""
    
    def __init__(self):
        self.esl = EventSocket()
        self.esl.connect('localhost', 8021, 'ClueCon')
    
    async def handle_incoming_call(self, call_uuid):
        # Answer call
        self.esl.api(f'uuid_answer {call_uuid}')
        
        # Play greeting
        self.esl.api(f'uuid_broadcast {call_uuid} /path/to/greeting.wav')
        
        # Start recording
        self.esl.api(f'uuid_record {call_uuid} /recordings/{call_uuid}.wav')
        
        # Stream audio to Azure Speech
        await self.stream_to_azure_speech(call_uuid)
```

#### Pros:
- ✅ Real phone numbers
- ✅ Traditional phone system
- ✅ Open-source
- ✅ Full control
- ✅ Very low cost ($1-5/month)

#### Cons:
- ❌ Requires SIP provider (small cost)
- ❌ More complex setup
- ❌ Need to manage server

---

### Option 3: Telegram Bot API (For Notifications)

**Best for**: Notifications, alerts, and simple messaging

#### Components:
1. **Telegram Bot API** (100% free, unlimited)
   - No cost, no limits
   - Rich media support
   - Voice messages
   - File sharing

#### Implementation:
```python
# backend/notifications/telegram_bot.py
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler

class TelegramNotifier:
    """Send notifications via Telegram"""
    
    def __init__(self, bot_token):
        self.bot = Bot(token=bot_token)
    
    async def send_notification(self, chat_id, message):
        await self.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown'
        )
    
    async def send_voice_message(self, chat_id, audio_file):
        await self.bot.send_voice(
            chat_id=chat_id,
            voice=open(audio_file, 'rb')
        )
```

#### Pros:
- ✅ 100% free, unlimited
- ✅ No setup cost
- ✅ Rich features
- ✅ Mobile + desktop apps
- ✅ Voice messages supported

#### Cons:
- ❌ Requires Telegram account
- ❌ Not traditional SMS
- ❌ Not suitable for customer-facing

---

### Option 4: Discord Webhooks (For Team Communication)

**Best for**: Internal team notifications and alerts

#### Implementation:
```python
# backend/notifications/discord_notifier.py
import aiohttp

class DiscordNotifier:
    """Send notifications via Discord webhooks"""
    
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
    
    async def send_notification(self, message, embed=None):
        async with aiohttp.ClientSession() as session:
            payload = {
                "content": message,
                "embeds": [embed] if embed else []
            }
            await session.post(self.webhook_url, json=payload)
```

#### Pros:
- ✅ 100% free
- ✅ No setup required
- ✅ Rich embeds
- ✅ File attachments
- ✅ Voice channels available

#### Cons:
- ❌ Requires Discord account
- ❌ Not suitable for customers
- ❌ Team communication only

---

## Recommended Implementation Strategy

### Phase 1: MVP (WebRTC + Telegram)
```
Customer/Technician → Web Browser (WebRTC) → Azure Speech → TradeSense
                                                                    ↓
Technician Notifications ← Telegram Bot ← TradeSense
```

**Cost**: $0/month  
**Setup Time**: 1-2 days  
**Best for**: Initial development and testing

### Phase 2: Production (FreeSWITCH + WebRTC + Telegram)
```
Customer → Phone → FreeSWITCH → Azure Speech → TradeSense
                                                     ↓
Technician → Web Browser (WebRTC) → Azure Speech → TradeSense
                                                     ↓
Notifications ← Telegram Bot ← TradeSense
```

**Cost**: ~$2-5/month (SIP provider)  
**Setup Time**: 3-5 days  
**Best for**: Production deployment with phone system

---

## Updated Cost Breakdown (No Twilio)

### First Year (Using Student Credits)
| Service | Monthly Cost | Source |
|---------|--------------|--------|
| Gemini API | $0 | Free tier |
| Azure OpenAI | $0 | $100 student credit |
| Azure Speech | $0 | Included in Azure |
| DigitalOcean | $0 | $200 student credit |
| Datadog | $0 | Free 2 years (student) |
| Sentry | $0 | Free tier |
| Langfuse | $0 | Free tier |
| **WebRTC/Jitsi** | **$0** | **Free & open-source** |
| **Telegram Bot** | **$0** | **Free & unlimited** |
| **FreeSWITCH** | **$0** | **Free & open-source** |
| **SIP Provider** | **$0-2** | **Optional, VoIP.ms** |
| **Total** | **$0-2/month** | **100% open-source** |

### After Credits Expire
| Service | Monthly Cost |
|---------|--------------|
| Gemini API | $0 (free tier) |
| Azure OpenAI | ~$20-30 |
| Azure Speech | ~$5-10 |
| Hosting | ~$5-10 |
| **SIP Provider** | **$2-5** (optional) |
| **Total** | **~$32-55/month** |

**Savings vs Twilio**: $5-10/month = $60-120/year

---

## Implementation Tasks

### Task 8.4: Replace Twilio Integration

**Old (Twilio):**
```python
- [ ] 8.4 Implement Twilio integration (Python)
  - Set up Twilio SDK for voice and SMS
  - Create webhook handlers for incoming calls/messages
  - Implement call routing and IVR flow
```

**New (Open-Source):**
```python
- [ ] 8.4 Implement WebRTC + Telegram integration (Python)
  - Set up WebRTC signaling server
  - Create WebRTC audio stream handlers
  - Integrate Telegram Bot API for notifications
  - Implement voice session management
  - (Optional) Set up FreeSWITCH for phone system
```

### Task 21.3: Replace Twilio Webhooks

**Old (Twilio):**
```python
- [ ] 21.3 Implement Twilio webhook handlers (Python)
  - Create endpoints for incoming calls
  - Create endpoints for incoming SMS
  - Add signature verification for security
```

**New (Open-Source):**
```python
- [ ] 21.3 Implement WebRTC + Telegram handlers (Python)
  - Create WebRTC signaling endpoints
  - Create Telegram bot webhook handlers
  - Add WebSocket support for real-time communication
  - (Optional) Create FreeSWITCH event handlers
```

---

## Quick Start: WebRTC + Telegram Setup

### 1. Create Telegram Bot (2 minutes)

```bash
# 1. Open Telegram and search for @BotFather
# 2. Send: /newbot
# 3. Follow prompts to create bot
# 4. Copy bot token (looks like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
```

### 2. Set Up WebRTC Server (5 minutes)

```bash
# Install dependencies
pip install aiortc aiohttp python-telegram-bot

# Add to .env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 3. Test Integration

```python
# test_communication.py
import asyncio
from telegram import Bot

async def test_telegram():
    bot = Bot(token="YOUR_BOT_TOKEN")
    await bot.send_message(
        chat_id="YOUR_CHAT_ID",
        text="✅ TradeSense notification system working!"
    )

asyncio.run(test_telegram())
```

---

## Comparison Matrix

| Feature | Twilio | WebRTC + Jitsi | FreeSWITCH | Telegram |
|---------|--------|----------------|------------|----------|
| **Cost** | $5-10/mo | $0 | $2-5/mo | $0 |
| **Phone Numbers** | ✅ Yes | ❌ No | ✅ Yes | ❌ No |
| **Voice Calls** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **SMS** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Open-Source** | ❌ No | ✅ Yes | ✅ Yes | ⚠️ API only |
| **Self-Hosted** | ❌ No | ✅ Yes | ✅ Yes | ❌ No |
| **Setup Complexity** | Easy | Easy | Medium | Very Easy |
| **Data Privacy** | ⚠️ Cloud | ✅ Full | ✅ Full | ⚠️ Cloud |
| **Best For** | Production | MVP/Web | Production | Notifications |

---

## Recommendation for Your Project

**For MVP and Development:**
1. **WebRTC** for voice interactions (web-based)
2. **Telegram Bot** for notifications
3. **Total Cost**: $0/month

**For Production (if phone numbers needed):**
1. **FreeSWITCH** + **VoIP.ms** for phone system ($2-5/month)
2. **WebRTC** for web-based voice
3. **Telegram Bot** for notifications
4. **Total Cost**: $2-5/month

**Savings**: $60-120/year compared to Twilio

---

## Next Steps

1. Remove Twilio from all documentation
2. Update tasks.md with WebRTC + Telegram implementation
3. Create WebRTC signaling server
4. Set up Telegram bot
5. (Optional) Set up FreeSWITCH for phone system

Would you like me to update all the documentation files to replace Twilio with these open-source alternatives?
