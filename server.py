#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import argparse
import asyncio
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger
from pipecat.transports.smallwebrtc.connection import (IceServer,
                                                       SmallWebRTCConnection)
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCPatchRequest, SmallWebRTCRequest, SmallWebRTCRequestHandler)

from main import run_bot

# Load environment variables
load_dotenv(override=True)

# Backend ICE configuration (used by Pipecat)
TURN_SERVER_URL = os.getenv("TURN_SERVER_URL", "").strip()
TURN_USERNAME = os.getenv("TURN_USERNAME", "").strip()
TURN_PASSWORD = os.getenv("TURN_PASSWORD", "").strip()
DEFAULT_STUN = os.getenv("STUN_URL", "stun:stun.l.google.com:19302").strip()

ice_servers = []

if TURN_SERVER_URL:
    ice_servers.append(
        IceServer(
            urls=TURN_SERVER_URL,
            username=TURN_USERNAME,
            credential=TURN_PASSWORD,
        )
    )

if DEFAULT_STUN:
    ice_servers.append(IceServer(urls=DEFAULT_STUN))

# Browser ICE configuration (defaults to Google stun, optionally includes TURN)
ICE_SERVER_CONFIG: list[dict] = []

if DEFAULT_STUN:
    ICE_SERVER_CONFIG.append({"urls": [DEFAULT_STUN]})

if TURN_SERVER_URL:
    turn_config = {"urls": [TURN_SERVER_URL]}
    if TURN_USERNAME:
        turn_config["username"] = TURN_USERNAME
    if TURN_PASSWORD:
        turn_config["credential"] = TURN_PASSWORD
    ICE_SERVER_CONFIG.append(turn_config)

if not ICE_SERVER_CONFIG:
    ICE_SERVER_CONFIG.append({"urls": ["stun:stun.l.google.com:19302"]})

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the SmallWebRTC request handler
small_webrtc_handler: SmallWebRTCRequestHandler = SmallWebRTCRequestHandler(ice_servers)


@app.post("/api/offer")
async def offer(request: Request):
    """Offer endpoint for handling voice agent connections.

    Args:
        request: The request to handle
    """
    request_json = await request.json()
    
    # Filter keys to avoid TypeError
    allowed_keys = {"sdp", "type", "pc_id", "restart_pc", "request_data", "requestData"}
    filtered_data = {k: v for k, v in request_json.items() if k in allowed_keys}
    
    webrtc_request = SmallWebRTCRequest.from_dict(filtered_data)

    async def start_bot(connection):
        asyncio.create_task(run_bot(connection))

    answer = await small_webrtc_handler.handle_web_request(
        webrtc_request,
        start_bot
    )

    return answer



@app.patch("/api/offer")
async def ice_candidate(request: SmallWebRTCPatchRequest):
    logger.debug(f"Received patch request: {request}")
    await small_webrtc_handler.handle_patch_request(request)
    return {"status": "success"}


@app.get("/")
async def serve_index():
    return FileResponse("index.html")


@app.get("/api/config")
async def rtc_config():
    """Expose ICE server configuration to the browser client."""

    return {"iceServers": ICE_SERVER_CONFIG}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # Run app
    await small_webrtc_handler.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC demo")
    parser.add_argument(
        "--host", default="localhost", help="Host for HTTP server (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=7860, help="Port for HTTP server (default: 7860)"
    )
    parser.add_argument("--verbose", "-v", action="count")
    args = parser.parse_args()

    logger.remove(0)
    if args.verbose:
        logger.add(sys.stderr, level="TRACE")
    else:
        logger.add(sys.stderr, level="DEBUG")

    uvicorn.run(app, host=args.host, port=args.port)