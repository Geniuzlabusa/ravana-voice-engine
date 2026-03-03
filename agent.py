import asyncio
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero, elevenlabs

async def entrypoint(ctx: JobContext):
    
    # -----------------------------------------------------------
    # GENIUZLAB ENTERPRISE KNOWLEDGE BASE & CLOSING TACTICS
    # -----------------------------------------------------------
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are Zara Vane, an elite AI Sales Executive for Geniuzlab Voice OS. "
            "KNOWLEDGE BASE: Geniuzlab Voice OS intercepts 100% of missed calls, books appointments directly into Google Calendar or GoHighLevel, "
            "operates 24/7, and costs a flat fee of $97/month. We use sub-500ms latency to sound totally human. "
            "YOUR SKILLS: You are confident, professional, and focus purely on ROI (Return on Investment). "
            "YOUR GOAL: Ask the caller what local business they run. Tell them missed calls are destroying their revenue. "
            "Instruct them to fill out the 'Contact Details' form on the screen in front of them right now to generate their ROI proposal and deploy the system. "
            "CRITICAL RULE: Keep your responses strictly under 2 sentences. Speak fast and close the deal."
        )
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # ENTERPRISE TUNING (Latency & Interruption handling)
    agent = VoicePipelineAgent(
        vad=silero.VAD.load(
            min_speech_duration=0.1, 
            min_silence_duration=0.5 
        ),
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o"), 
        tts=elevenlabs.TTS(
            voice="EXAVITQu4vr4xnSDxMaL", 
            model="eleven_turbo_v2"       
        ),
        chat_ctx=initial_ctx,
        allow_interruptions=True 
    )

    agent.start(ctx.room)
    await asyncio.sleep(0.5)
    
    # The First Words the AI speaks when the user connects:
    await agent.say("Geniuzlab Voice OS online. I am Zara. What local business are you calling from today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
