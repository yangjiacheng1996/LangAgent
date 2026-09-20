"""Tool registry for protocol layer.

This module provides:
- register_all(): Register all tools from an agent directory's tools/ subdirectory
- get_by_id(): Retrieve a registered ToolSpec by tool_id
- Dynamic import with unique namespaces and sys.modules cleanup
"""

import importlib.util
import os
import sys
from typing import Any, Optional

from langagent.cross_cutting import logger
from langagent.primitives.langchain_types import BaseTool
from langagent.protocol.event_bus import EventBus
from langagent.protocol.tool_schemas import (
    MINIMAL_JSON_SCHEMA,
    ToolIdDuplicateError,
    ToolSpec,
)


# Initialize event bus
event_bus = EventBus()

# Internal registry for tool specs (O(1) lookup)
_tool_registry: dict[str, ToolSpec] = {}


def _load_tool_from_file(tool_path: str, tool_id: str) -> Optional[ToolSpec]:
    """Load a tool from a Python file via dynamic import.
    
    Args:
        tool_path: Absolute path to tool .py file
        tool_id: Tool identifier (filename without .py extension)
        
    Returns:
        ToolSpec if successful, None if loading failed
        
    Side Effects:
        - Dynamically imports tool with unique namespace
        - Cleans up sys.modules entry after extraction
        - Publishes tool_load_failed event on errors
    """
    module_name = f"langagent_dynamic_tool_{tool_id}"
    
    try:
        # Dynamic import with unique namespace
        spec = importlib.util.spec_from_file_location(module_name, tool_path)
        if spec is None or spec.loader is None:
            logger.emit(
                tag="la.runtime.tool_load_failed",
                payload={
                    "path": tool_path,
                    "tool_id": tool_id,
                    "error": "Failed to create module spec"
                }
            )
            return None
        
        module = importlib.util.module_from_spec(spec)
        
        # Execute module to load definitions
        spec.loader.exec_module(module)
        
        # Verify exported variable matches filename (strict matching)
        if not hasattr(module, tool_id):
            logger.emit(
                tag="la.runtime.tool_load_failed",
                payload={
                    "path": tool_path,
                    "tool_id": tool_id,
                    "error": f"Tool file must export variable '{tool_id}' matching filename"
                }
            )
            
            # Publish tool_load_failed event
            try:
                event_bus.publish(
                    event_type="tool_load_failed",
                    source="protocol_tool_registry",
                    payload={
                        "path": tool_path,
                        "tool_id": tool_id,
                        "error": f"Missing export variable '{tool_id}'"
                    }
                )
            except Exception:
                pass  # Silently ignore event bus errors
            
            return None
        
        # Extract tool instance
        tool_instance = getattr(module, tool_id)
        
        if not isinstance(tool_instance, BaseTool):
            logger.emit(
                tag="la.runtime.tool_load_failed",
                payload={
                    "path": tool_path,
                    "tool_id": tool_id,
                    "error": f"Exported '{tool_id}' is not a BaseTool instance"
                }
            )
            
            # Publish tool_load_failed event
            try:
                event_bus.publish(
                    event_type="tool_load_failed",
                    source="protocol_tool_registry",
                    payload={
                        "path": tool_path,
                        "tool_id": tool_id,
                        "error": "Not a BaseTool instance"
                    }
                )
            except Exception:
                pass
            
            return None
        
        # Extract requires_approval constant (defaults to False)
        requires_approval = getattr(module, "REQUIRES_APPROVAL", False)
        
        # Extract args_schema from BaseTool
        args_schema = MINIMAL_JSON_SCHEMA.copy()
        if hasattr(tool_instance, "args_schema") and tool_instance.args_schema is not None:
            try:
                # Use Pydantic's model_json_schema() to get JSON Schema Draft 7
                if hasattr(tool_instance.args_schema, "model_json_schema"):
                    args_schema = tool_instance.args_schema.model_json_schema()
                    # Ensure $schema field is present
                    if "$schema" not in args_schema:
                        args_schema["$schema"] = "http://json-schema.org/draft-07/schema#"
            except Exception as e:
                logger.emit(
                    tag="la.runtime.tool_load_failed",
                    payload={
                        "path": tool_path,
                        "tool_id": tool_id,
                        "error": f"Failed to extract args_schema: {e}"
                    }
                )
        
        # Create ToolSpec
        tool_spec = ToolSpec(
            tool_id=tool_id,
            tool_name=tool_id,  # Identical to tool_id for naming consistency
            description=tool_instance.description or "",
            args_schema=args_schema,
            enabled=False,  # Default to False per FR-016
            requires_approval=bool(requires_approval)
        )
        
        return tool_spec
        
    except SyntaxError as e:
        logger.emit(
            tag="la.runtime.tool_load_failed",
            payload={
                "path": tool_path,
                "tool_id": tool_id,
                "error": f"SyntaxError: {e}"
            }
        )
        
        # Publish tool_load_failed event
        try:
            event_bus.publish(
                event_type="tool_load_failed",
                source="protocol_tool_registry",
                payload={
                    "path": tool_path,
                    "tool_id": tool_id,
                    "error": f"SyntaxError: {e}"
                }
            )
        except Exception:
            pass
        
        return None
    
    except ImportError as e:
        logger.emit(
            tag="la.runtime.tool_load_failed",
            payload={
                "path": tool_path,
                "tool_id": tool_id,
                "error": f"ImportError: {e}"
            }
        )
        
        # Publish tool_load_failed event
        try:
            event_bus.publish(
                event_type="tool_load_failed",
                source="protocol_tool_registry",
                payload={
                    "path": tool_path,
                    "tool_id": tool_id,
                    "error": f"ImportError: {e}"
                }
            )
        except Exception:
            pass
        
        return None
    
    except ModuleNotFoundError as e:
        logger.emit(
            tag="la.runtime.tool_load_failed",
            payload={
                "path": tool_path,
                "tool_id": tool_id,
                "error": f"ModuleNotFoundError: {e}"
            }
        )
        
        # Publish tool_load_failed event
        try:
            event_bus.publish(
                event_type="tool_load_failed",
                source="protocol_tool_registry",
                payload={
                    "path": tool_path,
                    "tool_id": tool_id,
                    "error": f"ModuleNotFoundError: {e}"
                }
            )
        except Exception:
            pass
        
        return None
    
    except Exception as e:
        logger.emit(
            tag="la.runtime.tool_load_failed",
            payload={
                "path": tool_path,
                "tool_id": tool_id,
                "error": f"Unexpected error: {e}"
            }
        )
        
        # Publish tool_load_failed event
        try:
            event_bus.publish(
                event_type="tool_load_failed",
                source="protocol_tool_registry",
                payload={
                    "path": tool_path,
                    "tool_id": tool_id,
                    "error": str(e)
                }
            )
        except Exception:
            pass
        
        return None
    
    finally:
        # Clean up sys.modules entry to prevent memory leaks
        sys.modules.pop(module_name, None)


def register_all(tools_dir: str) -> list[ToolSpec]:
    """Register all tools from tools_dir via dynamic import.
    
    Args:
        tools_dir: Absolute path to agent directory's tools/ subdirectory
        
    Returns:
        List of ToolSpec objects for successfully registered tools
        
    Side Effects:
        - Dynamically imports tools with unique namespace (langagent_dynamic_tool_{tool_id})
        - Cleans up sys.modules entries before return
        - Does NOT pollute sys.path
        - Publishes tool_registered event for each success
        - Publishes tool_load_failed event for each failure
        - Logs to la.runtime.tool_load_failed for failures
        
    Errors:
        Raises ToolIdDuplicateError (exit code 70) if duplicate tool_id detected.
        Does not raise exceptions for individual tool import failures (fail-soft).
        Returns empty list if tools_dir does not exist.
    """
    if not os.path.exists(tools_dir):
        return []
    
    if not os.path.isdir(tools_dir):
        return []
    
    loaded_tools = []
    loaded_tool_ids = set()
    
    # Scan for .py tool files
    try:
        entries = os.listdir(tools_dir)
    except OSError as e:
        logger.emit(
            tag="la.runtime.tool_load_failed",
            payload={"error": f"Failed to list tools directory {tools_dir}: {e}"}
        )
        return []
    
    for entry in sorted(entries):
        if not entry.endswith(".py"):
            continue
        
        if entry.startswith("__"):
            continue  # Skip __init__.py, __pycache__, etc.
        
        tool_path = os.path.join(tools_dir, entry)
        tool_id = entry[:-3]  # Remove .py extension
        
        # Check for duplicate tool_id
        if tool_id in loaded_tool_ids:
            raise ToolIdDuplicateError(
                f"Duplicate tool_id '{tool_id}' detected in {tools_dir}",
                exit_code=70
            )
        
        # Load tool
        tool_spec = _load_tool_from_file(tool_path, tool_id)
        
        if tool_spec is not None:
            loaded_tools.append(tool_spec)
            loaded_tool_ids.add(tool_id)
            
            # Register in internal registry
            _tool_registry[tool_id] = tool_spec
            
            # Publish tool_registered event
            try:
                event_bus.publish(
                    event_type="tool_registered",
                    source="protocol_tool_registry",
                    payload={
                        "tool_id": tool_spec.tool_id,
                        "tool_name": tool_spec.tool_name,
                        "description": tool_spec.description,
                        "requires_approval": tool_spec.requires_approval
                    }
                )
            except Exception:
                pass  # Silently ignore event bus errors
    
    return loaded_tools


def get_by_id(tool_id: str) -> Optional[ToolSpec]:
    """Retrieve registered ToolSpec by tool_id.
    
    Args:
        tool_id: Tool identifier (filename without .py extension)
        
    Returns:
        ToolSpec if found, None otherwise
        
    Performance:
        O(1) lookup via internal dict registry
    """
    return _tool_registry.get(tool_id)


__all__ = [
    "register_all",
    "get_by_id",
]
