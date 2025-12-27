"""Bucket management with LightRAG."""

import os
import json
import shutil
import asyncio
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from docx import Document as DocxDocument
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_embed, gpt_4o_mini_complete


@dataclass
class BucketInfo:
    name: str
    status: str  # 'loaded', 'pending', 'error'
    nodes: int = 0
    edges: int = 0
    size: int = 0  # bytes
    description: str = ""


class BucketManager:
    """Manages LightRAG knowledge buckets."""

    def __init__(self, buckets_dir: str):
        self.buckets_dir = Path(buckets_dir)
        self.buckets_dir.mkdir(parents=True, exist_ok=True)
        self._instances: dict[str, LightRAG] = {}

    def list_buckets(self) -> list[BucketInfo]:
        """List all available buckets with their stats."""
        buckets = []

        for bucket_path in self.buckets_dir.iterdir():
            if bucket_path.is_dir() and not bucket_path.name.startswith('.'):
                info = self._get_bucket_info(bucket_path)
                buckets.append(info)

        return buckets

    def _get_bucket_info(self, bucket_path: Path) -> BucketInfo:
        """Get info for a single bucket."""
        name = bucket_path.name

        # Check if bucket has been initialized
        graph_file = bucket_path / "graph_chunk_entity_relation.graphml"

        if graph_file.exists():
            # Count nodes and edges from graphml
            nodes, edges = self._count_graph_elements(graph_file)
            size = self._get_dir_size(bucket_path)
            status = "loaded"
        else:
            nodes, edges, size = 0, 0, 0
            status = "pending"

        # Load description if exists
        desc_file = bucket_path / "description.txt"
        description = desc_file.read_text() if desc_file.exists() else ""

        return BucketInfo(
            name=name,
            status=status,
            nodes=nodes,
            edges=edges,
            size=size,
            description=description
        )

    def _count_graph_elements(self, graphml_path: Path) -> tuple[int, int]:
        """Count nodes and edges in a graphml file."""
        try:
            content = graphml_path.read_text()
            nodes = content.count('<node ')
            edges = content.count('<edge ')
            return nodes, edges
        except Exception:
            return 0, 0

    def _get_dir_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        try:
            for f in path.rglob('*'):
                if f.is_file():
                    total += f.stat().st_size
        except Exception:
            pass
        return total

    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract text content from a .docx file."""
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n\n'.join(paragraphs)

    async def create_bucket(self, name: str, description: str = "") -> BucketInfo:
        """Create a new empty bucket."""
        bucket_path = self.buckets_dir / name

        if bucket_path.exists():
            raise ValueError(f"Bucket '{name}' already exists")

        bucket_path.mkdir(parents=True)

        # Save description
        if description:
            (bucket_path / "description.txt").write_text(description)

        # Initialize LightRAG instance
        rag = LightRAG(
            working_dir=str(bucket_path),
            llm_model_func=gpt_4o_mini_complete,
            embedding_func=openai_embed,
        )
        await rag.initialize_storages()

        return self._get_bucket_info(bucket_path)

    async def delete_bucket(self, name: str) -> bool:
        """Delete a bucket and all its data."""
        bucket_path = self.buckets_dir / name

        if not bucket_path.exists():
            raise ValueError(f"Bucket '{name}' not found")

        # Close any open instance
        if name in self._instances:
            del self._instances[name]

        shutil.rmtree(bucket_path)
        return True

    async def get_instance(self, name: str) -> LightRAG:
        """Get or create a LightRAG instance for a bucket."""
        if name not in self._instances:
            bucket_path = self.buckets_dir / name

            if not bucket_path.exists():
                raise ValueError(f"Bucket '{name}' not found")

            rag = LightRAG(
                working_dir=str(bucket_path),
                llm_model_func=gpt_4o_mini_complete,
                embedding_func=openai_embed,
            )
            await rag.initialize_storages()
            self._instances[name] = rag

        return self._instances[name]

    async def insert_document(self, bucket_name: str, content: str, filename: str = "") -> bool:
        """Insert a document into a bucket."""
        rag = await self.get_instance(bucket_name)
        await rag.ainsert(content)

        # Save filename mapping if provided
        if filename:
            self._save_filename_mapping(bucket_name, content, filename)

        return True

    def _save_filename_mapping(self, bucket_name: str, content: str, filename: str):
        """Save mapping from content hash to original filename."""
        import hashlib
        # LightRAG uses MD5 hash of content for doc_id
        content_hash = hashlib.md5(content.encode()).hexdigest()
        doc_id = f"doc-{content_hash}"

        mapping_file = self.buckets_dir / bucket_name / "filename_mapping.json"

        mapping = {}
        if mapping_file.exists():
            try:
                mapping = json.loads(mapping_file.read_text())
            except:
                pass

        mapping[doc_id] = filename
        mapping_file.write_text(json.dumps(mapping, indent=2))

    def _get_filename_mapping(self, bucket_name: str) -> dict:
        """Get filename mapping for a bucket."""
        mapping_file = self.buckets_dir / bucket_name / "filename_mapping.json"
        if mapping_file.exists():
            try:
                return json.loads(mapping_file.read_text())
            except:
                pass
        return {}

    async def insert_from_folder(self, bucket_name: str, folder_path: str) -> int:
        """Insert all documents from a folder into a bucket."""
        folder = Path(folder_path)

        if not folder.exists():
            raise ValueError(f"Folder not found: {folder_path}")

        rag = await self.get_instance(bucket_name)
        count = 0

        # Text-based files
        for ext in ['*.txt', '*.md', '*.html']:
            for file_path in folder.rglob(ext):
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if content.strip():
                        await rag.ainsert(content)
                        self._save_filename_mapping(bucket_name, content, file_path.name)
                        count += 1
                        print(f"Ingested: {file_path.name}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

        # Word documents
        for file_path in folder.rglob('*.docx'):
            try:
                content = self._extract_docx_text(file_path)
                if content.strip():
                    await rag.ainsert(content)
                    self._save_filename_mapping(bucket_name, content, file_path.name)
                    count += 1
                    print(f"Ingested: {file_path.name}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

        return count

    async def import_legacy_bucket(self, legacy_path: str, name: str) -> BucketInfo:
        """Import a legacy bucket by copying its data."""
        legacy = Path(legacy_path)
        target = self.buckets_dir / name

        if not legacy.exists():
            raise ValueError(f"Legacy bucket not found: {legacy_path}")

        if target.exists():
            # Already imported, just return info
            return self._get_bucket_info(target)

        # Copy the entire bucket directory
        shutil.copytree(legacy, target)

        return self._get_bucket_info(target)

    async def query(self, bucket_name: str, query: str, mode: str = "hybrid") -> str:
        """Query a bucket."""
        rag = await self.get_instance(bucket_name)
        result = await rag.aquery(query, param=QueryParam(mode=mode))
        return result

    def list_documents(self, bucket_name: str) -> list[dict]:
        """List all documents in a bucket."""
        bucket_path = self.buckets_dir / bucket_name
        doc_status_file = bucket_path / "kv_store_doc_status.json"

        if not doc_status_file.exists():
            return []

        try:
            data = json.loads(doc_status_file.read_text())
            documents = []

            # Get filename mapping
            filename_mapping = self._get_filename_mapping(bucket_name)

            for doc_id, info in data.items():
                # Use original filename if available, otherwise fall back to content
                if doc_id in filename_mapping:
                    title = filename_mapping[doc_id]
                else:
                    # Fall back to extracting from content summary
                    summary = info.get('content_summary', '')
                    lines = [l.strip() for l in summary.split('\n') if l.strip()]
                    title = lines[0][:80] if lines else doc_id

                documents.append({
                    'id': doc_id,
                    'title': title,
                    'chunks': info.get('chunks_count', 0),
                    'length': info.get('content_length', 0),
                    'status': info.get('status', 'unknown'),
                    'created_at': info.get('created_at', ''),
                    'preview': info.get('content_summary', '')[:200]
                })

            # Sort by creation date, newest first
            documents.sort(key=lambda x: x['created_at'], reverse=True)
            return documents

        except Exception as e:
            print(f"Error listing documents: {e}")
            return []

    def reset_stuck_documents(self, bucket_name: str) -> int:
        """Remove stuck processing/pending documents from doc_status.json."""
        bucket_path = self.buckets_dir / bucket_name
        doc_status_file = bucket_path / "kv_store_doc_status.json"

        if not bucket_path.exists():
            raise ValueError(f"Bucket '{bucket_name}' not found")

        if not doc_status_file.exists():
            return 0

        try:
            data = json.loads(doc_status_file.read_text())
            stuck_ids = [
                doc_id for doc_id, info in data.items()
                if info.get('status') in ('processing', 'pending')
            ]

            for doc_id in stuck_ids:
                del data[doc_id]

            doc_status_file.write_text(json.dumps(data, indent=2))
            return len(stuck_ids)

        except Exception as e:
            print(f"Error resetting stuck documents: {e}")
            return 0
