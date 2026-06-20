#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import re
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Iterable

import yaml


UUID32_RE = re.compile(r"^[0-9a-f]{32}$")


@dataclasses.dataclass(frozen=True)
class Card:
    uuid: str
    uuid8: str
    title: str
    status: str
    owner: str
    deps: tuple[str, ...]
    loc: str
    path: Path


@dataclasses.dataclass(frozen=True)
class Assignment:
    uuid: str
    member: str
    reason: str


@dataclasses.dataclass(frozen=True)
class Analysis:
    team: dict[str, str]
    cards: dict[str, Card]
    pending: dict[str, Card]
    pending_edges: list[tuple[str, str]]
    components: list[set[str]]
    roots: set[str]
    logic: str
    assignments: list[Assignment]
    left_pending: list[str]
    fairness: dict[str, object]
    mermaid: str


def extract_frontmatter(text: str) -> dict:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "---"), None)
    if start is None:
        return {}
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}
    raw = "\n".join(lines[start + 1:end])
    loaded = yaml.load(raw, Loader=yaml.BaseLoader) or {}
    return loaded if isinstance(loaded, dict) else {}


def normalize_deps(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items: Iterable[object] = [value]
    elif isinstance(value, list):
        items = value
    else:
        return ()
    deps: list[str] = []
    for item in items:
        dep = str(item or "").strip().lower()
        if dep and UUID32_RE.match(dep):
            deps.append(dep)
    return tuple(deps)


def read_team(dev: Path) -> dict[str, str]:
    team_path = dev / "TEAM.md"
    team: dict[str, str] = {}
    if not team_path.is_file():
        return team
    for line in team_path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1] in {"leader", "admin", "developer"}:
            team[cells[0]] = cells[1]
    return team


def load_card(task_dir: Path, owner_folder: str, loc: str) -> Card | None:
    task_path = task_dir / "TASK.md"
    if not task_path.is_file():
        return None
    fm = extract_frontmatter(task_path.read_text(encoding="utf-8"))
    uuid = str(fm.get("uuid") or "").strip().lower()
    if not UUID32_RE.match(uuid):
        return None
    return Card(
        uuid=uuid,
        uuid8=uuid[:8],
        title=str(fm.get("title") or task_dir.name),
        status=str(fm.get("status") or ""),
        owner=str(fm.get("owner") or owner_folder),
        deps=normalize_deps(fm.get("depends_on")),
        loc=loc,
        path=task_path,
    )


def iter_task_dirs(base: Path) -> Iterable[Path]:
    if not base.is_dir():
        return ()
    return (d for d in sorted(base.iterdir()) if d.is_dir() and not d.name.startswith("."))


def gather_cards(dev: Path, team: dict[str, str]) -> dict[str, Card]:
    cards: dict[str, Card] = {}
    for task_dir in iter_task_dirs(dev / "tasks" / "pool"):
        card = load_card(task_dir, "wait", "pool")
        if card:
            cards[card.uuid] = card
    for member in team:
        active_base = dev / "tasks" / member
        for task_dir in iter_task_dirs(active_base):
            if task_dir.name == "done":
                continue
            card = load_card(task_dir, member, "active")
            if card:
                cards[card.uuid] = card
        for task_dir in iter_task_dirs(active_base / "done"):
            card = load_card(task_dir, member, "done")
            if card:
                cards[card.uuid] = card
    return cards


def pending_cards(cards: dict[str, Card]) -> dict[str, Card]:
    return {
        uuid: card
        for uuid, card in cards.items()
        if card.loc == "pool" and card.owner == "wait" and card.status != "done"
    }


def build_pending_edges(pending: dict[str, Card]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    pending_ids = set(pending)
    for uuid, card in pending.items():
        for dep in card.deps:
            if dep in pending_ids:
                edges.append((dep, uuid))
    return sorted(edges)


def weak_components(pending: dict[str, Card], edges: list[tuple[str, str]]) -> list[set[str]]:
    adjacency: dict[str, set[str]] = {uuid: set() for uuid in pending}
    for src, dst in edges:
        adjacency[src].add(dst)
        adjacency[dst].add(src)
    seen: set[str] = set()
    components: list[set[str]] = []
    for uuid in sorted(pending):
        if uuid in seen:
            continue
        comp: set[str] = set()
        queue: deque[str] = deque([uuid])
        seen.add(uuid)
        while queue:
            cur = queue.popleft()
            comp.add(cur)
            for nxt in adjacency[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        components.append(comp)
    components.sort(key=lambda comp: (min(pending[u].uuid8 for u in comp), len(comp)))
    return components


def pending_roots(pending: dict[str, Card], edges: list[tuple[str, str]]) -> set[str]:
    incoming = Counter(dst for _, dst in edges)
    return {uuid for uuid in pending if incoming[uuid] == 0}


def upstream_owner_counts(uuids: Iterable[str], cards: dict[str, Card], pending: dict[str, Card]) -> Counter[str]:
    owners: Counter[str] = Counter()
    pending_ids = set(pending)
    for uuid in uuids:
        for dep in pending[uuid].deps:
            if dep in pending_ids:
                continue
            dep_card = cards.get(dep)
            if dep_card and dep_card.owner != "wait":
                owners[dep_card.owner] += 1
    return owners


def completed_counts(cards: dict[str, Card], team: dict[str, str]) -> dict[str, int]:
    counts = {member: 0 for member in team}
    for card in cards.values():
        if card.loc == "done" and card.owner in counts:
            counts[card.owner] += 1
    return counts


def active_counts(cards: dict[str, Card], team: dict[str, str]) -> dict[str, int]:
    counts = {member: 0 for member in team}
    for card in cards.values():
        if card.loc == "active" and card.owner in counts:
            counts[card.owner] += 1
    return counts


def inverse_completion_targets(total: int, done: dict[str, int]) -> dict[str, float]:
    if not done:
        return {}
    max_done = max(done.values(), default=0)
    weights = {member: max_done - count + 1 for member, count in done.items()}
    weight_sum = sum(weights.values()) or len(done)
    return {member: total * weight / weight_sum for member, weight in weights.items()}


def choose_member(
    candidates: Iterable[str],
    assigned_counts: dict[str, int],
    targets: dict[str, float],
    preference: Counter[str] | None = None,
) -> str:
    preference = preference or Counter()
    members = list(candidates)

    def score(member: str) -> tuple[float, int, int, str]:
        target = targets.get(member, 0.0)
        projected = assigned_counts[member] + 1
        deficit = projected - target
        return (deficit, assigned_counts[member], -preference[member], member)

    return min(members, key=score)


def fairness_summary(assigned_counts: dict[str, int], total: int, threshold_ratio: float) -> dict[str, object]:
    if not assigned_counts:
        return {"ok": True, "target": 0.0, "allowed_deviation": 0.0, "counts": {}}
    target = total / len(assigned_counts)
    allowed = target * threshold_ratio
    deviations = {member: abs(count - target) for member, count in assigned_counts.items()}
    return {
        "ok": all(dev <= allowed for dev in deviations.values()),
        "target": target,
        "allowed_deviation": allowed,
        "counts": dict(assigned_counts),
        "deviations": deviations,
    }


def assign_logic_a(
    components: list[set[str]],
    roots: set[str],
    cards: dict[str, Card],
    pending: dict[str, Card],
    team: dict[str, str],
    threshold_ratio: float,
) -> tuple[list[Assignment], dict[str, object]]:
    members = sorted(team)
    assigned_counts = {member: 0 for member in members}
    total = len(pending)
    targets = {member: total / len(members) for member in members} if members else {}
    assignments: list[Assignment] = []
    ordered = sorted(components, key=lambda comp: (-len(comp), min(pending[u].uuid8 for u in comp)))
    for comp in ordered:
        comp_roots = sorted(uuid for uuid in comp if uuid in roots)
        preference = upstream_owner_counts(comp_roots, cards, pending)
        preferred = [member for member, _ in preference.most_common() if member in team]
        candidates = preferred or members
        member = choose_member(candidates, assigned_counts, targets, preference)
        for uuid in sorted(comp, key=lambda item: pending[item].uuid8):
            assignments.append(Assignment(uuid, member, "component"))
        assigned_counts[member] += len(comp)
    fairness = fairness_summary(assigned_counts, total, threshold_ratio)
    fairness["mode"] = "A"
    return assignments, fairness


def assign_logic_b(
    roots: set[str],
    cards: dict[str, Card],
    pending: dict[str, Card],
    team: dict[str, str],
) -> tuple[list[Assignment], dict[str, object]]:
    members = sorted(team)
    assignable = sorted(roots, key=lambda uuid: pending[uuid].uuid8)
    done = completed_counts(cards, team)
    targets = inverse_completion_targets(len(assignable), done)
    assigned_counts = {member: 0 for member in members}
    assignments: list[Assignment] = []
    for uuid in assignable:
        preference = upstream_owner_counts([uuid], cards, pending)
        preferred = [member for member, _ in preference.most_common() if member in team]
        candidates = preferred or members
        member = choose_member(candidates, assigned_counts, targets, preference)
        reason = "upstream-owner" if preferred else "completion-balance"
        assignments.append(Assignment(uuid, member, reason))
        assigned_counts[member] += 1
    fairness = {
        "mode": "B",
        "targets": targets,
        "counts": assigned_counts,
        "completed_counts": done,
    }
    return assignments, fairness


def mermaid_graph(pending: dict[str, Card], edges: list[tuple[str, str]]) -> str:
    lines = ["flowchart TD"]
    if not pending:
        lines.append('  empty["no pending tasks"]')
        return "\n".join(lines)
    for uuid in sorted(pending, key=lambda item: pending[item].uuid8):
        card = pending[uuid]
        label = f"{card.uuid8} {card.title}".replace('"', "'")
        lines.append(f'  n{card.uuid8}["{label}"]')
    for src, dst in edges:
        lines.append(f"  n{pending[src].uuid8} --> n{pending[dst].uuid8}")
    return "\n".join(lines)


def analyze(dev: Path, threshold_ratio: float = 0.20) -> Analysis:
    team = read_team(dev)
    cards = gather_cards(dev, team)
    pending = pending_cards(cards)
    edges = build_pending_edges(pending)
    components = weak_components(pending, edges)
    roots = pending_roots(pending, edges)
    if not team or not pending:
        assignments: list[Assignment] = []
        fairness: dict[str, object] = {"mode": "none", "ok": True, "reason": "no team or no pending tasks"}
        logic = "none"
    elif len(components) > len(team):
        assignments, fairness = assign_logic_a(components, roots, cards, pending, team, threshold_ratio)
        logic = "A"
        if not fairness.get("ok"):
            assignments, fairness = assign_logic_b(roots, cards, pending, team)
            fairness["fallback_from"] = "A"
            logic = "B"
    else:
        assignments, fairness = assign_logic_b(roots, cards, pending, team)
        logic = "B"
    assigned_ids = {assignment.uuid for assignment in assignments}
    left_pending = sorted((set(pending) - assigned_ids), key=lambda uuid: pending[uuid].uuid8)
    return Analysis(
        team=team,
        cards=cards,
        pending=pending,
        pending_edges=edges,
        components=components,
        roots=roots,
        logic=logic,
        assignments=assignments,
        left_pending=left_pending,
        fairness=fairness,
        mermaid=mermaid_graph(pending, edges),
    )


def fmt_float(value: object) -> str:
    return f"{float(value):.2f}"


def task_link(card: Card) -> str:
    if card.loc == "pool":
        target = f"pool/{card.uuid8}/TASK.md"
    elif card.loc == "done":
        target = f"{card.owner}/done/{card.uuid8}/TASK.md"
    else:
        target = f"{card.owner}/{card.uuid8}/TASK.md"
    return f"[{card.uuid8}]({target})"


def render_board(analysis: Analysis) -> str:
    lines = [
        "# ASSIGNMENT BOARD · task allocation recommendation",
        "",
        "> Generated from task front matter. This is a recommendation; move cards only through leader/admin assignment flow.",
        "",
        "## Dependency Graph",
        "",
        "```mermaid",
        analysis.mermaid,
        "```",
        "",
        "## Summary",
        "",
        f"- Team members: {len(analysis.team)}",
        f"- Pending tasks: {len(analysis.pending)}",
        f"- Connected components: {len(analysis.components)}",
        f"- Logic used: {analysis.logic}",
    ]
    if analysis.fairness.get("fallback_from"):
        lines.append(f"- Fallback: {analysis.fairness['fallback_from']} -> {analysis.logic}")
    if analysis.fairness.get("target") is not None:
        lines.append(f"- Fairness target: {fmt_float(analysis.fairness['target'])}")
        lines.append(f"- Allowed deviation: {fmt_float(analysis.fairness['allowed_deviation'])}")
    lines += [
        "",
        "## Suggested Assignments",
        "",
        "<!-- 确定最终分配后删除⬆️，并取消注释⬇️；复制下方表格并将 suggested_owner 字段换成 final_owner -->",
        "<!-- ## Final Assignments -->",
        "",
        "| task | title | suggested_owner | reason |",
        "|---|---|---|---|",
    ]
    if analysis.assignments:
        for assignment in sorted(analysis.assignments, key=lambda item: analysis.pending[item.uuid].uuid8):
            card = analysis.pending[assignment.uuid]
            lines.append(f"| {task_link(card)} | {card.title} | {assignment.member} | {assignment.reason} |")
    else:
        lines.append("| _none_ | | | |")
    lines += [
        "",
        "## Left In Pool",
        "",
        "| task | title | reason |",
        "|---|---|---|",
    ]
    if analysis.left_pending:
        for uuid in analysis.left_pending:
            card = analysis.pending[uuid]
            reason = "blocked by pending dependency" if uuid not in analysis.roots else "not selected"
            lines.append(f"| {task_link(card)} | {card.title} | {reason} |")
    else:
        lines.append("| _none_ | | |")
    lines += [
        "",
        "## Member Counts",
        "",
        "| member | role | suggested_count | completed_count | active_count |",
        "|---|---|---:|---:|---:|",
    ]
    suggested = Counter(assignment.member for assignment in analysis.assignments)
    done = completed_counts(analysis.cards, analysis.team)
    active = active_counts(analysis.cards, analysis.team)
    for member in sorted(analysis.team):
        lines.append(
            f"| {member} | {analysis.team[member]} | {suggested[member]} | {done[member]} | {active[member]} |"
        )
    return "\n".join(lines) + "\n"


def write_board(dev: Path, analysis: Analysis) -> Path:
    path = dev / "tasks" / "ASSIGNMENT_BOARD.md"
    path.write_text(render_board(analysis), encoding="utf-8")
    return path


def default_dev_path() -> Path:
    return Path(__file__).resolve().parents[3]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build task dependency graph and assignment board.")
    parser.add_argument("--dev", type=Path, default=default_dev_path(), help="Path to dev directory.")
    parser.add_argument("--write", action="store_true", help="Write dev/tasks/ASSIGNMENT_BOARD.md.")
    parser.add_argument("--threshold", type=float, default=0.20, help="Fairness threshold ratio for logic A.")
    args = parser.parse_args(argv)
    analysis = analyze(args.dev, args.threshold)
    board = render_board(analysis)
    if args.write:
        path = write_board(args.dev, analysis)
        print(f"wrote {path}")
    else:
        print(board)
    return 0


if __name__ == "__main__":
    sys.exit(main())
