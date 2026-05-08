import datetime as dt
import html
import json
import math
import os
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
            "User-Agent": "custom-pacman-maze",
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


def read_days(calendar: dict) -> list[dict]:
    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append(
                {
                    "date": day["date"],
                    "count": int(day["contributionCount"]),
                    "weekday": int(day["weekday"]),
                }
            )

    return days


def point_segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx = bx - ax
    dy = by - ay

    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    cx = ax + t * dx
    cy = ay + t * dy

    return math.hypot(px - cx, py - cy)


def path_d(points: list[tuple[float, float]]) -> str:
    first = points[0]
    rest = points[1:]

    return "M " + f"{first[0]} {first[1]} " + " ".join(f"L {x} {y}" for x, y in rest)


def path_lengths(points: list[tuple[float, float]]) -> tuple[list[float], float]:
    cumulative = [0.0]
    total = 0.0

    for index in range(len(points) - 1):
        ax, ay = points[index]
        bx, by = points[index + 1]

        total += math.hypot(bx - ax, by - ay)
        cumulative.append(total)

    return cumulative, total


def nearest_path_time(px: float, py: float, points: list[tuple[float, float]]) -> float:
    cumulative, total = path_lengths(points)

    if total == 0:
        return 0.0

    best_distance = float("inf")
    best_length = 0.0

    for index in range(len(points) - 1):
        ax, ay = points[index]
        bx, by = points[index + 1]

        dx = bx - ax
        dy = by - ay

        if dx == 0 and dy == 0:
            continue

        t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))

        cx = ax + t * dx
        cy = ay + t * dy

        distance = math.hypot(px - cx, py - cy)
        length_here = cumulative[index] + math.hypot(cx - ax, cy - ay)

        if distance < best_distance:
            best_distance = distance
            best_length = length_here

    return best_length / total


def normalized(value: float) -> str:
    value = max(0.0, min(1.0, value))

    if abs(value) < 0.000001:
        return "0"

    if abs(value - 1) < 0.000001:
        return "1"

    return f"{value:.6f}".rstrip("0").rstrip(".")


def disappear_animation(t: float) -> tuple[str, str]:
    before = max(0.0, t - 0.01)
    after = min(1.0, t + 0.01)

    key_times = ";".join(
        [
            "0",
            normalized(before),
            normalized(t),
            normalized(after),
            "1",
        ]
    )

    return key_times, "1;1;0;0;1"


def build_svg(calendar: dict, dark: bool) -> str:
    days = read_days(calendar)
    active_days = [day for day in days if day["count"] > 0]

    total = int(calendar["totalContributions"])
    active_count = len(active_days)

    width = 1000
    height = 720
    duration = 34

    bg = "#02030a"
    wall_border = "#07051b"
    wall = "#352c98"
    wall_light = "#5148d7"
    pellet = "#ff7b22"
    text = "#f8fafc"
    muted = "#94a3b8"
    pacman = "#ffc31a"
    eye = "#ffffff"
    pupil = "#111827"

    ghost_red = "#ff4b36"
    ghost_green = "#57c785"
    ghost_orange = "#ff9f2f"
    ghost_pink = "#ff72b6"
    cherry = "#ff4b2b"
    cherry_leaf = "#65d46e"
    pill = "#ffffff"
    pill_red = "#ff563d"

    title = f"{html.escape(USERNAME)} no mapa dos commits"

    pacman_path_points = [
        (170, 245), (250, 245), (250, 185), (470, 185), (470, 245),
        (610, 245), (610, 185), (820, 185), (820, 285), (720, 285),
        (720, 395), (850, 395), (850, 525), (710, 525), (710, 610),
        (500, 610), (500, 540), (350, 540), (350, 620), (130, 620),
        (130, 530), (260, 530), (260, 420), (145, 420), (145, 330),
        (250, 330), (250, 245),
    ]

    ghost_path_one = [
        (610, 310), (700, 310), (700, 420), (820, 420), (820, 520),
        (700, 520), (700, 610), (520, 610), (520, 510), (610, 510),
        (610, 310),
    ]

    ghost_path_two = [
        (250, 540), (250, 430), (145, 430), (145, 300), (250, 300),
        (250, 185), (420, 185), (420, 300), (350, 300), (350, 540),
        (250, 540),
    ]

    ghost_path_three = [
        (790, 565), (880, 565), (880, 470), (790, 470), (790, 320),
        (880, 320), (880, 185), (720, 185), (720, 320), (790, 320),
        (790, 565),
    ]

    wall_segments = [
        (52, 136, 948, 136), (948, 136, 948, 636), (948, 636, 52, 636), (52, 636, 52, 136),
        (90, 165, 210, 165), (210, 165, 210, 245),
        (285, 165, 470, 165), (540, 165, 760, 165),
        (815, 165, 910, 165), (815, 165, 815, 250), (910, 165, 910, 285),
        (90, 300, 175, 300), (215, 300, 215, 440), (90, 440, 215, 440),
        (285, 300, 285, 520), (130, 520, 285, 520),
        (360, 300, 360, 210), (360, 210, 480, 210),
        (445, 300, 445, 250), (445, 250, 555, 250), (555, 250, 555, 300),
        (620, 300, 620, 210), (620, 210, 745, 210),
        (700, 300, 700, 440), (700, 440, 875, 440),
        (785, 300, 785, 520), (785, 520, 920, 520),
        (360, 425, 640, 425),
        (400, 515, 600, 515),
        (400, 515, 400, 590), (400, 590, 600, 590), (600, 590, 600, 515),
        (90, 555, 260, 555), (260, 555, 260, 636),
        (720, 555, 885, 555), (720, 555, 720, 636),
        (120, 600, 210, 600), (790, 600, 910, 600),
    ]

    pellets = []

    for y in range(180, 610, 40):
        for x in range(92, 925, 40):
            distance_to_wall = min(
                point_segment_distance(x, y, ax, ay, bx, by)
                for ax, ay, bx, by in wall_segments
            )

            if distance_to_wall >= 23:
                pellets.append((x, y))

    special_items = [
        ("cherry", 300, 185),
        ("pill", 700, 185),
        ("cherry", 650, 455),
        ("pill", 155, 560),
        ("cherry", 390, 620),
        ("pill", 860, 500),
    ]

    svg = []

    svg.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Pacman animado com commits de {html.escape(USERNAME)}">'
    )

    svg.append("<defs>")
    svg.append(
        '<filter id="shadow">'
        '<feDropShadow dx="0" dy="4" stdDeviation="3" flood-color="#000000" flood-opacity="0.5"/>'
        "</filter>"
    )
    svg.append("</defs>")

    svg.append(f'<rect width="{width}" height="{height}" fill="{bg}"/>')

    svg.append('<g id="header" filter="url(#shadow)">')
    svg.append('<g transform="translate(150 70)">')
    svg.append(f'<circle cx="0" cy="0" r="38" fill="{pacman}"/>')
    svg.append(f'<polygon points="0,0 43,-22 43,22" fill="{bg}"/>')
    svg.append(f'<circle cx="10" cy="-20" r="7" fill="{eye}"/>')
    svg.append(f'<circle cx="13" cy="-20" r="3" fill="{pupil}"/>')
    svg.append("</g>")

    header_ghosts = [
        (270, ghost_red), (380, ghost_green), (490, ghost_orange), (600, ghost_pink)
    ]

    for gx, color in header_ghosts:
        svg.append(f'<g transform="translate({gx} 78)">')
        svg.append(
            f'<path d="M -24 25 L -24 -8 C -24 -30 -12 -42 0 -42 C 12 -42 24 -30 24 -8 L 24 25 '
            f'L 15 16 L 7 25 L 0 16 L -7 25 L -15 16 Z" fill="{color}"/>'
        )
        svg.append(f'<circle cx="-8" cy="-20" r="6" fill="{eye}"/>')
        svg.append(f'<circle cx="8" cy="-20" r="6" fill="{eye}"/>')
        svg.append(f'<circle cx="-10" cy="-21" r="3" fill="{pupil}"/>')
        svg.append(f'<circle cx="6" cy="-21" r="3" fill="{pupil}"/>')
        svg.append("</g>")

    svg.append('<g transform="translate(760 68) rotate(38)">')
    svg.append(f'<rect x="-8" y="-28" width="16" height="56" rx="8" fill="{pill}"/>')
    svg.append(f'<rect x="-8" y="0" width="16" height="28" rx="7" fill="{pill_red}"/>')
    svg.append("</g>")

    svg.append('<g transform="translate(865 70)">')
    svg.append(f'<circle cx="-10" cy="14" r="13" fill="{cherry}"/>')
    svg.append(f'<circle cx="14" cy="10" r="13" fill="{cherry}"/>')
    svg.append(f'<path d="M -6 2 C 8 -24 20 -26 24 -32" fill="none" stroke="{cherry_leaf}" stroke-width="4"/>')
    svg.append(f'<path d="M 24 -32 C 10 -36 4 -31 -2 -23" fill="{cherry_leaf}"/>')
    svg.append("</g>")

    svg.append("</g>")

    svg.append(
        f'<text x="{width / 2}" y="122" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="19" font-weight="800" fill="{text}">'
        f'{title} • SCORE {total}'
        f"</text>"
    )

    wall_path = path_d([(52, 136), (948, 136), (948, 636), (52, 636), (52, 136)])

    all_wall_paths = [
        wall_path,
        path_d([(90, 165), (210, 165), (210, 245)]),
        path_d([(285, 165), (470, 165)]),
        path_d([(540, 165), (760, 165)]),
        path_d([(815, 165), (910, 165), (910, 285), (835, 285)]),
        path_d([(90, 300), (175, 300)]),
        path_d([(215, 300), (215, 440), (90, 440)]),
        path_d([(285, 300), (285, 520), (130, 520)]),
        path_d([(360, 300), (360, 210), (480, 210)]),
        path_d([(445, 300), (445, 250), (555, 250), (555, 300)]),
        path_d([(620, 300), (620, 210), (745, 210)]),
        path_d([(700, 300), (700, 440), (875, 440)]),
        path_d([(785, 300), (785, 520), (920, 520)]),
        path_d([(360, 425), (640, 425)]),
        path_d([(400, 515), (600, 515)]),
        path_d([(400, 515), (400, 590), (600, 590), (600, 515)]),
        path_d([(90, 555), (260, 555), (260, 636)]),
        path_d([(720, 555), (885, 555)]),
        path_d([(720, 555), (720, 636)]),
        path_d([(120, 600), (210, 600)]),
        path_d([(790, 600), (910, 600)]),
    ]

    svg.append('<g id="maze">')

    for item in all_wall_paths:
        svg.append(
            f'<path d="{item}" fill="none" stroke="{wall_border}" stroke-width="34" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    for item in all_wall_paths:
        svg.append(
            f'<path d="{item}" fill="none" stroke="{wall}" stroke-width="24" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )
        svg.append(
            f'<path d="{item}" fill="none" stroke="{wall_light}" stroke-width="3" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>'
        )

    svg.append("</g>")

    main_path = path_d(pacman_path_points)

    svg.append('<g id="pellets">')

    for x, y in pellets:
        t = nearest_path_time(x, y, pacman_path_points)
        key_times, values = disappear_animation(t)

        svg.append(
            f'<circle cx="{x}" cy="{y}" r="4.2" fill="{pellet}">'
            f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
            f'dur="{duration}s" repeatCount="indefinite"/>'
            f"</circle>"
        )

    svg.append("</g>")

    svg.append('<g id="bonus">')

    for kind, x, y in special_items:
        t = nearest_path_time(x, y, pacman_path_points)
        key_times, values = disappear_animation(t)

        if kind == "cherry":
            svg.append(f'<g transform="translate({x} {y})">')
            svg.append(
                f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
                f'dur="{duration}s" repeatCount="indefinite"/>'
            )
            svg.append(f'<circle cx="-7" cy="8" r="8" fill="{cherry}"/>')
            svg.append(f'<circle cx="8" cy="6" r="8" fill="{cherry}"/>')
            svg.append(f'<path d="M -4 0 C 4 -18 12 -19 18 -26" fill="none" stroke="{cherry_leaf}" stroke-width="3"/>')
            svg.append(f'<path d="M 18 -26 C 8 -29 2 -24 -2 -17" fill="{cherry_leaf}"/>')
            svg.append("</g>")
        else:
            svg.append(f'<g transform="translate({x} {y}) rotate(38)">')
            svg.append(
                f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
                f'dur="{duration}s" repeatCount="indefinite"/>'
            )
            svg.append(f'<rect x="-7" y="-22" width="14" height="44" rx="7" fill="{pill}"/>')
            svg.append(f'<rect x="-7" y="0" width="14" height="22" rx="6" fill="{pill_red}"/>')
            svg.append("</g>")

    svg.append("</g>")

    svg.append('<g id="characters" filter="url(#shadow)">')

    svg.append('<g id="pacman">')
    svg.append(
        f'<animateMotion dur="{duration}s" repeatCount="indefinite" rotate="auto" path="{main_path}"/>'
    )
    svg.append(f'<circle cx="0" cy="0" r="24" fill="{pacman}"/>')
    svg.append(f'<polygon points="0,0 28,-15 28,15" fill="{bg}">')
    svg.append(
        '<animate attributeName="points" '
        'values="0,0 29,-17 29,17;0,0 30,-3 30,3;0,0 29,-17 29,17" '
        'dur="0.28s" repeatCount="indefinite"/>'
    )
    svg.append("</polygon>")
    svg.append(f'<circle cx="5" cy="-13" r="5" fill="{eye}"/>')
    svg.append(f'<circle cx="7" cy="-13" r="2.2" fill="{pupil}"/>')
    svg.append("</g>")

    def ghost(name: str, color: str, points: list[tuple[float, float]], delay: str) -> None:
        svg.append(f'<g id="{name}">')
        svg.append(
            f'<animateMotion dur="{duration}s" begin="{delay}" repeatCount="indefinite" '
            f'rotate="auto" path="{path_d(points)}"/>'
        )
        svg.append(
            f'<path d="M -16 16 L -16 -5 C -16 -20 -8 -28 0 -28 C 8 -28 16 -20 16 -5 L 16 16 '
            f'L 10 10 L 5 16 L 0 10 L -5 16 L -10 10 Z" fill="{color}"/>'
        )
        svg.append(f'<circle cx="-6" cy="-11" r="4.5" fill="{eye}"/>')
        svg.append(f'<circle cx="6" cy="-11" r="4.5" fill="{eye}"/>')
        svg.append(f'<circle cx="-7" cy="-12" r="2" fill="{pupil}"/>')
        svg.append(f'<circle cx="5" cy="-12" r="2" fill="{pupil}"/>')
        svg.append("</g>")

    ghost("redGhost", ghost_red, ghost_path_one, "0s")
    ghost("orangeGhost", ghost_orange, ghost_path_two, "1.6s")
    ghost("pinkGhost", ghost_pink, ghost_path_three, "3.2s")
    ghost("greenGhost", ghost_green, list(reversed(ghost_path_three)), "5s")

    svg.append("</g>")

    svg.append(
        f'<text x="{width / 2}" y="685" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="15" fill="{muted}">'
        f'{total} commits nos últimos meses • {active_count} dias com contribuição'
        f"</text>"
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

    print("Pacman em labirinto gerado com sucesso.")
    print(f"Usuário: {USERNAME}")
    print(f"Total de contribuições: {calendar['totalContributions']}")


if __name__ == "__main__":
    main()