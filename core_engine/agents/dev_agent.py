from __future__ import annotations

from dataclasses import dataclass

from .pm_agent import ProductSchema


@dataclass(slots=True)
class GeneratedEndpoint:
    path: str
    method: str
    source: str
    model_fields: list[str]


@dataclass(slots=True)
class DeveloperAgent:
    """Produces a safe, framework-native endpoint plan from the PM contract."""

    async def run(self, schema: ProductSchema) -> list[GeneratedEndpoint]:
        resource = schema.resource
        plural = resource if resource.endswith("s") else f"{resource}s"
        fields = [f.name for f in schema.fields]
        model = ", ".join(fields)
        return [
            GeneratedEndpoint(f"/{plural}", "POST", "create_resource", fields),
            GeneratedEndpoint(f"/{plural}", "GET", "list_resources", fields),
            GeneratedEndpoint(f"/{plural}/{{resource_id}}", "GET", "get_resource", fields),
            GeneratedEndpoint(f"/{plural}/{{resource_id}}", "DELETE", "delete_resource", fields),
        ]
