from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from typing import Dict, Any, Optional

# Initialize OpenTelemetry TracerProvider
resource = Resource.create({"service.name": "startup-generator-agent"})
provider = TracerProvider(resource=resource)
tracer = provider.get_tracer("startup-generator-agent.tracer")

def start_agent_span(agent_name: str, project_id: str, action: str = "execute"):
    """
    Creates and starts an OpenTelemetry span for multi-agent distributed tracing.
    """
    span = tracer.start_span(f"{agent_name}.{action}")
    span.set_attribute("project.id", project_id)
    span.set_attribute("agent.name", agent_name)
    span.set_attribute("system.architecture", "multi-agent-adk")
    return span
