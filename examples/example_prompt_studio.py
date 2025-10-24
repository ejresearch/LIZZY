#!/usr/bin/env python3
"""
Example: Using Prompt Studio

Demonstrates how to compose prompts from blocks.
"""

import sys
import os

# Add lizzy to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lizzy.prompt_studio import PromptEngine, assemble_prompt
from lizzy.prompt_studio.blocks import (
    SceneBlock,
    CharacterBiosBlock,
    ProjectMetadataBlock,
    BooksQueryBlock,
    TextBlock,
    SectionHeaderBlock,
)


def example_1_basic():
    """Example 1: Basic prompt with scene + characters"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Prompt (Scene + Characters)")
    print("="*80 + "\n")

    blocks = [
        SectionHeaderBlock(title="SCENE CONTEXT"),
        SceneBlock(scene_number=1),
        SectionHeaderBlock(title="CHARACTER INFORMATION"),
        CharacterBiosBlock(),
    ]

    prompt = assemble_prompt(blocks, project_name="The Proposal 2.0")
    print(prompt)
    print(f"\n[Total: {len(prompt)} characters]")


def example_2_with_rag():
    """Example 2: Scene + RAG query"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Scene with Expert Guidance")
    print("="*80 + "\n")

    blocks = [
        SectionHeaderBlock(title="CURRENT SCENE"),
        SceneBlock(scene_number=5),
        SectionHeaderBlock(title="EXPERT GUIDANCE"),
        TextBlock("Please analyze this scene for structural elements."),
        BooksQueryBlock(
            query="romantic comedy scene structure and pacing",
            mode="hybrid"
        ),
    ]

    engine = PromptEngine()
    result = engine.assemble(blocks, project_name="The Proposal 2.0")

    # Show preview (first 1000 chars)
    preview = result.prompt[:1000] + "\n\n... [truncated]" if len(result.prompt) > 1000 else result.prompt
    print(preview)

    print(f"\n[Stats]")
    print(f"Total chars: {result.total_chars}")
    print(f"Execution time: {result.total_execution_time_ms:.2f}ms")
    print(f"Blocks executed: {len(result.metadata)}")


def example_3_custom_workflow():
    """Example 3: Custom workflow with templates"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Custom Workflow (Project Analysis)")
    print("="*80 + "\n")

    from lizzy.prompt_studio.blocks import TemplateBlock

    blocks = [
        SectionHeaderBlock(title="PROJECT OVERVIEW"),
        ProjectMetadataBlock(),

        SectionHeaderBlock(title="ANALYSIS REQUEST"),
        TemplateBlock(
            template="""
You are analyzing the project "{project_name}".

Task: Review the story spine and identify:
1. Potential weak points in the narrative arc
2. Character development opportunities
3. Structural improvements

Focus on: {focus_area}
            """,
            variables={'focus_area': 'Act 2 pacing'}
        ),
    ]

    prompt = assemble_prompt(blocks, project_name="The Proposal 2.0")
    print(prompt)


def example_4_metadata_tracking():
    """Example 4: Using metadata for performance tracking"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Metadata Tracking")
    print("="*80 + "\n")

    blocks = [
        SceneBlock(scene_number=1),
        CharacterBiosBlock(),
        BooksQueryBlock(query="meet-cute techniques", mode="local"),
    ]

    engine = PromptEngine()
    result = engine.assemble(blocks, project_name="The Proposal 2.0")

    print("Block Execution Metadata:\n")
    for meta in result.metadata:
        print(f"Block: {meta.block_type}")
        print(f"  ID: {meta.block_id}")
        print(f"  Time: {meta.execution_time_ms:.2f}ms")
        print(f"  Size: {meta.data_size_chars} chars")
        if meta.error:
            print(f"  Error: {meta.error}")
        print()

    print(f"Total execution time: {result.total_execution_time_ms:.2f}ms")
    print(f"Total prompt size: {result.total_chars} chars")


def example_5_conditional_blocks():
    """Example 5: Conditional block composition"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Conditional Blocks (Scene Context)")
    print("="*80 + "\n")

    from lizzy.prompt_studio.blocks import PreviousSceneBlock, NextSceneBlock

    def build_scene_prompt(scene_num: int):
        """Build a smart prompt that includes context based on scene number"""
        blocks = [
            SectionHeaderBlock(title=f"SCENE {scene_num}"),
            SceneBlock(scene_number=scene_num),
        ]

        # Add previous scene if not first
        if scene_num > 1:
            blocks.append(SectionHeaderBlock(title="PREVIOUS SCENE"))
            blocks.append(PreviousSceneBlock(scene_number=scene_num))

        # Add next scene if not last
        if scene_num < 30:
            blocks.append(SectionHeaderBlock(title="NEXT SCENE"))
            blocks.append(NextSceneBlock(scene_number=scene_num))

        return assemble_prompt(blocks, project_name="The Proposal 2.0")

    # Test with scene 5 (has prev and next)
    prompt = build_scene_prompt(5)
    print(prompt)


def main():
    """Run all examples"""
    print("\n╔═══════════════════════════════════════════════════════════╗")
    print("║         PROMPT STUDIO EXAMPLES                            ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    try:
        example_1_basic()
        input("\n[Press Enter for next example...]")

        example_2_with_rag()
        input("\n[Press Enter for next example...]")

        example_3_custom_workflow()
        input("\n[Press Enter for next example...]")

        example_4_metadata_tracking()
        input("\n[Press Enter for next example...]")

        example_5_conditional_blocks()

        print("\n" + "="*80)
        print("All examples complete!")
        print("="*80 + "\n")

    except KeyboardInterrupt:
        print("\n\nExamples interrupted.\n")
    except Exception as e:
        print(f"\n\nError: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
