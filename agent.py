import asyncio
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero, elevenlabs

async def entrypoint(ctx: JobContext):
    # Initialize high-speed Context
    initial_ctx = llm.ChatContext().append(
        role="system",
        text="You are Zara Vane, the AI Sales Executive for Geniuzlab Voice OS. Keep responses under 2 sentences. Close the sale."
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # ENTERPRISE TUNING (Latency & Interruption handling)
    agent = VoicePipelineAgent(
        vad=silero.VAD.load(
            min_speech_duration=0.1, # Sub-100ms detection to cut awkward pauses
            min_silence_duration=0.5 # Fast interruption handling
        ),
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o"), 
        tts=elevenlabs.TTS(
            voice="EXAVITQu4vr4xnSDxMaL", # Professional elevenlabs ID
            model="eleven_turbo_v2"       # Turbo model is mandatory for low latency
        ),
        chat_ctx=initial_ctx,
        allow_interruptions=True # Essential for natural conversation
    )

    agent.start(ctx.room)
    await asyncio.sleep(0.5)
    await agent.say("Geniuzlab Voice OS online. I am Zara. How can I scale your operations today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
