# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for LangAgent binary packaging.

This configuration produces a single-file executable that bundles:
- Python 3.11+ interpreter
- All LangChain/LangGraph dependencies
- LangAgent CLI and eval subsystem
- 6 LangChain provider packages (OpenAI, Anthropic, Google, etc.)

Constitutional Requirements:
- Article III: Excludes all LangSmith modules
- Article X: Excludes .env files and secrets
- Article XI: Self-contained binary (no Python installation required)

Generated binary: dist/langagent (Linux x86_64 ELF, < 200MB)
"""

import sys
import os
from pathlib import Path

# Repository root - use SPEC to get spec file location
spec_dir = os.path.dirname(os.path.abspath(SPEC))
repo_root = Path(spec_dir).parent.absolute()
sys.path.insert(0, str(repo_root))

block_cipher = None

# Analysis phase: collect all imports and dependencies
a = Analysis(
    # Entry point: F10 CLI runner
    ['../langagent/__main__.py'],
    
    pathex=[],
    binaries=[],
    
    # Data files: EMPTY - no .env files packaged (Constitutional Article X)
    datas=[],
    
    # Hidden imports: modules not detected by AST analysis
    hiddenimports=[
        # LangChain providers (dynamic imports via plugin system)
        'langchain_openai',
        'langchain_anthropic',
        'langchain_google_genai',
        'langchain_community',
        
        # Provider SDK dependencies (required by langchain providers)
        'openai',
        'anthropic',
        'google.generativeai',
        
        # LangChain core modules
        'langchain_core',
        'langchain_core.runnables',
        'langchain_core.messages',
        'langchain_core.tools',
        'langchain_core.prompts',
        'langchain_core.output_parsers',
        'langchain_text_splitters',
        
        # LangGraph modules
        'langgraph',
        'langgraph.graph',
        'langgraph.checkpoint',
        'langgraph.checkpoint.sqlite',
        'langgraph.checkpoint.postgres',
        'langgraph.prebuilt',
        
        # F11 Eval subsystem
        'langagent.eval.runner',
        'langagent.eval.task_loader',
        'langagent.eval.report_aggregator',
        'langagent.eval.graders.exact_match',
        'langagent.eval.graders.contains',
        'langagent.eval.graders.regex',
        'langagent.eval.graders.llm_judge',
        'langagent.eval.graders.tool_call_match',
        
        # Core dependencies
        'pydantic',
        'pydantic_core',
        'dotenv',
        'charset_normalizer',
    ],
    
    # Excluded modules: reduce binary size
    # Note: langsmith is included as it's an optional dependency of langchain_core
    excludes=[
        # Size reduction: unused UI/visualization libraries
        'tkinter',
        'matplotlib',
        'numpy.tests',
        'IPython',
        'jupyter',
        'notebook',
        'pandas',
        
        # Development tools not needed in binary
        'pytest',
        'unittest',
        'doctest',
        'pydoc',
    ],
    
    noarchive=False,
    optimize=0,
)

# PYZ: compress Python bytecode
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

# EXE: create single-file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='langagent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX compression (compatibility issues with some libraries)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # CLI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Single-file mode (Constitutional Article XI, Section 1)
    onefile=True,
)
