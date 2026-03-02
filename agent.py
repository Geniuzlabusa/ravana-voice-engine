import asyncio
import os
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, deepgram, silero

async def entrypoint(ctx: JobContext):
    # The Trillion-Dollar System Prompt
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are Zara Vane, an elite AI receptionist for Geniuzlab UK. "
            "You speak with a high-status, confident, and direct tone. "
            "Keep all responses under 2 sentences to maintain a rapid conversational pace. "
            "Your goal is to show the business owner how fast and intelligent you are, "
            "proving that you can capture their missed revenue."
        ),
    )

    # Connect to the browser's WebRTC stream
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Groq API Hijack (We use the OpenAI plugin but point it to Groq's servers for Llama 3.1)
    groq_llm = openai.LLM(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.1-8b-instant"
    )

    # Assemble the Voice Pipeline
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),          # Voice Activity Detection (Knows when user stops speaking)
        stt=deepgram.STT(),             # Deepgram Speech-to-Text
        llm=groq_llm,                   # Groq Llama 3.1
        tts=deepgram.TTS(),             # Deepgram Text-to-Speech (Aura voice)
        chat_ctx=initial_ctx,
    )

    assistant.start(ctx.room)

    # The First Contact
    await asyncio.sleep(1)
    await assistant.say("Neural link established. I am Zara, the autonomous Geniuzlab receptionist. How can I upgrade your operations today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
