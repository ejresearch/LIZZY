"""
RAG-based blocks for Prompt Studio - query LightRAG knowledge graph buckets.
"""

import os
from typing import Optional, List
from lightrag import LightRAG, QueryParam
from openai import AsyncOpenAI
from .base import Block


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


class BooksQueryBlock(Block):
    """
    Query the 'books' RAG bucket.

    Expert: Structure and beat engineering
    """

    def __init__(self, query: str, mode: str = "hybrid", block_id: str = None):
        super().__init__(block_id)
        self.query = query
        self.mode = mode  # naive, local, global, hybrid

    def execute(self, project_name: str, **kwargs) -> str:
        bucket_path = f"rag_buckets/{project_name}/books"

        if not os.path.exists(bucket_path):
            return f"[Books bucket not found at {bucket_path}]"

        # Initialize LightRAG
        rag = LightRAG(
            working_dir=bucket_path,
            llm_model_func=gpt_5_1_complete
        )

        # Query
        result = rag.query(
            self.query,
            param=QueryParam(mode=self.mode)
        )

        output = ["BOOKS EXPERT (Structure & Beat Engineering):"]
        output.append(f"Query: {self.query}")
        output.append(f"Mode: {self.mode}")
        output.append("\nResponse:")
        output.append(result)

        return "\n".join(output)

    def get_description(self) -> str:
        return f"Books bucket query: '{self.query[:50]}...' (mode: {self.mode})"

    def validate(self) -> tuple[bool, Optional[str]]:
        if not self.query or len(self.query.strip()) == 0:
            return (False, "Query cannot be empty")
        if self.mode not in ["naive", "local", "global", "hybrid"]:
            return (False, f"Invalid mode: {self.mode}")
        return (True, None)


class PlaysQueryBlock(Block):
    """
    Query the 'plays' RAG bucket.

    Expert: Dialogue and dramatic theory
    """

    def __init__(self, query: str, mode: str = "hybrid", block_id: str = None):
        super().__init__(block_id)
        self.query = query
        self.mode = mode

    def execute(self, project_name: str, **kwargs) -> str:
        bucket_path = f"rag_buckets/{project_name}/plays"

        if not os.path.exists(bucket_path):
            return f"[Plays bucket not found at {bucket_path}]"

        rag = LightRAG(
            working_dir=bucket_path,
            llm_model_func=gpt_5_1_complete
        )

        result = rag.query(
            self.query,
            param=QueryParam(mode=self.mode)
        )

        output = ["PLAYS EXPERT (Dialogue & Dramatic Theory):"]
        output.append(f"Query: {self.query}")
        output.append(f"Mode: {self.mode}")
        output.append("\nResponse:")
        output.append(result)

        return "\n".join(output)

    def get_description(self) -> str:
        return f"Plays bucket query: '{self.query[:50]}...' (mode: {self.mode})"

    def validate(self) -> tuple[bool, Optional[str]]:
        if not self.query or len(self.query.strip()) == 0:
            return (False, "Query cannot be empty")
        if self.mode not in ["naive", "local", "global", "hybrid"]:
            return (False, f"Invalid mode: {self.mode}")
        return (True, None)


class ScriptsQueryBlock(Block):
    """
    Query the 'scripts' RAG bucket.

    Expert: Visual storytelling and execution
    """

    def __init__(self, query: str, mode: str = "hybrid", block_id: str = None):
        super().__init__(block_id)
        self.query = query
        self.mode = mode

    def execute(self, project_name: str, **kwargs) -> str:
        bucket_path = f"rag_buckets/{project_name}/scripts"

        if not os.path.exists(bucket_path):
            return f"[Scripts bucket not found at {bucket_path}]"

        rag = LightRAG(
            working_dir=bucket_path,
            llm_model_func=gpt_5_1_complete
        )

        result = rag.query(
            self.query,
            param=QueryParam(mode=self.mode)
        )

        output = ["SCRIPTS EXPERT (Visual Storytelling & Execution):"]
        output.append(f"Query: {self.query}")
        output.append(f"Mode: {self.mode}")
        output.append("\nResponse:")
        output.append(result)

        return "\n".join(output)

    def get_description(self) -> str:
        return f"Scripts bucket query: '{self.query[:50]}...' (mode: {self.mode})"

    def validate(self) -> tuple[bool, Optional[str]]:
        if not self.query or len(self.query.strip()) == 0:
            return (False, "Query cannot be empty")
        if self.mode not in ["naive", "local", "global", "hybrid"]:
            return (False, f"Invalid mode: {self.mode}")
        return (True, None)


class MultiExpertQueryBlock(Block):
    """
    Query all three RAG buckets with the same query and combine results.

    This mimics the three-expert system used in brainstorming.
    """

    def __init__(self, query: str, mode: str = "hybrid", block_id: str = None):
        super().__init__(block_id)
        self.query = query
        self.mode = mode

    def execute(self, project_name: str, **kwargs) -> str:
        output = ["MULTI-EXPERT QUERY:"]
        output.append(f"Query: {self.query}")
        output.append(f"Mode: {self.mode}")
        output.append("\n" + "=" * 80 + "\n")

        # Query all three buckets
        books_block = BooksQueryBlock(self.query, self.mode)
        plays_block = PlaysQueryBlock(self.query, self.mode)
        scripts_block = ScriptsQueryBlock(self.query, self.mode)

        books_result = books_block.execute(project_name, **kwargs)
        output.append(books_result)
        output.append("\n" + "=" * 80 + "\n")

        plays_result = plays_block.execute(project_name, **kwargs)
        output.append(plays_result)
        output.append("\n" + "=" * 80 + "\n")

        scripts_result = scripts_block.execute(project_name, **kwargs)
        output.append(scripts_result)

        return "\n".join(output)

    def get_description(self) -> str:
        return f"Multi-expert query (all 3 buckets): '{self.query[:50]}...'"

    def validate(self) -> tuple[bool, Optional[str]]:
        if not self.query or len(self.query.strip()) == 0:
            return (False, "Query cannot be empty")
        if self.mode not in ["naive", "local", "global", "hybrid"]:
            return (False, f"Invalid mode: {self.mode}")
        return (True, None)
