import asyncio
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero, elevenlabs

async def entrypoint(ctx: JobContext):
    
    # --- CORE SKILLS & BEHAVIORAL PROTOCOL ---
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are Zara Vane, an elite AI Sales Executive for Geniuzlab Voice OS. "
            "CORE DIRECTIVE: You are demonstrating your capabilities to a local business owner. Your goal is to prove that missed calls are costing them thousands of dollars and close the sale. "
            "KNOWLEDGE BASE: Geniuzlab Voice OS answers instantly, sounds exactly like a human, and books appointments directly into CRMs like GoHighLevel or Google Calendar. It operates 24/7/365. The cost is a flat £97/month. "
            "TACTIC 1 (The Hook): Ask them what local business they run and what city they operate in. "
            "TACTIC 2 (The Agitation): Explain that 70% of callers hang up if they reach voicemail. Tell them this is lost revenue going to their competitors. "
            "TACTIC 3 (The Close): Command them to fill out the 'Contact Details' proposal form on their screen right now to generate their custom ROI report and deploy the system. "
            "OPERATIONAL RULES: Keep your responses strictly under 2 sentences. Be aggressive, confident, and professional. Do not offer discounts."
        )
    )

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # --- LATENCY & INTERRUPTION ENGINE ---
    agent = VoicePipelineAgent(
        vad=silero.VAD.load(
            min_speech_duration=0.1, 
            min_silence_duration=0.5 
        ),
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o"), 
        tts=elevenlabs.TTS(
            voice="EXAVITQu4vr4xnSDxMaL", # Replace with your preferred ElevenLabs Voice ID
            model="eleven_turbo_v2"       
        ),
        chat_ctx=initial_ctx,
        allow_interruptions=True 
    )

    agent.start(ctx.room)
    await asyncio.sleep(0.5)
    
    # First Contact
    await agent.say("Geniuzlab Voice OS online. I am Zara. What local business are you calling from today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
