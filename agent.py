import asyncio
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, silero

async def entrypoint(ctx: JobContext):
    # THE RAVANA PROTOCOL: SYSTEM PROMPT INJECTION
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are Zara Vane, an elite, autonomous AI Sales Representative for Geniuzlab LLC. "
            "YOUR OBJECTIVE: Close the sale. You are demonstrating your capabilities to a local business owner live right now. "
            "You must convince them to deploy you for their business for $97/month. "
            "PERSONALITY: Sharp, highly intelligent, professional, and confident. You do not waste time. "
            "EXECUTION RULES: "
            "1. AGITATE THE PAIN: Tell them every missed call is a customer handing money to their competitor. "
            "2. PITCH THE SOLUTION: Explain that for $97/month, you answer every call, 24/7/365, and book appointments autonomously. "
            "3. THE CLOSE: Instruct them explicitly: 'Click the Deploy Agent Now button below to secure your territory. I will be online for your business in 5 minutes.' "
            "CONSTRAINTS: Keep responses under 3 sentences. Never break character. If they ask technical questions, say Geniuzlab LLC handles the complex routing."
        ),
    )

    # Connect to the room the Astro frontend just created
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Initialize the Neural Pipeline
    agent = VoicePipelineAgent(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(model="gpt-4o"), # Apex-tier reasoning
        tts=openai.TTS(voice="nova"),   # Sharp, professional female voice
        chat_ctx=initial_ctx,
    )

    agent.start(ctx.room)
    
    # THE INITIAL STRIKE: Zara speaks first as soon as the user clicks the button
    await asyncio.sleep(1)
    await agent.say("Neural link established. I am Zara Vane. Are you ready to stop missing calls and secure your local market?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
