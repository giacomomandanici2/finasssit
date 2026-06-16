"""Ingest markdown documents into the knowledge base with chunking and embeddings."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

import tiktoken
import yaml
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.kb.models import KBChunk


@dataclass
class Chunk:
    content: str
    section: str
    heading_path: str
    content_hash: str


@dataclass
class ParsedDoc:
    document_id: str
    access_role: str
    language: str
    content: str


TOKENIZER = tiktoken.get_encoding("cl100k_base")
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def count_tokens(text: str) -> int:
    return len(TOKENIZER.encode(text))


def parse_front_matter(text: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    fm = yaml.safe_load(match.group(1))
    return fm or {}, text[match.end() :]


def read_docs(docs_dir: str) -> list[ParsedDoc]:
    docs: list[ParsedDoc] = []
    for fpath in sorted(Path(docs_dir).glob("*.md")):
        raw = fpath.read_text(encoding="utf-8")
        fm, body = parse_front_matter(raw)
        docs.append(
            ParsedDoc(
                document_id=fm.get("document_id", fpath.stem),
                access_role=fm.get("access_role", "public"),
                language=fm.get("language", "it"),
                content=body.strip(),
            )
        )
    return docs


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def chunk_document(doc: ParsedDoc, target: int = 500, overlap: int = 50) -> list[Chunk]:
    heading_pat = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = [
        (len(m.group(1)), m.group(2), m.start(), m.end())
        for m in heading_pat.finditer(doc.content)
    ]

    if not headings:
        return _split_text(doc, "", doc.content, target, overlap)

    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []

    for i, (level, title, h_start, h_end) in enumerate(headings):
        while stack and level <= stack[-1][0]:
            stack.pop()
        stack.append((level, title))

        section_text = doc.content[h_end : headings[i + 1][2] if i + 1 < len(headings) else len(doc.content)].strip()
        heading_path = " > ".join(t for _, t in stack)

        if count_tokens(section_text) <= target:
            chunks.append(
                Chunk(
                    content=section_text,
                    section=title,
                    heading_path=heading_path,
                    content_hash=_hash(section_text),
                )
            )
        else:
            chunks.extend(_split_text(doc, heading_path, section_text, target, overlap))

    return chunks


def _split_text(
    doc: ParsedDoc,
    heading_path: str,
    text: str,
    target: int,
    overlap: int,
) -> list[Chunk]:
    if count_tokens(text) <= target:
        section = heading_path.split(" > ")[-1] if heading_path else ""
        return [
            Chunk(
                content=text,
                section=section,
                heading_path=heading_path,
                content_hash=_hash(text),
            )
        ]

    blocks = re.split(r"\n\s*\n", text)
    if len(blocks) == 1:
        return _split_by_sentences(heading_path, text, target)

    chunks: list[Chunk] = []
    buffer: list[str] = []
    overlap_text: str = ""

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        proposed = "\n\n".join(buffer + [block]) if buffer else block

        if count_tokens(proposed) <= target:
            buffer.append(block)
        else:
            if buffer:
                chunk_text = "\n\n".join(buffer)
                _add_chunk(chunks, chunk_text, heading_path)
                overlap_text = _take_last_tokens(chunk_text, overlap)
            buffer = [block]

    if buffer:
        if overlap_text:
            buffer.insert(0, overlap_text)
        chunk_text = "\n\n".join(buffer)
        _add_chunk(chunks, chunk_text, heading_path)

    return chunks


def _split_by_sentences(heading_path: str, text: str, target: int) -> list[Chunk]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[Chunk] = []
    buffer: list[str] = []

    for sent in sentences:
        proposed = " ".join(buffer + [sent]) if buffer else sent
        if count_tokens(proposed) <= target:
            buffer.append(sent)
        else:
            if buffer:
                _add_chunk(chunks, " ".join(buffer), heading_path)
            buffer = [sent]

    if buffer:
        _add_chunk(chunks, " ".join(buffer), heading_path)

    return chunks


def _add_chunk(chunks: list[Chunk], content: str, heading_path: str) -> None:
    section = heading_path.split(" > ")[-1] if heading_path else ""
    chunks.append(
        Chunk(
            content=content,
            section=section,
            heading_path=heading_path,
            content_hash=_hash(content),
        )
    )


def _take_last_tokens(text: str, n: int) -> str:
    tokens = TOKENIZER.encode(text)
    if len(tokens) <= n:
        return text
    return TOKENIZER.decode(tokens[-n:])


async def get_existing_hashes(session: AsyncSession) -> set[str]:
    result = await session.execute(select(KBChunk.content))
    return {_hash(row[0]) for row in result.scalars()}


async def get_embeddings(
    client: AsyncOpenAI,
    texts: list[str],
    model: str,
    batch_size: int = 100,
) -> list[list[float]]:
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(model=model, input=batch)
        all_embeddings.extend([e.embedding for e in response.data])
    return all_embeddings


async def run(
    docs_dir: str,
    database_url: str,
    openai_api_key: str,
    model: str,
    target_tokens: int,
    overlap_tokens: int,
    batch_size: int,
) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    client = AsyncOpenAI(api_key=openai_api_key)

    docs = read_docs(docs_dir)
    print(f"Found {len(docs)} document(s)")

    all_chunks: list[tuple[ParsedDoc, Chunk]] = []
    for doc in docs:
        for c in chunk_document(doc, target=target_tokens, overlap=overlap_tokens):
            all_chunks.append((doc, c))

    async with session_factory() as session:
        existing = await get_existing_hashes(session)

    new_chunks = [(d, c) for d, c in all_chunks if c.content_hash not in existing]

    print(f"Total chunks: {len(all_chunks)}, new: {len(new_chunks)}")

    if not new_chunks:
        print("Nothing to ingest")
        return

    texts = [c.content for _, c in new_chunks]
    embeddings = await get_embeddings(client, texts, model, batch_size)

    async with session_factory() as session:
        for (doc, chunk), embedding in zip(new_chunks, embeddings):
            session.add(
                KBChunk(
                    document_id=doc.document_id,
                    section=chunk.heading_path,
                    content=chunk.content,
                    embedding=embedding,
                    access_role=doc.access_role,
                    language=doc.language,
                )
            )
        await session.commit()

    print(f"Ingested {len(new_chunks)} chunks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest markdown docs into KB")
    parser.add_argument("--docs-dir", default="docs", help="Path to markdown docs")
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://finassist:finassist_dev_password@localhost:5433/finassist",
        ),
    )
    parser.add_argument(
        "--openai-api-key",
        default=os.environ.get("OPENAI_API_KEY", ""),
    )
    parser.add_argument("--model", default="text-embedding-3-small")
    parser.add_argument("--target-tokens", type=int, default=500)
    parser.add_argument("--overlap-tokens", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=100)

    args = parser.parse_args()

    if not args.openai_api_key:
        print("Error: OPENAI_API_KEY not set. Use --openai-api-key or set the env var.")
        return

    asyncio.run(
        run(
            docs_dir=args.docs_dir,
            database_url=args.database_url,
            openai_api_key=args.openai_api_key,
            model=args.model,
            target_tokens=args.target_tokens,
            overlap_tokens=args.overlap_tokens,
            batch_size=args.batch_size,
        )
    )


if __name__ == "__main__":
    main()
