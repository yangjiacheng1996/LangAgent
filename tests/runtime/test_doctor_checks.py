"""Tests for doctor_check module.

Tests cover:
- DoctorCheckResult model validation
- 4 check functions (model, checkpointer, skills, instructions)
- Probe function injection
- Overall status aggregation
"""

import pytest
from unittest.mock import Mock
from pydantic import ValidationError

from langagent.runtime.doctor_check import DoctorCheckResult


class TestDoctorCheckResultModel:
    """T018: Test DoctorCheckResult Pydantic model."""
    
    def test_doctor_check_result_validates_json(self):
        """DoctorCheckResult should be JSON-serializable."""
        result = DoctorCheckResult(
            check_name="model",
            status="ok",
            detail="Connected successfully"
        )
        json_str = result.model_dump_json()
        assert "model" in json_str
        assert "ok" in json_str
    
    def test_doctor_check_result_frozen(self):
        """DoctorCheckResult should be immutable."""
        result = DoctorCheckResult(
            check_name="model",
            status="ok",
            detail="OK"
        )
        with pytest.raises(ValidationError):
            result.status = "error"
    
    def test_doctor_check_result_invalid_check_name(self):
        """Invalid check_name should raise ValidationError."""
        with pytest.raises(ValidationError):
            DoctorCheckResult(
                check_name="invalid",
                status="ok",
                detail="OK"
            )
    
    def test_doctor_check_result_invalid_status(self):
        """Invalid status should raise ValidationError."""
        with pytest.raises(ValidationError):
            DoctorCheckResult(
                check_name="model",
                status="invalid",
                detail="OK"
            )


class TestUS2DoctorChecks:
    """User Story 2: Doctor Self-Check Reporting."""
    
    def test_doctor_check_model_endpoint_reachable(self):
        """T119: Model check should return ok when endpoint is reachable."""
        from langagent.runtime.doctor_check import check_model
        
        config = Mock()
        config.model_provider = "openai"
        config.model_name = "gpt-4o"
        loaded = Mock()
        
        # Mock probe function that returns True (reachable)
        probe_fn = Mock(return_value=True)
        
        result = check_model(config, loaded, model_probe_fn=probe_fn)
        
        assert result.check_name == "model"
        assert result.status == "ok"
        assert "openai" in result.detail.lower()
        assert "gpt-4o" in result.detail.lower()
    
    def test_doctor_check_model_endpoint_unreachable(self):
        """T120: Model check should return error when endpoint unreachable."""
        from langagent.runtime.doctor_check import check_model
        
        config = Mock()
        config.model_provider = "openai"
        loaded = Mock()
        
        # Mock probe function that returns False (unreachable)
        probe_fn = Mock(return_value=False)
        
        result = check_model(config, loaded, model_probe_fn=probe_fn)
        
        assert result.check_name == "model"
        assert result.status == "error"
    
    def test_doctor_check_model_without_probe_fn_returns_skipped(self):
        """T121: Model check without probe_fn should return skipped."""
        from langagent.runtime.doctor_check import check_model
        
        config = Mock()
        loaded = Mock()
        
        result = check_model(config, loaded, model_probe_fn=None)
        
        assert result.check_name == "model"
        assert result.status == "skipped"
        assert "not provided" in result.detail
    
    def test_doctor_check_checkpointer_ok(self):
        """T122: Checkpointer check should return ok when working."""
        from langagent.runtime.doctor_check import check_checkpointer
        
        config = Mock()
        config.checkpointer = "sqlite"
        
        probe_fn = Mock(return_value=True)
        
        result = check_checkpointer(config, checkpoint_probe_fn=probe_fn)
        
        assert result.check_name == "checkpointer"
        assert result.status == "ok"
    
    def test_doctor_check_checkpointer_failed(self):
        """T123: Checkpointer check should return error when failed."""
        from langagent.runtime.doctor_check import check_checkpointer
        
        config = Mock()
        config.checkpointer = "postgres"
        
        probe_fn = Mock(return_value=False)
        
        result = check_checkpointer(config, checkpoint_probe_fn=probe_fn)
        
        assert result.check_name == "checkpointer"
        assert result.status == "error"
    
    def test_doctor_check_skills_all_valid(self):
        """T124: Skills check should return ok when all skills valid."""
        from langagent.runtime.doctor_check import check_skills
        
        loaded = Mock()
        skill1 = Mock()
        skill1.name = "web_search"
        skill1.version = "1.0.0"
        skill2 = Mock()
        skill2.name = "file_reader"
        skill2.version = "1.0.0"
        loaded.skills = [skill1, skill2]
        
        result = check_skills(loaded)
        
        assert result.check_name == "skills"
        assert result.status == "ok"
        assert "2" in result.detail
    
    def test_doctor_check_skills_malformed(self):
        """T125: Skills check should return warn for some malformed skills."""
        from langagent.runtime.doctor_check import check_skills
        
        loaded = Mock()
        skill1 = Mock()
        skill1.name = "web_search"
        skill1.version = "1.0.0"
        skill2 = Mock()
        skill2.name = "bad_skill"
        # Missing version attribute
        delattr(skill2, 'version')
        loaded.skills = [skill1, skill2]
        
        result = check_skills(loaded)
        
        assert result.check_name == "skills"
        assert result.status == "warn"
        assert "bad_skill" in result.detail
    
    def test_doctor_check_instructions_valid(self):
        """T128: Instructions check should return ok for valid instructions."""
        from langagent.runtime.doctor_check import check_instructions
        
        loaded = Mock()
        loaded.instructions = "You are a helpful assistant that helps users complete tasks."
        
        result = check_instructions(loaded)
        
        assert result.check_name == "instructions"
        assert result.status == "ok"
    
    def test_doctor_check_instructions_too_short(self):
        """T126: Instructions check should return warn for short instructions."""
        from langagent.runtime.doctor_check import check_instructions
        
        loaded = Mock()
        loaded.instructions = "Short"
        
        result = check_instructions(loaded)
        
        assert result.check_name == "instructions"
        assert result.status == "warn"
        assert "too short" in result.detail.lower()
    
    def test_run_doctor_checks_aggregates_overall(self):
        """T129: run_doctor_checks should aggregate overall status."""
        from langagent.runtime.doctor_check import run_doctor_checks
        
        config = Mock()
        config.model_provider = "openai"
        config.model_name = "gpt-4o"
        config.checkpointer = "memory"
        
        loaded = Mock()
        loaded.skills = []
        loaded.instructions = "You are a helpful assistant."
        
        model_probe = Mock(return_value=True)
        checkpoint_probe = Mock(return_value=True)
        
        checks, overall = run_doctor_checks(
            config, loaded,
            model_probe_fn=model_probe,
            checkpoint_probe_fn=checkpoint_probe
        )
        
        assert len(checks) == 4
        assert overall == "ok"
        
        # Verify probe functions called exactly once
        model_probe.assert_called_once()
        checkpoint_probe.assert_called_once()
