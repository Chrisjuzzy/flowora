"""
AI Infrastructure Optimizer - Optimizes infrastructure for AI workloads
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from database_production import get_db
import logging
from datetime import datetime
import json
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    import ollama
except Exception:
    ollama = None
import psutil
import subprocess

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/infra",
    tags=["infra-optimizer"],
    responses={404: {"description": "Not found"}},
)


# --- Pydantic Models ---

class InfrastructureModel(BaseModel):
    """Infrastructure model details"""
    model_name: str = Field(..., description="Name of the AI model")
    model_type: str = Field(..., description="Type of model (LLM, embedding, etc.)")
    parameters: str = Field(..., description="Number of parameters (e.g., '7B', '13B')")
    framework: str = Field(..., description="Framework (PyTorch, TensorFlow, etc.)")
    quantization: Optional[str] = Field(None, description="Quantization level (4-bit, 8-bit, etc.)")
    current_hardware: Dict[str, Any] = Field(..., description="Current hardware configuration")
    workload_pattern: Optional[str] = Field(None, description="Workload pattern (batch, streaming, etc.)")
    performance_requirements: Dict[str, Any] = Field(..., description="Performance requirements")


class OptimizationSuggestion(BaseModel):
    """Optimization suggestion"""
    id: str
    category: str  # hardware, software, configuration, scaling
    priority: str  # critical, high, medium, low
    title: str
    description: str
    expected_improvement: str
    implementation_effort: str
    steps: List[str]


class OptimizationPlan(BaseModel):
    """Infrastructure optimization plan"""
    plan_id: str
    infrastructure_model: InfrastructureModel
    current_assessment: Dict[str, Any]
    suggestions: List[OptimizationSuggestion]
    summary: Dict[str, Any]
    generated_at: datetime


# --- Analysis Functions ---

async def assess_current_infrastructure(
    infrastructure_model: InfrastructureModel
) -> Dict[str, Any]:
    """
    Assess current infrastructure for AI workloads

    Args:
        infrastructure_model: Infrastructure model details

    Returns:
        Dictionary with current infrastructure assessment
    """
    try:
        assessment = {
            "hardware": {},
            "software": {},
            "performance": {},
            "bottlenecks": []
        }

        # Analyze hardware
        current_hardware = infrastructure_model.current_hardware

        # CPU assessment
        cpu_info = {
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0
        }
        assessment["hardware"]["cpu"] = cpu_info

        # Memory assessment
        memory = psutil.virtual_memory()
        memory_info = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent_used": memory.percent
        }
        assessment["hardware"]["memory"] = memory_info

        # GPU assessment (if available)
        try:
            gpu_info = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu", 
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if gpu_info.returncode == 0:
                gpu_lines = gpu_info.stdout.strip().split('\n')
                gpus = []
                for line in gpu_lines:
                    parts = line.split(', ')
                    if len(parts) >= 4:
                        gpus.append({
                            "name": parts[0],
                            "memory_total_mb": int(parts[1]),
                            "memory_free_mb": int(parts[2]),
                            "utilization_percent": int(parts[3])
                        })
                assessment["hardware"]["gpu"] = gpus
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            assessment["hardware"]["gpu"] = []

        # Analyze model requirements
        model_params = infrastructure_model.parameters
        if 'B' in model_params:
            param_count = float(model_params.replace('B', ''))
            # Estimate memory requirements (rough estimate: 1B params ≈ 2GB at FP16)
            estimated_memory_gb = param_count * 2

            # Check if current memory is sufficient
            if estimated_memory_gb > memory_info["total_gb"] * 0.8:
                assessment["bottlenecks"].append({
                    "type": "memory",
                    "severity": "high",
                    "description": f"Model requires approximately {estimated_memory_gb:.1f}GB of memory, but only {memory_info['total_gb']}GB is available"
                })

        # Analyze GPU availability
        if not assessment["hardware"]["gpu"]:
            assessment["bottlenecks"].append({
                "type": "gpu",
                "severity": "medium",
                "description": "No GPU detected. GPU acceleration would significantly improve performance"
            })

        # Analyze quantization
        quantization = infrastructure_model.quantization
        if not quantization:
            assessment["bottlenecks"].append({
                "type": "quantization",
                "severity": "medium",
                "description": "No quantization specified. Quantization can reduce memory usage and improve inference speed"
            })

        return assessment

    except Exception as e:
        logger.error(f"Error assessing infrastructure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assess infrastructure: {str(e)}"
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
async def generate_optimization_suggestions(
    infrastructure_model: InfrastructureModel,
    current_assessment: Dict[str, Any]
) -> List[OptimizationSuggestion]:
    """
    Generate optimization suggestions using Ollama

    Args:
        infrastructure_model: Infrastructure model details
        current_assessment: Current infrastructure assessment

    Returns:
        List of optimization suggestions
    """
    suggestions = []

    # Generate rule-based suggestions for common issues
    for bottleneck in current_assessment.get("bottlenecks", []):
        if bottleneck["type"] == "memory":
            suggestions.append(OptimizationSuggestion(
                id="opt-quantization",
                category="configuration",
                priority="high",
                title="Implement Model Quantization",
                description="Reduce memory usage and improve inference speed through quantization",
                expected_improvement="30-50% reduction in memory usage, 2-3x faster inference",
                implementation_effort="Low",
                steps=[
                    "Evaluate 4-bit and 8-bit quantization options",
                    "Test quantized model for accuracy degradation",
                    "Implement quantization in inference pipeline",
                    "Monitor performance improvements"
                ]
            ))

        elif bottleneck["type"] == "gpu":
            suggestions.append(OptimizationSuggestion(
                id="opt-gpu-acceleration",
                category="hardware",
                priority="high",
                title="Add GPU Acceleration",
                description="GPU acceleration can significantly improve model inference speed",
                expected_improvement="10-50x faster inference depending on workload",
                implementation_effort="Medium",
                steps=[
                    "Evaluate GPU options (NVIDIA, AMD, etc.)",
                    "Consider cloud GPU services for flexibility",
                    "Update inference pipeline to use GPU",
                    "Optimize batch sizes for GPU utilization"
                ]
            ))

    if ollama is None:
        suggestions.append(OptimizationSuggestion(
            id="opt-ai-unavailable",
            category="configuration",
            priority="medium",
            title="AI suggestions unavailable",
            description="Ollama client is not installed; using rule-based recommendations only.",
            expected_improvement="Varies based on implementation",
            implementation_effort="Low",
            steps=[
                "Install the Ollama Python client in the backend image",
                "Ensure the Ollama service is running",
                "Retry optimization for AI-generated suggestions"
            ]
        ))
        return suggestions

    # Generate AI-based suggestions for more complex optimizations
    try:
        prompt = f"""
        Generate optimization suggestions for this AI infrastructure:

        Model Details:
        - Name: {infrastructure_model.model_name}
        - Type: {infrastructure_model.model_type}
        - Parameters: {infrastructure_model.parameters}
        - Framework: {infrastructure_model.framework}
        - Quantization: {infrastructure_model.quantization or 'None'}
        - Workload Pattern: {infrastructure_model.workload_pattern or 'Not specified'}

        Current Hardware:
        {json.dumps(infrastructure_model.current_hardware, indent=2)}

        Performance Requirements:
        {json.dumps(infrastructure_model.performance_requirements, indent=2)}

        Current Assessment:
        {json.dumps(current_assessment, indent=2)}

        Return a JSON object with:
        {{
            "suggestions": [
                {{
                    "id": "<unique identifier>",
                    "category": "<hardware/software/configuration/scaling>",
                    "priority": "<critical/high/medium/low>",
                    "title": "<short title>",
                    "description": "<detailed description>",
                    "expected_improvement": "<quantified improvement>",
                    "implementation_effort": "<Low/Medium/High>",
                    "steps": ["<step 1>", "<step 2>", ...]
                }}
            ]
        }}
        """

        # Call Ollama
        response = ollama.generate(
            model='qwen2.5-coder:7b',
            prompt=prompt,
            format='json'
        )

        # Parse response
        result = json.loads(response['response'])

        # Validate response structure
        if 'suggestions' not in result:
            logger.error(f"Invalid response from Ollama: {result}")
            raise ValueError("Invalid response format from Ollama")

        # Add AI-generated suggestions
        for suggestion_data in result['suggestions']:
            suggestion = OptimizationSuggestion(**suggestion_data)
            suggestions.append(suggestion)

    except Exception as e:
        logger.error(f"Error generating AI suggestions: {e}")
        # Add fallback suggestion
        suggestions.append(OptimizationSuggestion(
            id="opt-general",
            category="configuration",
            priority="medium",
            title="General Infrastructure Optimization",
            description="Review and optimize infrastructure configuration for better performance",
            expected_improvement="Varies based on implementation",
            implementation_effort="Medium",
            steps=[
                "Review current infrastructure configuration",
                "Identify bottlenecks through profiling",
                "Implement targeted optimizations",
                "Monitor and measure improvements"
            ]
        ))

    # Sort suggestions by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    suggestions.sort(key=lambda x: priority_order.get(x.priority, 4))

    return suggestions


# --- API Endpoints ---

@router.get("/analyze", response_model=Dict[str, Any])
async def analyze_infrastructure(
    model_name: str = "qwen2.5-coder:7b",
    model_type: str = "LLM",
    parameters: str = "7B",
    framework: str = "PyTorch",
    db: Session = Depends(get_db)
):
    """
    Analyze current infrastructure for AI workloads

    Returns current hardware assessment and basic recommendations
    """
    try:
        # Create basic infrastructure model
        infra_model = InfrastructureModel(
            model_name=model_name,
            model_type=model_type,
            parameters=parameters,
            framework=framework,
            current_hardware={
                "cpu_cores": psutil.cpu_count(logical=False),
                "cpu_threads": psutil.cpu_count(logical=True),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2)
            },
            performance_requirements={
                "latency_ms": "<100",
                "throughput_req": "high"
            }
        )

        # Assess current infrastructure
        assessment = await assess_current_infrastructure(infra_model)

        return {
            "status": "success",
            "infrastructure_model": infra_model.model_name,
            "assessment": assessment,
            "recommendations": [
                "Consider GPU acceleration for better performance",
                "Implement model quantization to reduce memory usage",
                "Monitor resource utilization during inference"
            ]
        }
    except Exception as e:
        logger.error(f"Error analyzing infrastructure: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Infrastructure analysis failed: {str(e)}"
        )

@router.post("/optimize", response_model=OptimizationPlan, status_code=status.HTTP_200_OK)
async def optimize_infrastructure(
    infrastructure_model: InfrastructureModel,
    db: Session = Depends(get_db)
):
    """
    Generate an optimization plan for AI infrastructure

    Analyzes current infrastructure and provides recommendations for optimization
    """
    try:
        # Assess current infrastructure
        current_assessment = await assess_current_infrastructure(infrastructure_model)

        # Generate optimization suggestions
        suggestions = await generate_optimization_suggestions(
            infrastructure_model,
            current_assessment
        )

        # Create summary
        summary = {
            "total_suggestions": len(suggestions),
            "critical_issues": sum(1 for s in suggestions if s.priority == "critical"),
            "high_priority_issues": sum(1 for s in suggestions if s.priority == "high"),
            "medium_priority_issues": sum(1 for s in suggestions if s.priority == "medium"),
            "low_priority_issues": sum(1 for s in suggestions if s.priority == "low"),
            "categories": {
                "hardware": sum(1 for s in suggestions if s.category == "hardware"),
                "software": sum(1 for s in suggestions if s.category == "software"),
                "configuration": sum(1 for s in suggestions if s.category == "configuration"),
                "scaling": sum(1 for s in suggestions if s.category == "scaling")
            }
        }

        # Log successful optimization
        logger.info(
            f"Generated optimization plan for model {infrastructure_model.model_name}: "
            f"{len(suggestions)} suggestions"
        )

        # Return optimization plan
        return OptimizationPlan(
            plan_id=f"opt-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            infrastructure_model=infrastructure_model,
            current_assessment=current_assessment,
            suggestions=suggestions,
            summary=summary,
            generated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in infrastructure optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating optimization plan"
        )


@router.get("/health")
async def get_infrastructure_health():
    """
    Get current infrastructure health status
    """
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Get GPU status if available
        gpu_status = []
        try:
            gpu_info = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu", 
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if gpu_info.returncode == 0:
                gpu_lines = gpu_info.stdout.strip().split('\n')
                for line in gpu_lines:
                    parts = line.split(', ')
                    if len(parts) >= 3:
                        gpu_status.append({
                            "name": parts[0],
                            "utilization_percent": int(parts[1]),
                            "temperature_c": int(parts[2])
                        })
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        return {
            "cpu": {
                "utilization_percent": cpu_percent,
                "status": "healthy" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical"
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent_used": memory.percent,
                "status": "healthy" if memory.percent < 80 else "warning" if memory.percent < 95 else "critical"
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent_used": disk.percent,
                "status": "healthy" if disk.percent < 80 else "warning" if disk.percent < 95 else "critical"
            },
            "gpu": gpu_status
        }

    except Exception as e:
        logger.error(f"Error getting infrastructure health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get infrastructure health status"
        )
