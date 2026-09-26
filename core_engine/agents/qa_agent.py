from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Finding:
    rule: str
    severity: str
    path: str
    line: int
    message: str


@dataclass(slots=True)
class QAReport:
    passed: bool
    findings: list[Finding] = field(default_factory=list)


@dataclass(slots=True)
class QAAgent:
    """OWASP-aligned static security gate with deterministic Python AST checks."""

    forbidden_calls = {"eval", "exec", "compile", "__import__"}
    dangerous_modules = {"pickle", "marshal", "telnetlib"}

    async def run(self, root: str | Path = ".") -> QAReport:
        base = Path(root)
        files = list(base.rglob("*.py")) if base.exists() else []
        results = await asyncio.gather(*(asyncio.to_thread(self._scan_file, p) for p in files))
        findings = [f for group in results for f in group]
        return QAReport(passed=not any(f.severity == "HIGH" for f in findings), findings=findings)

    def _scan_file(self, path: Path) -> list[Finding]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            return [Finding("A05", "HIGH", str(path), 1, f"Unparseable source: {exc}")]
        findings: list[Finding] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in self.forbidden_calls:
                findings.append(Finding("A03", "HIGH", str(path), node.lineno, f"Dangerous dynamic execution: {node.func.id}"))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in self.dangerous_modules:
                        findings.append(Finding("A08", "HIGH", str(path), node.lineno, f"Unsafe serialization/network module: {alias.name}"))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"execute", "executemany"}:
                if node.args and isinstance(node.args[0], ast.BinOp):
                    findings.append(Finding("A03", "HIGH", str(path), node.lineno, "Possible SQL string construction before execute"))
        return findings
