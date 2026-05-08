import datetime as dt
import html
import json
import os
import random
import urllib.request
from pathlib import Path


USERNAME = os.getenv("GH_USERNAME", "sayydaviid")
TOKEN = os.getenv("GITHUB_TOKEN")

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_contributions(username: str, token: str) -> dict:
    today = dt.datetime.now(dt.timezone.utc)
    start = today - dt.timedelta(days=370)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
                color
              }
            }
          }
        }
      }
    }
    """

    payload = {
        "query": query,
        "variables": {
            "login": username,
            "from": start.isoformat(),
            "to": today.isoformat(),
        },
    }

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "custom-pacman-contribution-graph",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2, ensure_ascii=False))

    user = data.get("data", {}).get("user")

    if not user:
        raise RuntimeError(f"Usuário não encontrado: {username}")

    return user["contributionsCollection"]["contributionCalendar"]


def contribution_level(count: int) -> int:
    if count <= 0:
        return 0

    if count == 1:
        return 1

    if count <= 3:
        return 2

    if count <= 6:
        return 3

    return 4


def normalize_time(value: float) -> str:
    value = max(0.0, min(1.0, value))

    if value == 0:
        return "0"

    if value == 1:
        return "1"

    return f"{value:.6f}".rstrip("0").rstrip(".")


def pellet_animation(index: int, total_positions: int) -> tuple[str, str]:
    eat_time = index / max(1, total_positions - 1)
    before = max(0.0, eat_time - 0.012)
    after = min(1.0, eat_time + 0.012)

    key_times = ";".join(
        [
            "0",
            normalize_time(before),
            normalize_time(eat_time),
            normalize_time(after),
            "1",
        ]
    )

    values = "1;1;0;0;1"

    return key_times, values


def build_grid(calendar: dict) -> tuple[list[dict], list[dict]]:
    cells = []
    weeks = calendar["weeks"]

    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            count = int(day["contributionCount"])
            weekday = int(day["weekday"])

            cells.append(
                {
                    "week": week_index,
                    "weekday": weekday,
                    "count": count,
                    "date": day["date"],
                    "level": contribution_level(count),
                }
            )

    path_cells = []

    for week_index, week in enumerate(weeks):
        days = week["contributionDays"]

        ordered_days = sorted(days, key=lambda item: int(item["weekday"]))

        if week_index % 2 == 1:
            ordered_days = list(reversed(ordered_days))

        for day in ordered_days:
            count = int(day["contributionCount"])
            weekday = int(day["weekday"])

            path_cells.append(
                {
                    "week": week_index,
                    "weekday": weekday,
                    "count": count,
                    "date": day["date"],
                    "level": contribution_level(count),
                }
            )

    return cells, path_cells


def build_svg(calendar: dict, dark: bool) -> str:
    cells, path_cells = build_grid(calendar)

    total_contributions = calendar["totalContributions"]
    weeks_count = len(calendar["weeks"])

    width = 950
    height = 240

    board_x = 62
    board_y = 78
    cell = 11
    gap = 5
    step = cell + gap

    duration = 26

    if dark:
        bg = "#0d1117"
        panel = "#161b22"
        text = "#f0f6fc"
        muted = "#8b949e"
        empty = "#30363d"
        level_colors = {
            0: "#30363d",
            1: "#0e4429",
            2: "#006d32",
            3: "#26a641",
            4: "#39d353",
        }
        pacman = "#f2cc60"
        mouth = panel
        ghost_one = "#ff7b72"
        ghost_two = "#79c0ff"
        ghost_three = "#d2a8ff"
        pellet = "#f2cc60"
    else:
        bg = "#ffffff"
        panel = "#f6f8fa"
        text = "#24292f"
        muted = "#57606a"
        empty = "#ebedf0"
        level_colors = {
            0: "#ebedf0",
            1: "#9be9a8",
            2: "#40c463",
            3: "#30a14e",
            4: "#216e39",
        }
        pacman = "#bf8700"
        mouth = panel
        ghost_one = "#cf222e"
        ghost_two = "#0969da"
        ghost_three = "#8250df"
        pellet = "#bf8700"

    def cx(item: dict) -> float:
        return board_x + item["week"] * step + cell / 2

    def cy(item: dict) -> float:
        return board_y + item["weekday"] * step + cell / 2

    path_points = []

    for item in path_cells:
        path_points.append((cx(item), cy(item)))

    if not path_points:
        path_points.append((board_x, board_y))

    path_d = "M " + " L ".join(f"{round(x, 2)} {round(y, 2)}" for x, y in path_points)

    random.seed(f"{USERNAME}-{total_contributions}")

    svg = []

    svg.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img">'
    )

    svg.append("<defs>")
    svg.append(
        '<filter id="shadow">'
        '<feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000000" flood-opacity="0.35"/>'
        "</filter>"
    )
    svg.append(
        f'<linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{ghost_two}"/>'
        f'<stop offset="50%" stop-color="{pacman}"/>'
        f'<stop offset="100%" stop-color="{ghost_one}"/>'
        f"</linearGradient>"
    )
    svg.append("</defs>")

    svg.append(f'<rect width="{width}" height="{height}" rx="20" fill="{bg}"/>')
    svg.append(f'<rect x="18" y="18" width="{width - 36}" height="{height - 36}" rx="18" fill="{panel}"/>')

    svg.append(
        f'<text x="{width / 2}" y="50" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="800" fill="url(#titleGradient)">'
        f'{html.escape(USERNAME)} no mapa dos commits'
        f"</text>"
    )

    svg.append(f'<g id="grid">')

    for item in cells:
        x = board_x + item["week"] * step
        y = board_y + item["weekday"] * step
        level = item["level"]
        fill = level_colors[level]
        opacity = "1" if level > 0 else "0.65"

        svg.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}" opacity="{opacity}"/>'
        )

    svg.append("</g>")

    svg.append(f'<g id="pellets">')

    total_positions = len(path_cells)

    for index, item in enumerate(path_cells):
        if item["count"] <= 0:
            continue

        key_times, values = pellet_animation(index, total_positions)

        radius = 2.2

        if item["count"] >= 5:
            radius = 2.8

        if item["count"] >= 10:
            radius = 3.4

        svg.append(
            f'<circle cx="{cx(item)}" cy="{cy(item)}" r="{radius}" fill="{pellet}" opacity="1">'
            f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
            f'dur="{duration}s" repeatCount="indefinite"/>'
            f"</circle>"
        )

    svg.append("</g>")

    svg.append(f'<path d="{path_d}" fill="none" stroke="none" id="pacmanPath"/>')

    svg.append('<g id="pacman" filter="url(#shadow)">')
    svg.append(
        f'<animateMotion dur="{duration}s" repeatCount="indefinite" rotate="auto" path="{path_d}"/>'
    )
    svg.append(f'<circle cx="0" cy="0" r="10" fill="{pacman}"/>')
    svg.append(f'<polygon points="0,0 13,-8 13,8" fill="{mouth}">')
    svg.append(
        '<animate attributeName="points" '
        'values="0,0 13,-8 13,8;0,0 13,-1 13,1;0,0 13,-8 13,8" '
        'dur="0.32s" repeatCount="indefinite"/>'
    )
    svg.append("</polygon>")
    svg.append("</g>")

    def ghost(color: str, delay: float, scale: float) -> str:
        return (
            f'<g filter="url(#shadow)" transform="scale({scale})">'
            f'<animateMotion dur="{duration}s" begin="{delay}s" repeatCount="indefinite" rotate="auto" path="{path_d}"/>'
            f'<path d="M -9 8 L -9 -1 C -9 -8 -5 -12 0 -12 C 5 -12 9 -8 9 -1 L 9 8 '
            f'L 5 5 L 2 8 L 0 5 L -2 8 L -5 5 Z" fill="{color}"/>'
            f'<circle cx="-4" cy="-3" r="2.4" fill="#ffffff"/>'
            f'<circle cx="4" cy="-3" r="2.4" fill="#ffffff"/>'
            f'<circle cx="-3.2" cy="-3" r="1.1" fill="#111827"/>'
            f'<circle cx="4.8" cy="-3" r="1.1" fill="#111827"/>'
            f"</g>"
        )

    svg.append('<g id="ghosts">')
    svg.append(ghost(ghost_one, 3.4, 1))
    svg.append(ghost(ghost_two, 5.8, 0.92))
    svg.append(ghost(ghost_three, 8.2, 0.86))
    svg.append("</g>")

    svg.append(
        f'<text x="{width / 2}" y="198" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{muted}">'
        f'{total_contributions} contribuições nos últimos meses'
        f"</text>"
    )

    legend_x = 70
    legend_y = 205

    svg.append(
        f'<text x="{legend_x - 8}" y="{legend_y + 9}" text-anchor="end" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{muted}">menos</text>'
    )

    for level in range(5):
        svg.append(
            f'<rect x="{legend_x + level * 16}" y="{legend_y}" width="11" height="11" '
            f'rx="3" fill="{level_colors[level]}"/>'
        )

    svg.append(
        f'<text x="{legend_x + 88}" y="{legend_y + 9}" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="10" fill="{muted}">mais</text>'
    )

    svg.append("</svg>")

    return "\n".join(svg)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN não encontrado.")

    calendar = fetch_contributions(USERNAME, TOKEN)

    light_svg = build_svg(calendar, dark=False)
    dark_svg = build_svg(calendar, dark=True)

    (OUTPUT_DIR / "pacman_contribution_graph.svg").write_text(light_svg, encoding="utf-8")
    (OUTPUT_DIR / "pacman_contribution_graph_dark.svg").write_text(dark_svg, encoding="utf-8")

    print("Pacman gerado com sucesso.")
    print(f"Usuário: {USERNAME}")
    print(f"Contribuições: {calendar['totalContributions']}")


if __name__ == "__main__":
    main()