from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.core.db import create_db_and_tables, engine
from app.routers import (
    agreements,
    analysis,
    confirm,
    conversations,
    evaluation,
    evidence,
    health,
    share,
    stamp,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLES_DIR = Path(__file__).parent / "data" / "samples"


def seed_samples() -> None:
    """Load app/data/samples/*.txt once, so the demo dropdown is populated
    on a fresh database. Idempotent: ingest() dedupes on the file hash."""
    if not SAMPLES_DIR.exists():
        return

    with Session(engine) as session:
        for path in sorted(SAMPLES_DIR.glob("*.txt")):
            # "T01_clear_deal.txt" -> "T01 clear deal"
            label = path.stem.replace("_", " ")
            try:
                conversation, _, deduplicated = conversations.ingest(
                    session,
                    raw=path.read_bytes(),
                    filename=path.name,
                    is_sample=True,
                    sample_label=label,
                )
            except Exception:
                logger.exception("Could not seed sample %s", path.name)
                session.rollback()
                continue

            if not deduplicated:
                logger.info("Seeded sample %s (id=%s)", label, conversation.id)

        session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_samples()
    yield


app = FastAPI(
    title="Handshake to Contract",
    description=(
        "Turns an informal WhatsApp chat into a clear, confirmable record. "
        "Decision support, not legal advice."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(conversations.router)
app.include_router(analysis.router)
app.include_router(agreements.router)
app.include_router(confirm.router)
app.include_router(evidence.router)
app.include_router(share.owner_router)
app.include_router(share.public_router)
app.include_router(stamp.router)
app.include_router(evaluation.router)
