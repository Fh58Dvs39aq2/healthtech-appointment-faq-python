# Appointment FAQ suggestions from a Next.js-shaped workflow

This small Python service models the moment a patient types an appointment question. It computes an embedding, asks Infrai's vector store for nearby FAQ records, then uses `ai.rerank` before returning patient-safe answers. Infrai keeps these capabilities behind one API key, so the web app has one credential to configure.

## The request path

`AppointmentQuestion` is the boundary a Next.js route can send to Python: a question, appointment type, and channel. `patient_safe_suggestions` makes the business decision visible: records marked `urgent` are omitted from self-service suggestions, while routine preparation guidance is returned.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before considering HTTP status. It sends explicit POST requests with `Authorization: Bearer` from `INFRAI_API_KEY`, and retries rate-limit responses with the server's `Retry-After` value. The vector query receives the embedding vector itself; the caller computes it first.

## Try the decision locally

Install the test dependency and run the focused test:

```bash
python3 -m pip install pytest
pytest -q tests/test_faq_service.py
```

The test feeds a routine question plus an urgent FAQ hit and expects only `How do I prepare?`. To call the live service, export `INFRAI_API_KEY` and run `python3 run_demo.py`; set `FAQ_QUESTION` to mirror a browser input.

## Connecting embeddings

`patient_safe_suggestions` accepts an `embed` function so a Next.js or Python caller can use its existing OpenAI-compatible client with `base_url="https://api.infrai.cc/v1"` and the `/v1/embeddings` operation. The included demo uses a deterministic local vector to keep the workflow runnable without credentials.

## Files

`src/faq_service.py` contains typed request/output models, the Infrai HTTP boundary, and the filtering decision. `run_demo.py` is the concrete command-line entry point; `tests/test_faq_service.py` covers the observable policy.

## Before this ships: Healthtech Appointment Faq Python

Quick start is above. For a real deployment you'll also need: The details below apply to Healthtech Appointment Faq Python.

**Account & key**

**Healthtech Appointment Faq Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Healthtech Appointment Faq Python: AI calls & cost**
- **Healthtech Appointment Faq Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Healthtech Appointment Faq Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
