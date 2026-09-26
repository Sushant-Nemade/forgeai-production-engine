from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class FieldSpec(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")
    type: str = Field(pattern=r"^(string|integer|number|boolean)$")
    required: bool = True


class ProductSchema(BaseModel):
    resource: str = Field(pattern=r"^[a-z][a-z0-9-]{1,48}$")
    fields: list[FieldSpec] = Field(min_length=1, max_length=32)
    auth_required: bool = True


@dataclass(slots=True)
class ProductManagerAgent:
    """Turns a human product brief into a constrained, typed API schema."""

    async def run(self, brief: str) -> ProductSchema:
        text = brief.strip()
        if not text:
            raise ValueError("Product brief must not be empty")
        resource_match = re.search(r"(?:resource|entity|model)\s*[:=]\s*([a-zA-Z0-9_-]+)", text, re.I)
        resource = (resource_match.group(1) if resource_match else "item").lower().replace("_", "-")
        field_matches = re.findall(r"\b([a-z][a-z0-9_]{1,30})\s*\((string|integer|number|boolean)\)", text, re.I)
        fields: list[FieldSpec] = []
        seen: set[str] = set()
        for name, kind in field_matches:
            name = name.lower()
            if name not in seen and name not in {"id", "created_at", "updated_at"}:
                fields.append(FieldSpec(name=name, type=kind.lower(), required=True))
                seen.add(name)
        if not fields:
            fields = [FieldSpec(name="name", type="string", required=True)]
        return ProductSchema(resource=resource, fields=fields)

    @staticmethod
    def schema_mapping(schema: ProductSchema) -> dict[str, Any]:
        return {
            "table": schema.resource.replace("-", "_"),
            "columns": [{"name": f.name, "type": f.type, "nullable": not f.required} for f in schema.fields],
            "operations": ["create", "list", "get", "delete"],
            "authentication": "JWT" if schema.auth_required else "none",
        }
