"""
Phase 7 Tests for User Story 5 - Stage Guard Integration (T083-T084).

These tests verify that stage guards prevent capability violations during
model_adapt and graph_compose stages per FR-047 and FR-048.

MUST FAIL before T089 implementation.
"""

import pytest
from unittest.mock import Mock, patch


# ============================================================================
# T083: test_model_adapt_stage_guard
# ============================================================================

def test_model_adapt_stage_guard():
    """
    T083: Test stage guard model_adapt blacklist enforcement.
    
    Expected behavior:
    - Attempting RuntimeDirLoader.load during create() should raise
      StageCapabilityViolationError per FR-047
    - MUST FAIL before T089 implementation
    """
    from langagent.primitives.chat_model_factory import create
    from langagent.primitives.exceptions import StageCapabilityViolationError
    
    # Create minimal config
    config = Mock()
    config.model_provider = "openai"
    config.model_name = "gpt-4"
    config.model_base_url = None
    
    # Set up environment
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"}):
        with patch("langagent.primitives.chat_model_factory.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            # Attempt to call RuntimeDirLoader.load during create()
            # This should be blocked by stage guard
            with patch("langagent.primitives.chat_model_factory.ChatOpenAI") as mock_chat:
                def side_effect_load(*args, **kwargs):
                    # Simulate attempting to load agent during model_adapt stage
                    from langagent.primitives.runtime_dir_loader import RuntimeDirLoader
                    RuntimeDirLoader.load("some/path")
                
                mock_chat.side_effect = side_effect_load
                
                with pytest.raises(StageCapabilityViolationError) as exc_info:
                    create(config)
                
                # Verify error mentions stage guard violation
                error_msg = str(exc_info.value).lower()
                assert "stage" in error_msg or "capability" in error_msg or "violation" in error_msg


# ============================================================================
# T084: test_graph_compose_stage_guard
# ============================================================================

def test_graph_compose_stage_guard():
    """
    T084: Test stage guard graph_compose blacklist enforcement.
    
    Expected behavior:
    - Attempting chat_model_factory.create during build() should raise
      StageCapabilityViolationError per FR-048
    - MUST FAIL before T089 implementation
    """
    from langagent.primitives.state_graph_builder import build
    from langagent.primitives.exceptions import StageCapabilityViolationError
    from langgraph.checkpoint.memory import MemorySaver
    from pathlib import Path
    
    # Create minimal loaded_agent
    loaded_agent = Mock()
    loaded_agent.agent_dir = Path(__file__).parent.parent / "fixtures" / "test_agent_dirs" / "minimal"
    loaded_agent.tool_ids = []
    loaded_agent.instructions = "Test"
    loaded_agent.skill_names = []
    loaded_agent.metadata = {}
    
    # Create minimal config
    config = Mock()
    config.model_provider = "openai"
    config.model_name = "gpt-4"
    config.model_base_url = None
    config.model = None
    config.checkpointer = "memory"
    config.checkpoint_sqlite_path = None
    config.checkpoint_postgres_dsn = None
    config.middleware_ids = []
    config.guardrail_policy = None
    
    checkpoint = MemorySaver()
    
    # Attempt to call chat_model_factory.create during build()
    # This should be blocked by stage guard
    with patch("langagent.primitives.state_graph_builder.StateGraph") as mock_graph_cls:
        def side_effect_create(*args, **kwargs):
            # Simulate attempting to create model during graph_compose stage
            from langagent.primitives.chat_model_factory import create
            mock_config = Mock()
            mock_config.model_provider = "openai"
            mock_config.model_name = "gpt-4"
            mock_config.model_base_url = None
            create(mock_config)
        
        mock_builder = Mock()
        mock_builder.compile.side_effect = side_effect_create
        mock_graph_cls.return_value = mock_builder
        
        with pytest.raises(StageCapabilityViolationError) as exc_info:
            build(
                loaded_agent=loaded_agent,
                config=config,
                checkpoint=checkpoint
            )
        
        # Verify error mentions stage guard violation
        error_msg = str(exc_info.value).lower()
        assert "stage" in error_msg or "capability" in error_msg or "violation" in error_msg
