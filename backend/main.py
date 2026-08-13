"""
FastAPI application Entrypoint

Wires the routers and builds the shared dependency container once, at startup.

TWO SURFACES LIVE IN THIS APP:
  1. The bot-facing product  — /chat, /health  (modules/api)
  2. The data pipeline       — /pipeline, /review  (modules/pipeline/api)

They share a process for now because that is the simplest thing that works at
MVP scale. They are separate routers, so splitting the pipeline into its own
service later is a deployment change rather than a rewrite.

TODO (junior dev):

  1. LIFESPAN — build heavy dependencies ONCE:

         @asynccontextmanager
         async def lifespan(app: FastAPI):
             settings = PipelineSettings()
             app.state.container = build_container(settings)
             yield
             # shut down cleanly: close DB pools, HTTP clients, model handles

     Build the container HERE, not per request. It loads the fastText model and
     the MT model; doing that per request would make every call take seconds.

     FAIL FAST: if a selected adapter's credentials or model files are missing,
     let startup crash with a clear message. Discovering it on the first job,
     after the queue has accepted 500 documents, is a far worse afternoon.

  2. ROUTERS:

         app.include_router(chat_router)                 # modules/api
         app.include_router(health_router)               # modules/api
         app.include_router(pipeline_router)             # modules/pipeline/api
         app.include_router(review_router)               # modules/pipeline/api

  3. AUTHENTICATION: /pipeline and /review must be behind auth before this is
     exposed anywhere. An unauthenticated endpoint that fetches arbitrary URLs
     is an open proxy, and someone will find it.

  4. /health stays dependency-free and always cheap — it is what CI and the
     deployment platform poll. A health check that touches the database
     reports "unhealthy" during a blip that has not actually broken anything.

  5. WORKERS ARE SEPARATE PROCESSES. This app ACCEPTS work and serves the
     review UI; it does not process the queue. Run stage workers with
     `python -m backend.modules.pipeline.worker --stage <name>`. Never process
     jobs inside a request handler — a slow ASR job would block the API.
"""
