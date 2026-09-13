import hashlib
import json
import secrets
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from random import Random
from typing import Any

from topology_benchmark.application.catalog import BenchmarkCatalog
from topology_benchmark.application.errors import InvalidApplicationRequestError
from topology_benchmark.core.models import GenerationRequest, Problem
from topology_benchmark.pipeline.config import PipelineConfig
from topology_benchmark.pipeline.providers import ModelProvider, build_provider
from topology_benchmark.pipeline.scoring import extract_final_answer, score_answer


@dataclass(frozen=True, slots=True)
class GeneratedItem:
    item_id: str
    domain: str
    problem: Problem[Any]


class BenchmarkPipeline:
    def __init__(self, config: PipelineConfig, catalog: BenchmarkCatalog) -> None:
        self.config = config
        self._catalog = catalog
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        for domain, config in self.config.domains.items():
            self._catalog.validate_domain(domain)
            for recipe in config.recipes:
                self._catalog.validate_recipe(domain, recipe)

    def run(self, *, evaluate: bool = True) -> Path:
        if evaluate and self.config.provider is None:
            raise InvalidApplicationRequestError(
                "evaluation requested but no provider is configured"
            )
        root_seed = self.config.seed if self.config.seed is not None else secrets.randbits(128)
        identity = _manifest_config(self.config)
        identity["output_dir"] = "<excluded>"
        run_id = _digest(
            f"run:{root_seed}:{json.dumps(identity, sort_keys=True, separators=(',', ':'))}"
        )[:16]
        run_dir = self.config.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        media_dir = run_dir / "media"
        media_dir.mkdir()
        items = self._generate(root_seed)
        self._write_dataset(run_dir, media_dir, items)
        manifest = self._manifest(root_seed, run_id, items)
        _write_json(run_dir / "manifest.private.json", manifest)
        if evaluate:
            assert self.config.provider is not None
            self._evaluate(run_dir, items, build_provider(self.config.provider))
        return run_dir

    def _generate(self, root_seed: int) -> tuple[GeneratedItem, ...]:
        scheduler = Random(_derive_seed(root_seed, "schedule"))
        generated = []
        for index in range(self.config.size):
            domain = _weighted_choice(
                scheduler, {key: value.weight for key, value in self.config.domains.items()}
            )
            domain_config = self.config.domains[domain]
            level = _weighted_choice(scheduler, domain_config.generation_levels)
            seed = _derive_seed(root_seed, f"item:{index}:{domain}")
            request = GenerationRequest(seed=seed, difficulty=int(level))
            if domain_config.recipes:
                problem = self._catalog.generate_recipe(
                    domain=domain,
                    request=request,
                    recipe_id=_weighted_choice(scheduler, domain_config.recipes),
                )
            else:
                problem = self._catalog.generate(domain=domain, request=request)
            item_id = _problem_id(index, domain, problem)
            generated.append(GeneratedItem(item_id, domain, problem))
        return tuple(generated)

    @staticmethod
    def _write_dataset(run_dir: Path, media_dir: Path, items: tuple[GeneratedItem, ...]) -> None:
        public_records = []
        private_records = []
        for item in items:
            media = []
            for index, section in enumerate(item.problem.sections):
                suffix = _media_suffix(section.media_type)
                path = media_dir / f"{item.item_id}-{index}{suffix}"
                path.write_text(section.content, encoding="utf-8")
                media.append(
                    {
                        "media_type": section.media_type,
                        "path": path.relative_to(run_dir).as_posix(),
                    }
                )
            public_records.append(
                {
                    "id": item.item_id,
                    "domain": item.domain,
                    "question": item.problem.question,
                    "media": media,
                }
            )
            private_records.append(
                {
                    "id": item.item_id,
                    "answer": item.problem.answer,
                    "generator_seed": item.problem.seed,
                    "question_kind": item.problem.question_kind,
                }
            )
        _write_jsonl(run_dir / "dataset.public.jsonl", public_records)
        _write_jsonl(run_dir / "ground_truth.private.jsonl", private_records)

    def _manifest(
        self, root_seed: int, run_id: str, items: tuple[GeneratedItem, ...]
    ) -> dict[str, Any]:
        combinations = Counter((item.domain, item.problem.question_kind) for item in items)
        return {
            "schema_version": 1,
            "run_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "root_seed": root_seed,
            "size": len(items),
            "realized_distribution": {
                f"{domain}/{kind}": count for (domain, kind), count in sorted(combinations.items())
            },
            "resolved_config": _manifest_config(self.config),
        }

    def _evaluate(
        self, run_dir: Path, items: tuple[GeneratedItem, ...], provider: ModelProvider
    ) -> None:
        predictions = []
        correct = Counter()
        totals = Counter()
        max_retries = self.config.provider.max_retries if self.config.provider else 0
        for item in items:
            response = ""
            error = None
            for _ in range(max_retries + 1):
                try:
                    response = provider.answer(item.problem.question, item.problem.sections)
                    error = None
                    break
                except Exception as caught:  # A provider failure is an item result, not a lost run.
                    error = f"{type(caught).__name__}: {caught}"
            is_correct = error is None and score_answer(item.problem.answer, response)
            kind = item.problem.question_kind
            key = f"{item.domain}/{kind}"
            totals[key] += 1
            correct[key] += int(is_correct)
            predictions.append(
                {
                    "id": item.item_id,
                    "response": response,
                    "extracted_answer": extract_final_answer(response),
                    "correct": is_correct,
                    "error": error,
                }
            )
        _write_jsonl(run_dir / "predictions.jsonl", predictions)
        total = sum(totals.values())
        failures = sum(prediction["error"] is not None for prediction in predictions)
        _write_json(
            run_dir / "summary.json",
            {
                "provider": provider.identity,
                "accuracy": sum(correct.values()) / total if total else 0.0,
                "correct": sum(correct.values()),
                "total": total,
                "failed_requests": failures,
                "by_question_kind": {
                    key: {"accuracy": correct[key] / count, "correct": correct[key], "total": count}
                    for key, count in sorted(totals.items())
                },
            },
        )


def _weighted_choice[T](rng: Random, weights: dict[T, float]) -> T:
    total = sum(weights.values())
    point = rng.random() * total
    cumulative = 0.0
    for value, weight in weights.items():
        cumulative += weight
        if point < cumulative:
            return value
    return next(reversed(weights))


def _derive_seed(root_seed: int, label: str) -> int:
    digest = hashlib.blake2b(f"{root_seed}:{label}".encode(), digest_size=16).digest()
    return int.from_bytes(digest)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _problem_id(index: int, domain: str, problem: Problem[Any]) -> str:
    visible = {
        "position": index,
        "domain": domain,
        "question": problem.question,
        "sections": [
            {"media_type": section.media_type, "content": section.content}
            for section in problem.sections
        ],
    }
    return _digest(json.dumps(visible, sort_keys=True, separators=(",", ":")))[:20]


def _media_suffix(media_type: str) -> str:
    return {"image/svg+xml": ".svg", "image/png": ".png", "text/plain": ".txt"}.get(
        media_type, ".bin"
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value


def _manifest_config(config: PipelineConfig) -> dict[str, Any]:
    value = _jsonable(config.model_dump())
    provider = value.get("provider")
    if isinstance(provider, dict):
        provider["extra_headers"] = {key: "<redacted>" for key in provider.get("extra_headers", {})}
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    path.write_text(text, encoding="utf-8")
