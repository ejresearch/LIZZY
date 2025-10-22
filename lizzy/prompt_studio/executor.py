"""
Prompt Studio Executor

Takes prompts built by Prompt Studio and executes them with LLMs.
Does NOT modify the original automated/interactive brainstorm modules.

This is a thin wrapper that sends custom prompts to LLMs and returns results.
"""

import os
from typing import Optional, Dict, Any
from openai import AsyncOpenAI
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    """Result of executing a prompt"""
    success: bool
    response: str
    model: str
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None
    error: Optional[str] = None


class PromptExecutor:
    """
    Executes prompts built by Prompt Studio.

    This is separate from automated/interactive brainstorm - it's a simple
    executor that takes any prompt and sends it to an LLM.
    """

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key)

    async def execute(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_message: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a prompt with an LLM.

        Args:
            prompt: The assembled prompt from Prompt Studio
            model: Which model to use (gpt-4o, gpt-4o-mini, etc.)
            temperature: Creativity (0.0-1.0)
            max_tokens: Maximum response length
            system_message: Optional system message

        Returns:
            ExecutionResult with response and metadata
        """

        # Default system message for screenplay work
        if system_message is None:
            system_message = """You are an expert screenplay consultant with deep knowledge of:
- Story structure and beat engineering
- Dialogue and dramatic theory
- Visual storytelling and execution

Provide detailed, actionable feedback based on the context provided."""

        try:
            # Call OpenAI
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract response
            content = response.choices[0].message.content

            # Calculate cost estimate
            tokens_used = response.usage.total_tokens if response.usage else None
            cost = self._estimate_cost(model, tokens_used) if tokens_used else None

            return ExecutionResult(
                success=True,
                response=content,
                model=model,
                tokens_used=tokens_used,
                cost_estimate=cost
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                response="",
                model=model,
                error=str(e)
            )

    def _estimate_cost(self, model: str, tokens: int) -> float:
        """
        Estimate cost based on model and tokens.

        Rough estimates (as of 2025):
        - gpt-4o: $5/1M input, $15/1M output (average ~$10/1M)
        - gpt-4o-mini: $0.15/1M input, $0.60/1M output (average ~$0.40/1M)
        """
        cost_per_1m = {
            "gpt-4o": 10.0,
            "gpt-4o-mini": 0.40,
            "gpt-4-turbo": 10.0,
            "gpt-3.5-turbo": 0.50,
        }

        rate = cost_per_1m.get(model, 10.0)  # Default to gpt-4o rate
        return (tokens / 1_000_000) * rate


class BrainstormExecutor:
    """
    Specialized executor for brainstorming tasks.

    Uses prompts from Prompt Studio to generate scene ideas, dialogue,
    character development, etc. Does NOT modify the original brainstorm modules.
    """

    def __init__(self):
        self.executor = PromptExecutor()

    async def generate_scene_ideas(
        self,
        prompt: str,
        model: str = "gpt-4o",
        num_ideas: int = 3
    ) -> ExecutionResult:
        """
        Generate scene ideas based on a Prompt Studio prompt.

        Args:
            prompt: Assembled prompt from Prompt Studio
            model: Which model to use
            num_ideas: How many ideas to generate

        Returns:
            ExecutionResult with scene ideas
        """

        enhanced_prompt = f"""{prompt}

Based on the above context, generate {num_ideas} distinct scene ideas or approaches. For each idea:

1. **Core Concept**: What's the main dramatic beat?
2. **Visual Approach**: How would this look on screen?
3. **Dialogue Flavor**: What's the tone of the conversation?
4. **Why It Works**: How does this serve the story?

Be specific and actionable."""

        return await self.executor.execute(
            prompt=enhanced_prompt,
            model=model,
            temperature=0.8,  # Higher for creativity
            max_tokens=2000
        )

    async def analyze_scene(
        self,
        prompt: str,
        model: str = "gpt-4o"
    ) -> ExecutionResult:
        """
        Analyze a scene based on Prompt Studio context.

        Args:
            prompt: Assembled prompt from Prompt Studio
            model: Which model to use

        Returns:
            ExecutionResult with analysis
        """

        enhanced_prompt = f"""{prompt}

Analyze this scene and provide:

1. **Structural Analysis**: How does this fit in the overall story arc?
2. **Character Dynamics**: What are the key relationship tensions?
3. **Pacing**: Is this the right moment for this beat?
4. **Suggestions**: What could make this scene stronger?

Be detailed and reference specific story elements."""

        return await self.executor.execute(
            prompt=enhanced_prompt,
            model=model,
            temperature=0.5,  # Lower for analytical work
            max_tokens=2000
        )

    async def get_expert_feedback(
        self,
        prompt: str,
        focus_area: str,
        model: str = "gpt-4o"
    ) -> ExecutionResult:
        """
        Get expert feedback on a specific aspect.

        Args:
            prompt: Assembled prompt from Prompt Studio
            focus_area: What to focus on (dialogue, structure, visual, etc.)
            model: Which model to use

        Returns:
            ExecutionResult with expert feedback
        """

        enhanced_prompt = f"""{prompt}

Focus specifically on: **{focus_area}**

Provide expert guidance on this aspect, including:
- What's working well
- What could be improved
- Specific techniques or approaches to try
- Examples or references that might help

Be practical and actionable."""

        return await self.executor.execute(
            prompt=enhanced_prompt,
            model=model,
            temperature=0.6,
            max_tokens=2000
        )


# Convenience function for quick execution
async def execute_prompt(
    prompt: str,
    execution_type: str = "general",
    **kwargs
) -> ExecutionResult:
    """
    Quick helper to execute a prompt.

    Args:
        prompt: Assembled prompt from Prompt Studio
        execution_type: Type of execution (general, ideas, analysis, feedback)
        **kwargs: Additional arguments

    Returns:
        ExecutionResult
    """

    if execution_type == "ideas":
        executor = BrainstormExecutor()
        return await executor.generate_scene_ideas(prompt, **kwargs)

    elif execution_type == "analysis":
        executor = BrainstormExecutor()
        return await executor.analyze_scene(prompt, **kwargs)

    elif execution_type == "feedback":
        executor = BrainstormExecutor()
        focus = kwargs.pop('focus_area', 'general screenplay writing')
        return await executor.get_expert_feedback(prompt, focus, **kwargs)

    else:
        # General execution
        executor = PromptExecutor()
        return await executor.execute(prompt, **kwargs)
