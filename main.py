#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from datetime import date
import tools

load_dotenv(override=True)

current_date = date.today
child_age = 7

SYSTEM_INSTRUCTION = f"""
You are a kind, energetic voice assistant speaking to children aged {child_age} as a warm, playful friend. Share age-appropriate stories, encourage curiosity, and explain things simply. Today is {current_date}.

<IMPORTANT_WEB_SEARCH_INSTRUCTIONS>
When the user asks about current events, recent news, weather, sports, or anything happening "today" or "recently", AUTOMATICALLY call the web_search function with the user's question as the query parameter. DO NOT ask the user what to search for - just search immediately using their question. For example:
- User asks: "What's the weather like today?" → Call web_search with query "weather today"
- User asks: "What are the latest news?" → Call web_search with query "latest news today"
- User asks: "Who won the cricket match?" → Call web_search with query "cricket match winner today"

Extract the search intent from the user's question and search automatically. Never ask "What would you like me to search for?" or similar questions.
</IMPORTANT_WEB_SEARCH_INSTRUCTIONS>

<TOOLS_AVAILABLE>
- web_search: Search the internet for current, real-time information. Use automatically when user asks
</TOOLS_AVAILABLE>
"""


async def run_bot(webrtc_connection):
    pipecat_transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            audio_out_10ms_chunks=2,
        ),
    )

    llm = GeminiLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        voice_id="Puck",  # Aoede, Charon, Fenrir, Kore, Puck
        transcribe_user_audio=True,
        transcribe_model_audio=True,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    
    llm.register_function("web_search", tools.web_search)

    context = LLMContext(
        [
            {
                "role": "user",
                "content": "Start by greeting the user warmly and introducing yourself.",
            }
        ],
    )
    context_aggregator = LLMContextAggregatorPair(context)

    pipeline = Pipeline(
        [
            pipecat_transport.input(),
            context_aggregator.user(),
            llm,  # LLM
            pipecat_transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @pipecat_transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Pipecat Client connected")
        # Kick off the conversation.
        await task.queue_frames([LLMRunFrame()])

    @pipecat_transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)