"""
Bucket Manager - Create and populate LightRAG buckets.
"""

import asyncio
import os
from pathlib import Path
from typing import List
from lightrag import LightRAG
from lightrag.llm.openai import openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import setup_logger
from openai import AsyncOpenAI

setup_logger("lightrag", level="INFO")


# Custom GPT-5-mini completion function for LightRAG
async def gpt_5_1_complete(
    prompt: str,
    system_prompt: str = None,
    history_messages: list = None,
    **kwargs
) -> str:
    """GPT-5.1 completion function compatible with LightRAG."""
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model="gpt-5.1",
        messages=messages,
        temperature=kwargs.get("temperature", 0.7),
        max_completion_tokens=kwargs.get("max_tokens", 2000)
    )

    return response.choices[0].message.content


async def create_bucket(bucket_name: str, bucket_dir: Path) -> LightRAG:
    """
    Create a new LightRAG bucket.

    Args:
        bucket_name: Name of the bucket (for logging)
        bucket_dir: Directory path for the bucket

    Returns:
        Initialized LightRAG instance

    Example:
        rag = await create_bucket("books", Path("./rag_buckets/books"))
    """
    print(f"🔧 Creating bucket: {bucket_name}")
    print(f"   Location: {bucket_dir}")

    # Ensure directory exists
    bucket_dir.mkdir(parents=True, exist_ok=True)

    # Initialize LightRAG with official pattern
    rag = LightRAG(
        working_dir=str(bucket_dir),
        embedding_func=openai_embed,
        llm_model_func=gpt_5_1_complete,
    )

    # CRITICAL: Both initialization calls required!
    await rag.initialize_storages()
    await initialize_pipeline_status()

    print(f"✅ Bucket '{bucket_name}' created and initialized\n")
    return rag


async def populate_bucket(
    rag: LightRAG,
    bucket_name: str,
    source_files: List[Path],
    verbose: bool = True
) -> dict:
    """
    Populate a bucket with documents.

    Args:
        rag: Initialized LightRAG instance
        bucket_name: Name of bucket (for logging)
        source_files: List of file paths to insert
        verbose: Print progress messages

    Returns:
        Dictionary with stats: {
            'total': int,
            'inserted': int,
            'failed': int,
            'skipped': int
        }

    Example:
        files = list(Path("./books").glob("*.docx"))
        stats = await populate_bucket(rag, "books", files)
    """
    stats = {
        'total': len(source_files),
        'inserted': 0,
        'failed': 0,
        'skipped': 0
    }

    if verbose:
        print(f"📚 Populating '{bucket_name}' with {len(source_files)} files\n")

    for i, file_path in enumerate(source_files, 1):
        try:
            if verbose:
                print(f"[{i}/{len(source_files)}] {file_path.name}")

            # Read file content
            content = read_file(file_path)

            if not content or not content.strip():
                if verbose:
                    print(f"  ⚠️  Empty file, skipping")
                stats['skipped'] += 1
                continue

            # Insert into RAG
            await rag.ainsert(content)
            stats['inserted'] += 1

            if verbose:
                print(f"  ✅ Inserted ({len(content):,} chars)\n")

        except Exception as e:
            stats['failed'] += 1
            if verbose:
                print(f"  ❌ Error: {e}\n")
            continue

    if verbose:
        print(f"\n{'='*60}")
        print(f"Bucket '{bucket_name}' population complete:")
        print(f"  Total files: {stats['total']}")
        print(f"  Inserted: {stats['inserted']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"{'='*60}\n")

    return stats


def read_file(file_path: Path) -> str:
    """
    Read content from a file (supports .txt, .docx).

    Args:
        file_path: Path to file

    Returns:
        File content as string

    Raises:
        Exception if file cannot be read
    """
    if file_path.suffix.lower() == '.docx':
        # Handle Word documents
        from docx import Document
        doc = Document(file_path)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    else:
        # Handle text files
        return file_path.read_text(encoding='utf-8')


async def create_and_populate_bucket(
    bucket_name: str,
    bucket_dir: Path,
    source_files: List[Path],
    verbose: bool = True
) -> tuple[LightRAG, dict]:
    """
    Create a new bucket and populate it with files (convenience function).

    Args:
        bucket_name: Name of the bucket
        bucket_dir: Directory for the bucket
        source_files: Files to insert
        verbose: Print progress

    Returns:
        Tuple of (rag_instance, stats_dict)

    Example:
        files = list(Path("/Users/elle/Desktop/books").glob("*.docx"))
        rag, stats = await create_and_populate_bucket(
            "books",
            Path("./rag_buckets/books"),
            files
        )
        await rag.finalize_storages()
    """
    # Create bucket
    rag = await create_bucket(bucket_name, bucket_dir)

    # Populate bucket
    stats = await populate_bucket(rag, bucket_name, source_files, verbose)

    return rag, stats


# Convenience sync wrapper
def create_and_populate_bucket_sync(
    bucket_name: str,
    bucket_dir: Path,
    source_files: List[Path],
    verbose: bool = True
) -> dict:
    """
    Synchronous wrapper for create_and_populate_bucket.

    Returns:
        Stats dictionary

    Example:
        from pathlib import Path
        from backend.bucket_manager import create_and_populate_bucket_sync

        files = list(Path("./books").glob("*.docx"))
        stats = create_and_populate_bucket_sync(
            "books",
            Path("./rag_buckets/books"),
            files
        )
    """
    async def _run():
        rag, stats = await create_and_populate_bucket(
            bucket_name, bucket_dir, source_files, verbose
        )
        await rag.finalize_storages()
        return stats

    return asyncio.run(_run())


def install_bucket(source_path: Path, bucket_name: str = None, overwrite: bool = False) -> dict:
    """
    Install a pre-built LightRAG bucket from another location.

    This copies an existing, fully-processed LightRAG bucket directory
    into your rag_buckets/ folder, allowing you to use buckets from
    other projects (like ender2) without reprocessing.

    Args:
        source_path: Path to existing LightRAG bucket directory
        bucket_name: Name for installed bucket (defaults to source dir name)
        overwrite: If True, overwrite existing bucket with same name

    Returns:
        Dictionary with stats: {
            'bucket_name': str,
            'files_copied': int,
            'total_size_mb': float,
            'destination': Path
        }

    Raises:
        FileNotFoundError: If source_path doesn't exist
        ValueError: If destination exists and overwrite=False
        Exception: If bucket validation fails

    Example:
        from pathlib import Path
        from backend.bucket_manager import install_bucket

        # Install bucket from ender2
        stats = install_bucket(
            source_path=Path("/path/to/ender2/rag_buckets/romcom_films"),
            bucket_name="films",
            overwrite=False
        )
        print(f"Installed {stats['files_copied']} files ({stats['total_size_mb']:.2f} MB)")
    """
    import shutil

    if not source_path.exists():
        raise FileNotFoundError(f"Source path not found: {source_path}")

    if not source_path.is_dir():
        raise ValueError(f"Source path is not a directory: {source_path}")

    # Validate it's a LightRAG bucket
    required_files = [
        "graph_chunk_entity_relation.graphml",
        "kv_store_full_docs.json",
        "vdb_chunks.json"
    ]

    missing = [f for f in required_files if not (source_path / f).exists()]

    if missing:
        raise Exception(
            f"Source directory is not a valid LightRAG bucket. "
            f"Missing files: {', '.join(missing)}"
        )

    # Determine bucket name
    if bucket_name is None:
        bucket_name = source_path.name

    # Setup destination
    dest = Path(f"./rag_buckets/{bucket_name}")

    if dest.exists():
        if not overwrite:
            raise ValueError(
                f"Bucket '{bucket_name}' already exists. "
                f"Set overwrite=True to replace it."
            )
        shutil.rmtree(dest)

    # Copy bucket
    shutil.copytree(source_path, dest)

    # Gather stats
    files = list(dest.glob("*"))
    total_size = sum(f.stat().st_size for f in files if f.is_file())

    return {
        'bucket_name': bucket_name,
        'files_copied': len(files),
        'total_size_mb': total_size / 1024 / 1024,
        'destination': dest
    }
