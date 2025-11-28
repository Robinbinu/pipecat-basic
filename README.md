## Pipecat Basic Voice Agent

Real-time WebRTC demo that routes audio through Pipecat, Gemini Live, and a FastAPI backend. This repo now ships with a production-friendly Docker image and Railway configuration so you can run the agent locally or deploy it with minimal setup.

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) or `pip`
- A Google Gemini API key with realtime access (`GOOGLE_API_KEY`)

Create a `.env` file (or define environment variables in your shell/host) with:

```
GOOGLE_API_KEY=your-key-here
```

### Local development

Install dependencies and run the FastAPI server (defaults to port 7860):

```bash
uv pip install -r requirements.txt  # or: pip install -r requirements.txt
uv run server.py                    # or: uvicorn server:app --host 0.0.0.0 --port 7860
```

Browse to `http://localhost:7860` and click **Connect** to start the WebRTC session.

### Docker

Build and run the container locally. The container entrypoint respects the `PORT` variable (defaults to `7860`).

```bash
docker build -t pipecat-basic .
docker run --rm -p 7860:7860 \
	-e GOOGLE_API_KEY=$GOOGLE_API_KEY \
	pipecat-basic
```

### Railway deployment

Railway automatically detects `railway.toml` and builds with the included `Dockerfile`:

1. Install the [Railway CLI](https://railway.com/docs/cli/installation) and log in.
2. Create a project: `railway init` and link it to this repo.
3. Set the required env var: `railway variables set GOOGLE_API_KEY=...`.
4. Deploy: `railway up`.

Railway injects the `PORT` variable; the container command will bind to `0.0.0.0:${PORT}` automatically.

### Useful commands

```bash
# Run FastAPI server with auto-reload
uvicorn server:app --reload --port 7860
```
