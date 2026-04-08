
"""
Tests for AI Infrastructure Optimizer
"""
import pytest
from fastapi.testclient import TestClient


def test_infra_optimize_success(client):
    """Test successful infrastructure optimization"""
    infra_model = {
        "model_name": "llama-2-7b",
        "model_type": "LLM",
        "parameters": "7B",
        "framework": "PyTorch",
        "quantization": "4-bit",
        "current_hardware": {
            "cpu_cores": 8,
            "memory_gb": 16,
            "gpu_available": False
        },
        "performance_requirements": {
            "inference_time_ms": 100,
            "throughput_requests_per_sec": 10
        }
    }

    response = client.post("/infra/optimize", json=infra_model)

    assert response.status_code == 200
    data = response.json()
    assert "plan_id" in data
    assert "current_assessment" in data
    assert "suggestions" in data
    assert "summary" in data
    assert "generated_at" in data


def test_infra_optimize_minimal_config(client):
    """Test infrastructure optimization with minimal config"""
    infra_model = {
        "model_name": "test-model",
        "model_type": "LLM",
        "parameters": "3B",
        "framework": "PyTorch",
        "current_hardware": {
            "cpu_cores": 4,
            "memory_gb": 8
        },
        "performance_requirements": {
            "inference_time_ms": 200
        }
    }

    response = client.post("/infra/optimize", json=infra_model)

    assert response.status_code == 200
    data = response.json()
    assert "plan_id" in data


def test_infra_optimize_validation_error(client):
    """Test infrastructure optimization with invalid input"""
    infra_model = {
        "model_name": "test-model"
        # Missing required fields
    }

    response = client.post("/infra/optimize", json=infra_model)

    assert response.status_code == 422  # Validation error


def test_infra_optimize_with_gpu(client):
    """Test infrastructure optimization with GPU"""
    infra_model = {
        "model_name": "llama-2-13b",
        "model_type": "LLM",
        "parameters": "13B",
        "framework": "PyTorch",
        "quantization": "8-bit",
        "current_hardware": {
            "cpu_cores": 16,
            "memory_gb": 32,
            "gpu_available": True,
            "gpu_memory_gb": 16
        },
        "performance_requirements": {
            "inference_time_ms": 50,
            "throughput_requests_per_sec": 20
        }
    }

    response = client.post("/infra/optimize", json=infra_model)

    assert response.status_code == 200
    data = response.json()

    # Check that GPU is detected in assessment
    if data["current_assessment"].get("hardware", {}).get("gpu"):
        assert len(data["current_assessment"]["hardware"]["gpu"]) > 0


def test_infra_optimize_suggestions_structure(client):
    """Test that optimization suggestions have correct structure"""
    infra_model = {
        "model_name": "test-model",
        "model_type": "LLM",
        "parameters": "7B",
        "framework": "PyTorch",
        "current_hardware": {
            "cpu_cores": 8,
            "memory_gb": 16
        },
        "performance_requirements": {
            "inference_time_ms": 100
        }
    }

    response = client.post("/infra/optimize", json=infra_model)

    assert response.status_code == 200
    data = response.json()

    # Check suggestion structure
    if data["suggestions"]:
        suggestion = data["suggestions"][0]
        assert "id" in suggestion
        assert "category" in suggestion
        assert "priority" in suggestion
        assert "title" in suggestion
        assert "description" in suggestion
        assert "expected_improvement" in suggestion
        assert "implementation_effort" in suggestion
        assert "steps" in suggestion
        assert isinstance(suggestion["steps"], list)


def test_infra_optimize_summary_structure(client):
    """Test that optimization summary has correct structure"""
    infra_model = {
        "model_name": "test-model",
        "model_type": "LLM",
        "parameters": "7B",
        "framework": "PyTorch",
        "current_hardware": {
            "cpu_cores": 8,
            "memory_gb": 16
        },
        "performance_requirements": {
            "inference_time_ms": 100
        }
    }

    response = client.post("/infra/optimize", json=infra_model)

    assert response.status_code == 200
    data = response.json()

    # Check summary structure
    assert "total_suggestions" in data["summary"]
    assert "critical_issues" in data["summary"]
    assert "estimated_improvement" in data["summary"]


def test_infra_optimize_bottleneck_detection(client):
    """Test that infrastructure optimization detects bottlenecks"""
    infra_model = {
        "model_name": "large-model",
        "model_type": "LLM",
        "parameters": "70B",
        "framework": "PyTorch",
        "current_hardware": {
            "cpu_cores": 8,
            "memory_gb": 16
        },
        "performance_requirements": {
            "inference_time_ms": 50
        }
    }

    response = client.post("/infra/optimize", json=infra_model)

    assert response.status_code == 200
    data = response.json()

    # Check that bottlenecks are detected
    if data["current_assessment"].get("bottlenecks"):
        assert len(data["current_assessment"]["bottlenecks"]) > 0

        bottleneck = data["current_assessment"]["bottlenecks"][0]
        assert "type" in bottleneck
        assert "severity" in bottleneck
        assert "description" in bottleneck
