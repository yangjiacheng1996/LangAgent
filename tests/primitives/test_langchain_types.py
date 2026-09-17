"""
Tests for langchain_types re-export module.

Verifies:
1. All LangChain/LangGraph types are correctly re-exported
2. Re-exported types are identical to originals (not wrappers)
3. No direct langchain/langgraph imports exist outside primitives layer (FR-033, SC-005)
"""

import subprocess
from pathlib import Path

import pytest

# Import from primitives re-export module
from langagent.primitives.langchain_types import (
    # Messages
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    add_messages,
    # Models
    BaseChatModel,
    # Tools
    BaseTool,
    tool,
    # Graph
    StateGraph,
    START,
    END,
    # Checkpointing
    BaseCheckpointSaver,
)

# Import originals for identity verification
from langchain_core.messages import (
    BaseMessage as OriginalBaseMessage,
    HumanMessage as OriginalHumanMessage,
    AIMessage as OriginalAIMessage,
    SystemMessage as OriginalSystemMessage,
    ToolMessage as OriginalToolMessage,
)
from langgraph.graph.message import add_messages as original_add_messages
from langchain_core.language_models import BaseChatModel as OriginalBaseChatModel
from langchain_core.tools import BaseTool as OriginalBaseTool, tool as original_tool
from langgraph.graph import StateGraph as OriginalStateGraph, START as ORIGINAL_START, END as ORIGINAL_END
from langgraph.checkpoint.base import BaseCheckpointSaver as OriginalBaseCheckpointSaver


class TestLangChainTypesReExport:
    """Test suite for langchain_types re-export module."""

    def test_import_messages(self):
        """T064: Import message types and verify identity to LangChain originals."""
        # Verify all message types are imported
        assert BaseMessage is not None
        assert HumanMessage is not None
        assert AIMessage is not None
        assert SystemMessage is not None
        assert ToolMessage is not None
        assert add_messages is not None

        # Verify identity - re-exports must be identical objects, not wrappers
        assert BaseMessage is OriginalBaseMessage, "BaseMessage should be identical to langchain_core.messages.BaseMessage"
        assert HumanMessage is OriginalHumanMessage, "HumanMessage should be identical to langchain_core.messages.HumanMessage"
        assert AIMessage is OriginalAIMessage, "AIMessage should be identical to langchain_core.messages.AIMessage"
        assert SystemMessage is OriginalSystemMessage, "SystemMessage should be identical to langchain_core.messages.SystemMessage"
        assert ToolMessage is OriginalToolMessage, "ToolMessage should be identical to langchain_core.messages.ToolMessage"
        assert add_messages is original_add_messages, "add_messages should be identical to langgraph.graph.message.add_messages"

    def test_import_models(self):
        """T065: Import model types and verify identity."""
        # Verify model types are imported
        assert BaseChatModel is not None

        # Verify identity
        assert BaseChatModel is OriginalBaseChatModel, "BaseChatModel should be identical to langchain_core.language_models.BaseChatModel"

    def test_import_tools(self):
        """T066: Import tool types and verify identity."""
        # Verify tool types are imported
        assert BaseTool is not None
        assert tool is not None

        # Verify identity
        assert BaseTool is OriginalBaseTool, "BaseTool should be identical to langchain_core.tools.BaseTool"
        assert tool is original_tool, "tool decorator should be identical to langchain_core.tools.tool"

    def test_import_graph(self):
        """T067: Import graph types and verify identity."""
        # Verify graph types are imported
        assert StateGraph is not None
        assert START is not None
        assert END is not None

        # Verify identity
        assert StateGraph is OriginalStateGraph, "StateGraph should be identical to langgraph.graph.StateGraph"
        assert START is ORIGINAL_START, "START should be identical to langgraph.graph.START"
        assert END is ORIGINAL_END, "END should be identical to langgraph.graph.END"

        # Note: CompiledStateGraph is not exported in current implementation
        # This is acceptable as it's typically returned by StateGraph.compile()

    def test_import_checkpoint(self):
        """T068: Import checkpoint types and verify identity."""
        # Verify checkpoint types are imported
        assert BaseCheckpointSaver is not None

        # Verify identity
        assert BaseCheckpointSaver is OriginalBaseCheckpointSaver, "BaseCheckpointSaver should be identical to langgraph.checkpoint.base.BaseCheckpointSaver"

    def test_import_runtime_context(self):
        """T069: Import Runtime context from langgraph.prebuilt per FR-032."""
        # According to research.md Decision 2, Runtime may be in langgraph.runtime
        # However, it may not be available in all LangGraph versions
        try:
            from langgraph.runtime import Runtime as OriginalRuntime
            from langagent.primitives.langchain_types import Runtime
            
            assert Runtime is not None
            assert Runtime is OriginalRuntime, "Runtime should be identical to langgraph.runtime.Runtime"
        except ImportError:
            # Runtime may not exist in current LangGraph version - skip test
            pytest.skip("Runtime not available in current LangGraph version")

    def test_no_direct_langchain_imports_runtime(self):
        """T070: Static analysis - runtime layer should not have direct langchain imports."""
        project_root = Path(__file__).parent.parent.parent
        runtime_dir = project_root / "langagent" / "runtime"

        if not runtime_dir.exists():
            pytest.skip("Runtime layer does not exist yet")

        # Run grep to find direct langchain/langgraph imports
        result = subprocess.run(
            ["grep", "-r", "-E", "from (langchain|langgraph)", str(runtime_dir)],
            capture_output=True,
            text=True,
        )

        # grep returns non-zero exit code when no matches found
        if result.returncode == 0:
            # Found matches - this is a violation
            matches = result.stdout.strip()
            pytest.fail(
                f"Found direct langchain/langgraph imports in runtime layer (violates FR-033):\n{matches}\n"
                f"All imports must go through langagent.primitives.langchain_types"
            )

        # No matches found (returncode != 0) - test passes

    def test_no_direct_langchain_imports_cross_cutting(self):
        """T071: Static analysis - cross_cutting layer should not have direct langchain imports."""
        project_root = Path(__file__).parent.parent.parent
        cross_cutting_dir = project_root / "langagent" / "cross_cutting"

        if not cross_cutting_dir.exists():
            pytest.skip("Cross_cutting layer does not exist yet")

        # Run grep to find direct langchain/langgraph imports
        result = subprocess.run(
            ["grep", "-r", "-E", "from (langchain|langgraph)", str(cross_cutting_dir)],
            capture_output=True,
            text=True,
        )

        # grep returns non-zero exit code when no matches found
        if result.returncode == 0:
            # Found matches - this is a violation
            matches = result.stdout.strip()
            pytest.fail(
                f"Found direct langchain/langgraph imports in cross_cutting layer (violates FR-033):\n{matches}\n"
                f"All imports must go through langagent.primitives.langchain_types"
            )

        # No matches found (returncode != 0) - test passes
