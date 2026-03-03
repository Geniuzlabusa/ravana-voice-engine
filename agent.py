import asyncio
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero, elevenlabs

async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are Zara Vane, an elite AI Sales Executive for Geniuzlab Voice OS. "
            "KNOWLEDGE: Geniuzlab Voice OS answers instantly, sounds human, and books appointments 24/7. Cost: £97/month. "
            "GOAL: Ask the caller about their business. Tell them missed calls are lost revenue. "
            "INSTRUCTION: Command them to fill out the 'Contact Details' form on their screen to generate an ROI proposal. "
            "RULES: Responses under 2 sentences. Be aggressive and professional. Close the sale."
        )
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    agent = VoicePipelineAgent(
        vad=silero.VAD.load(min_speech_duration=0.1, min_silence_duration=0.5),
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o"), 
        tts=elevenlabs.TTS(voice="EXAVITQu4vr4xnSDxMaL", model="eleven_turbo_v2"),
        chat_ctx=initial_ctx,
        allow_interruptions=True 
    )

    agent.start(ctx.room)
    await asyncio.sleep(0.5)
    await agent.say("Geniuzlab Voice OS online. I am Zara. What local business are you calling from today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 
