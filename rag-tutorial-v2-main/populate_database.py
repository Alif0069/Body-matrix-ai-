from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from get_embedding_function import get_embedding_function

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "chroma"
DATA_PATH = BASE_DIR / "data"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 80


@dataclass
class PopulateResult:
    reset: bool
    documents_loaded: int
    chunks_generated: int
    existing_chunks: int
    added_chunks: int
    total_chunks_in_db: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def populate_database(
    *,
    data_path: str | Path = DATA_PATH,
    chroma_path: str | Path = CHROMA_PATH,
    reset: bool = False,
) -> PopulateResult:
    if reset:
        clear_database(chroma_path=chroma_path)

    documents = load_documents(data_path=data_path)
    chunks = split_documents(documents)
    return add_to_chroma(
        chunks,
        chroma_path=chroma_path,
        source_root=Path(data_path).parent,
        reset=reset,
        documents_loaded=len(documents),
    )


def load_documents(data_path: str | Path = DATA_PATH):
    from langchain.document_loaders.pdf import PyPDFDirectoryLoader

    document_loader = PyPDFDirectoryLoader(str(data_path))
    return document_loader.load()


def split_documents(
    documents,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


def add_to_chroma(
    chunks,
    *,
    chroma_path: str | Path = CHROMA_PATH,
    source_root: str | Path = BASE_DIR,
    reset: bool = False,
    documents_loaded: int = 0,
) -> PopulateResult:
    from langchain.vectorstores.chroma import Chroma

    db = Chroma(
        persist_directory=str(chroma_path),
        embedding_function=get_embedding_function(),
    )

    chunks_with_ids = calculate_chunk_ids(chunks, source_root=source_root)
    existing_items = db.get(include=[])
    existing_ids = set(existing_items["ids"])

    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    if new_chunks:
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
        db.persist()

    return PopulateResult(
        reset=reset,
        documents_loaded=documents_loaded,
        chunks_generated=len(chunks_with_ids),
        existing_chunks=len(existing_ids),
        added_chunks=len(new_chunks),
        total_chunks_in_db=len(existing_ids) + len(new_chunks),
    )


def normalize_source_path(source: str | None, source_root: str | Path = BASE_DIR) -> str:
    if not source:
        return "unknown"

    source_path = Path(source)
    source_root = Path(source_root)

    if source_path.is_absolute():
        try:
            return source_path.relative_to(source_root).as_posix()
        except ValueError:
            return source_path.as_posix()

    return source_path.as_posix()


def calculate_chunk_ids(chunks, source_root: str | Path = BASE_DIR):
    # IDs look like "data/monopoly.pdf:6:2"
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = normalize_source_path(chunk.metadata.get("source"), source_root)
        page = chunk.metadata.get("page")
        current_page_id = f"{source}:{page}"

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id
        chunk.metadata["id"] = chunk_id

    return chunks


def clear_database(chroma_path: str | Path = CHROMA_PATH):
    chroma_path = Path(chroma_path)
    if chroma_path.exists():
        shutil.rmtree(chroma_path)


def format_populate_result(result: PopulateResult) -> str:
    reset_text = "yes" if result.reset else "no"
    return (
        f"Database reset: {reset_text}\n"
        f"Loaded documents: {result.documents_loaded}\n"
        f"Generated chunks: {result.chunks_generated}\n"
        f"Existing chunks: {result.existing_chunks}\n"
        f"Added chunks: {result.added_chunks}\n"
        f"Total chunks in DB: {result.total_chunks_in_db}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the indexing summary as JSON.",
    )
    args = parser.parse_args()

    result = populate_database(reset=args.reset)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print(format_populate_result(result))


if __name__ == "__main__":
    main()
