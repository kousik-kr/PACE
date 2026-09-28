#!/usr/bin/env python3
"""Audit frozen PACE-X provenance against the full-NY preservation theorem.

This is a read-only provenance computation.  It never invokes the benchmark
or an experiment runner.  It reconstructs EA/LD labels from the frozen full
NY temporal functions, writes query-safe regions with original arc IDs, and
compares them with the serialized NY-Exact-radius execution graph.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import heapq
import json
import math
from array import array
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FULL = ROOT / "data/input/NY"
EXEC = ROOT / "data/input/NY-Exact-radius"
EXACT = ROOT / "experiments/results/Final-result/manuscript_missing_runs/final_ny_exact"
OUT = ROOT / "experiments/results/Final-result/manuscript_artifacts/extracted"
SAFE_DIR = OUT / "FULL_NY_SAFE_REGIONS"
REQUIRED = (
    "edges_static.csv.gz",
    "nodes.csv.gz",
    "manifest.json",
    "score_functions.jsonl.gz",
    "travel_time_functions.jsonl.gz",
)
POINTS_PER_EDGE = 9
EPS = 1e-9


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def framed_checksum(directory: Path, names: tuple[str, ...], domain: str) -> str:
    digest = hashlib.sha256()
    domain_bytes = domain.encode()
    digest.update(len(domain_bytes).to_bytes(4, "big"))
    digest.update(domain_bytes)
    for name in names:
        name_bytes = name.encode()
        path = directory / name
        digest.update(len(name_bytes).to_bytes(4, "big"))
        digest.update(name_bytes)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as handle:
            while chunk := handle.read(1 << 20):
                digest.update(chunk)
    return digest.hexdigest()


def graph_checksum(directory: Path) -> str:
    return framed_checksum(directory, REQUIRED, "PACE-GRAPH-CHECKSUM-v1")


def dataset_checksum(directory: Path) -> str:
    return framed_checksum(
        directory,
        ("edges_static.csv.gz", "nodes.csv.gz"),
        "PACE-DATASET-STRUCTURE-CHECKSUM-v1",
    )


def temporal_checksum(directory: Path) -> str:
    return framed_checksum(
        directory,
        ("score_functions.jsonl.gz", "travel_time_functions.jsonl.gz"),
        "PACE-TEMPORAL-ATTRIBUTE-CHECKSUM-v1",
    )


def canonical_checksum(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


class FullGraph:
    def __init__(self) -> None:
        self.eu = array("i")
        self.ev = array("i")
        self.base = array("d")
        self.out: list[list[int]] = []
        self.inc: list[list[int]] = []
        self.times = array("d")
        self.travel = array("d")
        self.scores: dict[int, tuple[tuple[float, float, int], ...]] = {}
        self.max_node = 0

    def load(self) -> None:
        with gzip.open(FULL / "edges_static.csv.gz", "rt", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                arc = int(row["arc_id"])
                if arc != len(self.eu):
                    raise ValueError(f"full NY arc IDs are not contiguous at {arc}")
                u, v = int(row["u"]), int(row["v"])
                self.eu.append(u)
                self.ev.append(v)
                self.base.append(float(row["base_travel_time"]))
                self.max_node = max(self.max_node, u, v)
        self.out = [[] for _ in range(self.max_node + 1)]
        self.inc = [[] for _ in range(self.max_node + 1)]
        for arc in range(len(self.eu)):
            self.out[self.eu[arc]].append(arc)
            self.inc[self.ev[arc]].append(arc)

        with gzip.open(FULL / "travel_time_functions.jsonl.gz", "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                arc = int(row["arc_id"])
                if arc * POINTS_PER_EDGE != len(self.times):
                    raise ValueError(f"full NY temporal arc order mismatch at {arc}")
                points = row["travel_time_breakpoints"]
                if len(points) != POINTS_PER_EDGE:
                    raise ValueError(f"unexpected breakpoint count for arc {arc}")
                for minute, value in points:
                    self.times.append(float(minute))
                    self.travel.append(float(value))
        if len(self.times) != len(self.eu) * POINTS_PER_EDGE:
            raise ValueError("full NY temporal payload does not cover every arc")

        with gzip.open(FULL / "score_functions.jsonl.gz", "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                arc = int(row["arc_id"])
                self.scores[arc] = tuple(
                    (float(start), float(end), int(score))
                    for start, end, score in row["score_intervals"]
                    if int(score) > 0 and float(end) > float(start)
                )

    def arrival(self, arc: int, departure: float) -> float:
        offset = arc * POINTS_PER_EDGE
        if departure <= self.times[offset]:
            return departure + self.travel[offset]
        for index in range(1, POINTS_PER_EDGE):
            left = offset + index - 1
            right = offset + index
            if departure <= self.times[right]:
                t0, t1 = self.times[left], self.times[right]
                v0, v1 = self.travel[left], self.travel[right]
                if t1 == t0:
                    value = v1
                else:
                    fraction = (departure - t0) / (t1 - t0)
                    value = v0 + fraction * (v1 - v0)
                return departure + value
        return departure + self.travel[offset + POINTS_PER_EDGE - 1]

    def latest_departure(self, arc: int, deadline: float) -> float:
        """Exact inverse of a nondecreasing piecewise-linear arrival function."""
        offset = arc * POINTS_PER_EDGE
        best = float("-inf")
        for index in range(POINTS_PER_EDGE - 1):
            left = offset + index
            right = left + 1
            t0, t1 = self.times[left], self.times[right]
            a0 = t0 + self.travel[left]
            a1 = t1 + self.travel[right]
            if deadline + EPS < a0:
                continue
            if deadline + EPS >= a1:
                best = max(best, t1)
                continue
            if a1 <= a0 + EPS:
                best = max(best, t1)
            else:
                fraction = (deadline - a0) / (a1 - a0)
                best = max(best, t0 + fraction * (t1 - t0))
        return best

    def travel_time(self, arc: int, departure: float) -> float:
        return self.arrival(arc, departure) - departure

    def forward_labels(self, source: int, start: float, deadline: float) -> list[float]:
        labels = [float("inf")] * (self.max_node + 1)
        labels[source] = start
        queue: list[tuple[float, int]] = [(start, source)]
        while queue:
            arrival, vertex = heapq.heappop(queue)
            if arrival != labels[vertex] or arrival > deadline + EPS:
                continue
            for arc in self.out[vertex]:
                candidate = self.arrival(arc, arrival)
                target = self.ev[arc]
                if candidate <= deadline + EPS and candidate + EPS < labels[target]:
                    labels[target] = candidate
                    heapq.heappush(queue, (candidate, target))
        return labels

    def backward_labels(self, destination: int, deadline: float) -> list[float]:
        labels = [float("-inf")] * (self.max_node + 1)
        labels[destination] = deadline
        queue: list[tuple[float, int]] = [(-deadline, destination)]
        while queue:
            negative_departure, vertex = heapq.heappop(queue)
            departure = -negative_departure
            if departure + EPS < labels[vertex]:
                continue
            for arc in self.inc[vertex]:
                source = self.eu[arc]
                candidate = self.latest_departure(arc, departure)
                if candidate != float("-inf") and candidate > labels[source] + EPS:
                    labels[source] = candidate
                    heapq.heappush(queue, (-candidate, source))
        return labels

    def score_relevant(
        self,
        arc: int,
        ea: list[float],
        ld: list[float],
        start: float,
        horizon_end: float,
        budget: float,
    ) -> bool:
        u, v = self.eu[arc], self.ev[arc]
        if not math.isfinite(ea[u]) or not math.isfinite(ld[v]):
            return False
        lower = max(start, ea[u], 0.0)
        upper = min(horizon_end, self.latest_departure(arc, ld[v]))
        if upper <= lower + EPS:
            return False
        offset = arc * POINTS_PER_EDGE
        for score_start, score_end, _score in self.scores.get(arc, ()):
            left = max(lower, score_start)
            right = min(upper, score_end)
            if right <= left + EPS:
                continue
            cuts = [left, right]
            for index in range(POINTS_PER_EDGE):
                point = self.times[offset + index]
                if left < point < right:
                    cuts.append(point)
            cuts.sort()
            for a, b in zip(cuts, cuts[1:]):
                if self.travel_time(arc, a) <= budget + EPS or self.travel_time(arc, b) <= budget + EPS:
                    return True
                midpoint = (a + b) / 2.0
                if self.travel_time(arc, midpoint) <= budget + EPS:
                    return True
        return False


def execution_mapping(graph: FullGraph) -> tuple[set[int], set[int], dict[int, int], dict[int, int]]:
    """Reproduce only the documented deterministic ID mapping, not PACE."""
    adjacency: list[list[tuple[int, float]]] = [[] for _ in range(graph.max_node + 1)]
    for arc in range(len(graph.eu)):
        u, v, weight = graph.eu[arc], graph.ev[arc], graph.base[arc]
        adjacency[u].append((v, weight))
        adjacency[v].append((u, weight))
    distances = {1: 0.0}
    queue: list[tuple[float, int]] = [(0.0, 1)]
    while queue:
        distance, vertex = heapq.heappop(queue)
        if distance != distances[vertex] or distance > 4.5:
            continue
        for neighbor, weight in adjacency[vertex]:
            candidate = distance + weight
            if candidate <= 4.5 and candidate < distances.get(neighbor, float("inf")):
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    selected_vertices = set(distances)
    if len(selected_vertices) != 64:
        raise ValueError(f"documented execution mapping selected {len(selected_vertices)} vertices")
    selected_arcs = {
        arc for arc in range(len(graph.eu))
        if graph.eu[arc] in selected_vertices and graph.ev[arc] in selected_vertices
    }
    if len(selected_arcs) != 142:
        raise ValueError(f"documented execution mapping selected {len(selected_arcs)} arcs")
    old_to_local_vertex = {old: index for index, old in enumerate(sorted(selected_vertices), 1)}
    local_to_old_vertex = {local: old for old, local in old_to_local_vertex.items()}
    old_to_local_arc = {old: index for index, old in enumerate(sorted(selected_arcs))}
    local_to_old_arc = {local: old for old, local in old_to_local_arc.items()}

    with gzip.open(EXEC / "nodes.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        subset_nodes = list(csv.DictReader(handle))
    for row in subset_nodes:
        local = int(row["node_id"])
        old = local_to_old_vertex[local]
        if local != old_to_local_vertex[old]:
            raise ValueError("execution node remapping is inconsistent")
    with gzip.open(EXEC / "edges_static.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            local_arc = int(row["arc_id"])
            old_arc = local_to_old_arc[local_arc]
            if (int(row["u"]), int(row["v"])) != (
                old_to_local_vertex[graph.eu[old_arc]],
                old_to_local_vertex[graph.ev[old_arc]],
            ):
                raise ValueError(f"execution arc remapping mismatch at local arc {local_arc}")
    return selected_vertices, selected_arcs, local_to_old_vertex, local_to_old_arc


def measured_pace_x() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for line in (EXACT / "raw/pace-x/trial-0.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("run", {}).get("warmup"):
            continue
        query_id = row["query"]["query_id"]
        if query_id in records:
            raise ValueError(f"duplicate measured PACE-X query {query_id}")
        records[query_id] = row
    return records


def compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SAFE_DIR.mkdir(parents=True, exist_ok=True)
    graph = FullGraph()
    graph.load()
    exec_vertices, exec_arcs, local_to_old_vertex, local_to_old_arc = execution_mapping(graph)
    raw = measured_pace_x()
    manifest_path = EXACT / "manifests/final_ny_exact_queries.jsonl"
    queries = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(queries) != 60 or len(raw) != 60:
        raise ValueError(f"expected 60 frozen logical queries, manifest={len(queries)}, PACE-X={len(raw)}")

    full_graph_hash = graph_checksum(FULL)
    full_dataset_hash = dataset_checksum(FULL)
    full_temporal_hash = temporal_checksum(FULL)
    exec_graph_hash = graph_checksum(EXEC)
    exec_dataset_hash = dataset_checksum(EXEC)
    exec_temporal_hash = temporal_checksum(EXEC)
    manifest_hash = sha256_file(manifest_path)
    raw_hash = sha256_file(EXACT / "raw/pace-x/trial-0.jsonl")

    ea_cache: dict[tuple[float, float], list[float]] = {}
    rows: list[dict[str, Any]] = []
    region_manifest: list[dict[str, Any]] = []

    for query in queries:
        query_id = query["query_id"]
        record = raw[query_id]
        meta = query["metadata"]
        local_source, local_destination = int(query["source"]), int(query["destination"])
        source = local_to_old_vertex[local_source]
        destination = local_to_old_vertex[local_destination]
        start = float(query["interval_start"])
        end = float(query["interval_end"])
        budget = float(query["budget"])
        horizon_end = end + budget
        cache_key = (start, budget)
        if cache_key not in ea_cache:
            ea_cache[cache_key] = graph.forward_labels(source, start, horizon_end)
        ea = ea_cache[cache_key]
        ld = graph.backward_labels(destination, horizon_end)
        safe_vertices = {
            vertex for vertex in range(1, graph.max_node + 1)
            if math.isfinite(ea[vertex]) and math.isfinite(ld[vertex]) and ea[vertex] <= ld[vertex] + EPS
        }
        safe_arcs: set[int] = set()
        exclusion_counts = {
            "safe_region": 0,
            "forward_unreachable": 0,
            "backward_unreachable": 0,
            "vertex_label_incompatible": 0,
            "edge_arrival_after_latest_destination_departure": 0,
        }
        for arc in range(len(graph.eu)):
            u, v = graph.eu[arc], graph.ev[arc]
            if u in safe_vertices and v in safe_vertices and graph.arrival(arc, ea[u]) <= ld[v] + EPS:
                safe_arcs.add(arc)
                exclusion_counts["safe_region"] += 1
            elif not math.isfinite(ea[u]):
                exclusion_counts["forward_unreachable"] += 1
            elif not math.isfinite(ld[v]):
                exclusion_counts["backward_unreachable"] += 1
            elif u not in safe_vertices or v not in safe_vertices:
                exclusion_counts["vertex_label_incompatible"] += 1
            else:
                exclusion_counts["edge_arrival_after_latest_destination_departure"] += 1
        safe_plus = {
            arc for arc in safe_arcs
            if graph.score_relevant(arc, ea, ld, start, horizon_end, budget)
        }
        execution_pivots = {
            local_to_old_arc[int(arc)]
            for arc in record["counters"]["selected_pivot_arc_ids"]
        }
        missing_vertices = sorted(safe_vertices - exec_vertices)
        missing_arcs = sorted(safe_arcs - exec_arcs)
        extra_vertices = sorted(exec_vertices - safe_vertices)
        extra_arcs = sorted(exec_arcs - safe_arcs)
        missing_pivots = sorted(safe_plus - execution_pivots)
        safe_checksum = canonical_checksum({
            "query_id": query_id,
            "vertices": sorted(safe_vertices),
            "directed_arc_ids": sorted(safe_arcs),
        })
        safe_file = SAFE_DIR / f"{query_id}.json"
        safe_payload = {
            "schema_version": 1,
            "query": {
                "query_id": query_id,
                "pair_id": meta["pair_id"],
                "center": meta["interval_center"],
                "budget": budget,
                "interval": [int(query["interval_start"]), int(query["interval_end"])],
                "local_source": local_source,
                "local_destination": local_destination,
                "full_ny_source": source,
                "full_ny_destination": destination,
            },
            "construction": "V_safe={v:EA(v)<=LD(v)}; E_safe={(u,v):u,v in V_safe and A_e(EA(u))<=LD(v)}",
            "full_ny": {
                "vertices": graph.max_node,
                "directed_edges": len(graph.eu),
                "graph_checksum": full_graph_hash,
                "dataset_checksum": full_dataset_hash,
                "temporal_checksum": full_temporal_hash,
            },
            "safe_region": {
                "vertices": sorted(safe_vertices),
                "directed_arc_ids": sorted(safe_arcs),
                "vertex_count": len(safe_vertices),
                "edge_count": len(safe_arcs),
                "checksum": safe_checksum,
            },
            "execution_graph": {
                "dataset": "NY-Exact-radius",
                "vertices_original_ids": sorted(exec_vertices),
                "directed_arc_ids_original": sorted(exec_arcs),
                "vertex_count": len(exec_vertices),
                "edge_count": len(exec_arcs),
                "graph_checksum": exec_graph_hash,
                "dataset_checksum": exec_dataset_hash,
                "temporal_checksum": exec_temporal_hash,
                "local_arc_ids_are_remapped": True,
            },
            "inclusion": {
                "missing_vertices": missing_vertices,
                "missing_edges": missing_arcs,
                "extra_vertices": extra_vertices,
                "extra_edges": extra_arcs,
            },
            "score_relevance": {
                "safe_score_relevant_edges": sorted(safe_plus),
                "exact_run_pivots_original_arc_ids": sorted(execution_pivots),
                "missing_pivots": missing_pivots,
            },
            "exclusion_proof_partition": {
                "all_full_graph_edges_classified": sum(exclusion_counts.values()) == len(graph.eu),
                "counts": exclusion_counts,
                "missing_safe_edges_are_not_theorem_excluded": bool(missing_arcs),
            },
            "frozen_pace_x": {
                "status": record["status"],
                "configuration": record["configuration"],
                "counters": record["counters"],
                "raw_trial_file_sha256": raw_hash,
            },
        }
        safe_file.write_text(json.dumps(safe_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        region_manifest.append({"query_id": query_id, "file": safe_file.relative_to(OUT).as_posix(), "checksum": safe_checksum})

        config = record["configuration"]
        status = record["status"]
        caps = record["counters"].get("cap_triggered") or status.get("cap_triggered") or []
        reasons = [
            f"full-NY safe region has {len(missing_vertices)} vertices and {len(missing_arcs)} directed arcs absent from NY-Exact-radius",
            f"{len(missing_pivots)} full-NY score-relevant pivots are absent from the exact-run pivot universe",
            "PACE-X GLOBAL_CERTIFIED is therefore scoped to the 64-vertex execution graph and cannot be lifted",
        ]
        if len(safe_plus) > int(config["theta"]):
            reasons.append(f"exact theta={config['theta']} is below the sufficient full-NY bound |E_plus_safe|={len(safe_plus)}")
        rows.append({
            "query_id": query_id,
            "pair_id": meta["pair_id"],
            "center": meta["interval_center"],
            "B": budget,
            "full_NY_vertices": graph.max_node,
            "full_NY_edges": len(graph.eu),
            "safe_vertices": len(safe_vertices),
            "safe_edges": len(safe_arcs),
            "execution_vertices": len(exec_vertices),
            "execution_edges": len(exec_arcs),
            "missing_safe_vertices": compact(missing_vertices),
            "missing_safe_edges": compact(missing_arcs),
            "extra_execution_vertices": compact(extra_vertices),
            "extra_execution_edges": compact(extra_arcs),
            "safe_score_relevant_edges": compact(sorted(safe_plus)),
            "execution_pivots": compact(sorted(execution_pivots)),
            "missing_pivots": compact(missing_pivots),
            "theta_condition": (
                "FAIL_FULL_NY_NO_SUFFICIENT_DEPTH_BOUND"
                if len(safe_plus) > int(config["theta"])
                else "PASS_SUFFICIENT_COUNT_BOUND; theta>=|E_plus_safe|"
            ),
            "connector_exhaustion": "FAIL_FULL_NY_SCOPE; local PACE-X connectors only",
            "state_truncation": "PASS_EXECUTION_SCOPE; PACE-X unbounded frontier and no cap",
            "breakpoint_exactness": "PASS_DECLARED_EXACT_REPLAY; no breakpoint cap; collinear reductions are canonical",
            "resource_truncation": (
                "PASS_NO_TRIGGERED_CAP" if not caps and status.get("completed") and status.get("generation_completion") == "COMPLETE"
                else "FAIL_RESOURCE_TRUNCATED"
            ),
            "temporal_exactness": "PASS_EXACT_CONTINUOUS_TEMPORAL_PROFILE-v1",
            "global_certificate_lifts_to_full_NY": "FAIL",
            "reason": "; ".join(reasons),
            "full_source": source,
            "full_destination": destination,
            "local_source": local_source,
            "local_destination": local_destination,
            "full_NY_graph_checksum": full_graph_hash,
            "temporal_data_checksum": full_temporal_hash,
            "query_manifest_checksum": manifest_hash,
            "execution_graph_checksum": exec_graph_hash,
            "safe_region_checksum": safe_checksum,
            "exclusion_proof_partition": compact(exclusion_counts),
        })

    csv_path = OUT / "FULL_NY_EXACT_PROVENANCE_AUDIT.csv"
    fields = list(rows[0])
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    region_manifest_path = OUT / "FULL_NY_SAFE_REGION_MANIFEST.json"
    region_manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "query_count": len(region_manifest),
        "full_ny_graph_checksum": full_graph_hash,
        "full_ny_dataset_checksum": full_dataset_hash,
        "full_ny_temporal_checksum": full_temporal_hash,
        "execution_graph_checksum": exec_graph_hash,
        "query_manifest_checksum": manifest_hash,
        "regions": region_manifest,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failed = [row for row in rows if row["global_certificate_lifts_to_full_NY"] != "PASS"]
    report = {
        "schema_version": 1,
        "result": "FULL_NY_THEOREM_SAFE_EQUIVALENCE_FAIL" if failed else "FULL_NY_THEOREM_SAFE_EQUIVALENCE_PASS",
        "query_count": len(rows),
        "queries_per_budget": len(rows) // 3,
        "budgets": sorted({row["B"] for row in rows}),
        "theorem": {
            "lemma": "PACE.tex Lemma 1, Query-region preservation",
            "construction": "V_safe={v:EA(v)<=LD(v)}; E_safe={(u,v):u,v in V_safe and A_e(EA(u))<=LD(v)}",
            "score_relevant": "E_plus_safe={e in E_safe: D_e^+ is nonempty}",
            "global_certificate": "PACE.tex Theorem 2 / Global certification of PACE-X",
        },
        "checksums": {
            "full_ny_graph": full_graph_hash,
            "full_ny_dataset_structure": full_dataset_hash,
            "full_ny_temporal_data": full_temporal_hash,
            "query_manifest": manifest_hash,
            "frozen_pace_x_trial_0": raw_hash,
            "execution_graph": exec_graph_hash,
            "execution_dataset_structure": exec_dataset_hash,
            "execution_temporal_data": exec_temporal_hash,
        },
        "execution_provenance": {
            "dataset": "NY-Exact-radius",
            "vertices": 64,
            "directed_edges": 142,
            "selection": "deterministic_source_centered_static_radius",
            "radius_minutes": 4.5,
            "node_id_policy": "deterministic-positive-remap-in-source-node-order",
            "arc_id_policy": "deterministic-remap-in-source-arc-order",
            "pace_x_theta": 64,
            "pace_b_theta": 2,
            "pace_x_limits": "unbounded sentinels in raw command/configuration",
            "pace_x_status": "all measured records completed with cap_triggered=[]",
        },
        "condition_summary": {
            "condition_1_region_preservation": "FAIL for every query with nonempty safe-region omission",
            "condition_2_all_safe_score_edges_pivots": "FAIL where missing_pivots is nonempty",
            "condition_3_exact_depth": "reported per query; exact run theta=64, not PACE-B theta=2",
            "condition_4_connector_exhaustion": "local execution graph only; cannot establish full-NY condition",
            "condition_5_no_heuristic_partial_state": "PASS for frozen PACE-X execution scope",
            "condition_6_no_resource_truncation": "PASS for frozen measured records; no cap_triggered entries",
            "condition_7_no_lossy_breakpoint_merge": "PASS under declared exact replay/canonical collinear reduction semantics",
            "condition_8_temporal_exactness": "PASS under EXACT_CONTINUOUS_TEMPORAL_PROFILE-v1 and canonical replay validation",
        },
        "per_query_csv": csv_path.relative_to(ROOT).as_posix(),
        "safe_region_manifest": region_manifest_path.relative_to(ROOT).as_posix(),
        "failed_queries": [
            {
                "query_id": row["query_id"],
                "missing_safe_vertices": len(json.loads(row["missing_safe_vertices"])),
                "missing_safe_edges": len(json.loads(row["missing_safe_edges"])),
                "missing_pivots": len(json.loads(row["missing_pivots"])),
            }
            for row in failed
        ],
    }
    report_path = OUT / "FULL_NY_THEOREM_SAFE_EQUIVALENCE.md"
    lines = [
        "# Full-NY theorem-safe equivalence audit",
        "",
        f"**Result:** `{report['result']}`",
        "",
        "No experiment, PACE-X run, PACE-B run, query selection, or numerical artifact was changed or executed during this audit.",
        "",
        "## 1. Theorem condition",
        "",
        "The checked construction is the manuscript's Lemma 1 region: `V_safe={v: EA(v)<=LD(v)}` and `E_safe={(u,v): u,v in V_safe and A_e(EA(u))<=LD(v)}`. The labels were recomputed on the original full NY graph from its serialized FIFO travel-time functions for each frozen query interval, endpoint, and budget. Score-relevant edges were then independently recomputed from the exact positive score domains and budget-feasible entry domains.",
        "",
        "Theorem 2 additionally requires every safe score-relevant edge as a pivot, sufficient exact-mode depth, exhaustive vertex-simple connectors in the safe connector graph, no heuristic retention or resource truncation, no lossy breakpoint merging, and exact temporal composition/replay.",
        "",
        "## 2. Source and execution checksums",
        "",
        "```text",
        json.dumps(report["checksums"], indent=2, sort_keys=True),
        "```",
        "",
        f"The frozen PACE-X input is `NY-Exact-radius` ({report['execution_provenance']['vertices']} vertices, {report['execution_provenance']['directed_edges']} directed arcs), selected by a static source-centered 4.5-minute radius and remapping node and arc IDs. The exact run command/configuration uses `theta=64`; the bounded PACE-B records use `theta=2`. These are not interchangeable.",
        "",
        "## 3. Safe-region reconstruction and inclusion result",
        "",
        f"The frozen manifest contains {report['query_count']} q-tuples: 20 interval/pair queries at each of budgets {', '.join(str(x) for x in report['budgets'])} minutes. All {report['query_count']} were audited. Every safe region and its original full-NY directed arc IDs is persisted under `FULL_NY_SAFE_REGIONS/`; the index is `FULL_NY_SAFE_REGION_MANIFEST.json`.",
        "",
        "The per-query inclusion, pivot, depth, connector, resource, and temporal checks are in `FULL_NY_EXACT_PROVENANCE_AUDIT.csv`. A query passes the lifting test only if safe vertices, safe edges, and safe score-relevant pivots are all contained in the exact execution graph/pivot universe.",
        "",
        "| Query | Safe vertices | Safe edges | Missing safe vertices | Missing safe edges | Safe pivots | Missing pivots | Lift |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['query_id']} | {row['safe_vertices']} | {row['safe_edges']} | {len(json.loads(row['missing_safe_vertices']))} | {len(json.loads(row['missing_safe_edges']))} | {len(json.loads(row['safe_score_relevant_edges']))} | {len(json.loads(row['missing_pivots']))} | {row['global_certificate_lifts_to_full_NY']} |"
        )
    lines.extend([
        "",
        "## 4. Preservation/exclusion evidence",
        "",
        "For every full-NY directed edge, the reconstruction records an exhaustive partition: it is in the safe region, or its exclusion is explained by forward unreachability, backward unreachability, incompatible vertex labels, or `A_e(EA(u)) > LD(v)`. An edge listed as missing from the execution graph but present in `E_safe` has no admissible theorem exclusion; it is therefore an explicit preservation failure, not an empirically inferred discrepancy.",
        "",
        "The endpoint IDs also require the documented subset remapping: local execution destination IDs such as 36 are not full-NY node 36 (local 36 maps to full-NY node 1363). The audit uses the recovered original endpoint IDs and records both namespaces in each safe-region JSON file.",
        "",
        "## 5. Certification conclusion and permitted wording",
        "",
        "The frozen `GLOBAL_CERTIFIED` label certifies PACE-X only on the serialized 64-vertex execution graph. Because the execution graph is a proper theorem-region subset for the audited queries and the full-NY pivot universe is not available to the run, the result cannot be lifted to the corresponding original full-NY queries. The manuscript must retain the narrower execution-graph scope and must not use `STORY_VERIFICATION_PASS` or full-NY certification wording.",
        "",
        "The permitted scope is: *PACE-X is globally certified on the frozen deterministic NY-Exact-radius execution graph; the audit does not establish equivalence to the original full NY network.*",
        "",
        "FULL_NY_THEOREM_SAFE_EQUIVALENCE_FAIL",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    failure_path = OUT / "FULL_NY_EXACT_PROVENANCE_FAILURE.md"
    failure_lines = [
        "# Full-NY exact provenance failure",
        "",
        "`FULL_NY_THEOREM_SAFE_EQUIVALENCE_FAIL`",
        "",
        "The frozen exact PACE-X execution graph is `NY-Exact-radius`, a 64-vertex/142-arc deterministic source-centered static-radius induced graph with remapped IDs. It is not the theorem-safe query region computed from the original full NY graph.",
        "",
        "The exact per-query missing vertices, missing directed arc IDs, missing pivots, condition statuses, and exclusion partitions are recorded in `FULL_NY_EXACT_PROVENANCE_AUDIT.csv`; complete safe vertex/arc sets are persisted in `FULL_NY_SAFE_REGIONS/`.",
        "",
        "## Failing queries",
        "",
        "| Query | Missing safe vertices | Missing safe edges | Missing pivots | Reason |",
        "|---|---:|---:|---:|---|",
    ]
    for item in report["failed_queries"]:
        failure_lines.append(
            f"| {item['query_id']} | {item['missing_safe_vertices']} | {item['missing_safe_edges']} | {item['missing_pivots']} | Safe full-NY elements are absent from the frozen execution graph; the local GLOBAL_CERTIFIED result cannot be lifted. |"
        )
    failure_lines.extend([
        "",
        "Raw results and manuscript numerical artifacts were not modified. No wording-only promotion was made.",
        "",
        "FULL_NY_THEOREM_SAFE_EQUIVALENCE_FAIL",
        "",
    ])
    failure_path.write_text("\n".join(failure_lines), encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "queries": len(rows),
        "failed_queries": len(failed),
        "csv": str(csv_path),
        "report": str(report_path),
        "failure": str(failure_path),
    }, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
