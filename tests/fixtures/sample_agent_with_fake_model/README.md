# Sample agent fixture for F08 integration tests

This directory provides minimal fixtures for testing the main loop dispatcher
with FakeListChatModel and real LangGraph.

## Contents

- `fake_model_config.py`: FakeListChatModel factory functions
- `tools/echo.py`: Simple echo tool for deterministic testing

## Usage

```python
from tests.fixtures.sample_agent_with_fake_model.fake_model_config import create_fake_model_single_turn
from tests.fixtures.sample_agent_with_fake_model.tools.echo import echo

fake_model = create_fake_model_single_turn()
# Use with real StateGraph in integration tests
```
