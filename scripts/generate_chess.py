import datetime as dt
import html
import json
import math
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
            "User-Agent": "chess-contribution-svg",
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


def piece_for_count(count: int, is_white: bool) -> str:
    white = {
        "pawn": "♙",
        "knight": "♘",
        "bishop": "♗",
        "rook": "♖",
        "queen": "♕",
        "king": "♔",
    }

    black = {
        "pawn": "♟",
        "knight": "♞",
        "bishop": "♝",
        "rook": "♜",
        "queen": "♛",
        "king": "♚",
    }

    pieces = white if is_white else black

    if count >= 18:
        return pieces["king"]
    if count >= 12:
        return pieces["queen"]
    if count >= 8:
        return pieces["rook"]
    if count >= 5:
        return pieces["bishop"]
    if count >= 3:
        return pieces["knight"]

    return pieces["pawn"]


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


def build_svg(calendar: dict, dark: bool) -> str:
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    width = 980
    height = 260

    board_x = 70
    board_y = 74
    cell = 13
    gap = 4
    step = cell + gap

    rows = 7
    cols = len(weeks)

    if dark:
        bg = "#0d1117"
        panel = "#161b22"
        text = "#f0f6fc"
        muted = "#8b949e"
        square_light = "#d0d7de"
        square_dark = "#30363d"
        empty_opacity = "0.16"
        white_piece = "#f0f6fc"
        black_piece = "#010409"
        accent = "#58a6ff"
        glow = "#f2cc60"
    else:
        bg = "#ffffff"
        panel = "#f6f8fa"
        text = "#24292f"
        muted = "#57606a"
        square_light = "#ffffff"
        square_dark = "#d0d7de"
        empty_opacity = "0.55"
        white_piece = "#24292f"
        black_piece = "#ffffff"
        accent = "#0969da"
        glow = "#bf8700"

    active = []

    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            count = int(day["contributionCount"])
            weekday = int(day["weekday"])

            x = board_x + week_index * step
            y = board_y + weekday * step

            active.append(
                {
                    "count": count,
                    "weekday": weekday,
                    "week": week_index,
                    "x": x,
                    "y": y,
                    "date": day["date"],
                    "level": contribution_level(count),
                }
            )

    active_days = [item for item in active if item["count"] > 0]
    random.seed(f"{USERNAME}-{total}-{len(active_days)}")

    max_pieces = 110
    if len(active_days) > max_pieces:
        active_days = sorted(active_days, key=lambda item: item["count"], reverse=True)[:max_pieces]
        active_days = sorted(active_days, key=lambda item: (item["week"], item["weekday"]))

    targets = active_days[:]
    random.shuffle(targets)

    svg = []

    svg.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Chess contribution animation for {html.escape(USERNAME)}">'
    )

    svg.append("<defs>")
    svg.append(
        f'<filter id="softGlow"><feDropShadow dx="0" dy="0" stdDeviation="2.2" flood-color="{glow}" flood-opacity="0.75"/></filter>'
    )
    svg.append(
        f'<linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{accent}"/>'
        f'<stop offset="100%" stop-color="{glow}"/>'
        f"</linearGradient>"
    )
    svg.append("</defs>")

    svg.append(f'<rect width="{width}" height="{height}" rx="22" fill="{bg}"/>')
    svg.append(f'<rect x="28" y="24" width="{width - 56}" height="{height - 48}" rx="18" fill="{panel}"/>')

    svg.append(
        f'<text x="{width / 2}" y="51" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="700" fill="url(#titleGradient)">'
        f'Tavares no tabuleiro dos commits'
        f"</text>"
    )

    svg.append(
        f'<text x="{width / 2}" y="226" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{muted}">'
        f'{total} contribuições nos últimos meses virando peças de xadrez'
        f"</text>"
    )

    svg.append('<g id="board">')

    level_colors_dark = {
        0: square_dark,
        1: "#0e4429",
        2: "#006d32",
        3: "#26a641",
        4: "#39d353",
    }

    level_colors_light = {
        0: square_dark,
        1: "#9be9a8",
        2: "#40c463",
        3: "#30a14e",
        4: "#216e39",
    }

    level_colors = level_colors_dark if dark else level_colors_light

    for item in active:
        x = item["x"]
        y = item["y"]
        level = item["level"]
        alternate = (item["week"] + item["weekday"]) % 2 == 0

        if level == 0:
            fill = square_light if alternate else square_dark
            opacity = empty_opacity
        else:
            fill = level_colors[level]
            opacity = "0.88"

        svg.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
            f'fill="{fill}" opacity="{opacity}"/>'
        )

    svg.append("</g>")

    svg.append('<g id="moves">')

    for index, item in enumerate(active_days):
        target = targets[index % len(targets)] if targets else item

        if target is item and len(targets) > 1:
            target = targets[(index + 1) % len(targets)]

        start_cx = item["x"] + cell / 2
        start_cy = item["y"] + cell / 2
        target_cx = target["x"] + cell / 2
        target_cy = target["y"] + cell / 2

        dx = round(target_cx - start_cx, 2)
        dy = round(target_cy - start_cy, 2)

        distance = math.sqrt(dx * dx + dy * dy)
        if distance < 20:
            dx = ((index % 9) - 4) * step
            dy = (((index * 2) % 7) - 3) * step

        is_white = (index + item["count"]) % 2 == 0
        piece = piece_for_count(item["count"], is_white)
        piece_color = white_piece if is_white else black_piece

        size = 15
        if item["count"] >= 5:
            size = 17
        if item["count"] >= 12:
            size = 19

        dur = 9 + (index % 9)
        begin = round((index % 12) * 0.22, 2)

        svg.append(f'<g transform="translate({start_cx} {start_cy})">')
        svg.append("<g>")
        svg.append(
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0; {dx} {dy}; {dx} {dy}; 0 0" '
            f'keyTimes="0; 0.42; 0.62; 1" dur="{dur}s" begin="{begin}s" '
            f'repeatCount="indefinite"/>'
        )
        svg.append(
            f'<animate attributeName="opacity" values="0.7;1;1;0.7" '
            f'dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
        )
        svg.append(
            f'<text x="0" y="0" text-anchor="middle" dominant-baseline="central" '
            f'font-family="Segoe UI Symbol, Noto Color Emoji, Apple Color Emoji, serif" '
            f'font-size="{size}" font-weight="700" fill="{piece_color}" filter="url(#softGlow)">'
            f'{piece}'
            f"</text>"
        )
        svg.append("</g>")
        svg.append("</g>")

        if index < 32:
            svg.append(
                f'<circle cx="{target_cx}" cy="{target_cy}" r="1" fill="{glow}" opacity="0">'
                f'<animate attributeName="opacity" values="0;0.85;0" '
                f'dur="{dur}s" begin="{begin + 3.4}s" repeatCount="indefinite"/>'
                f'<animate attributeName="r" values="1;7;1" '
                f'dur="{dur}s" begin="{begin + 3.4}s" repeatCount="indefinite"/>'
                f"</circle>"
            )

    svg.append("</g>")

    svg.append(
        f'<text x="50" y="239" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="11" fill="{muted}">menos</text>'
    )

    legend_x = 88
    legend_y = 230

    for level in range(5):
        fill = level_colors[level] if level > 0 else square_dark
        opacity = "0.35" if level == 0 else "0.9"
        svg.append(
            f'<rect x="{legend_x + level * 18}" y="{legend_y}" width="12" height="12" '
            f'rx="3" fill="{fill}" opacity="{opacity}"/>'
        )

    svg.append(
        f'<text x="{legend_x + 100}" y="239" font-family="Segoe UI, Arial, sans-serif" '
        f'font-size="11" fill="{muted}">mais</text>'
    )

    svg.append("</svg>")

    return "\n".join(svg)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN não encontrado no ambiente do workflow.")

    calendar = fetch_contributions(USERNAME, TOKEN)

    light_svg = build_svg(calendar, dark=False)
    dark_svg = build_svg(calendar, dark=True)

    (OUTPUT_DIR / "chess.svg").write_text(light_svg, encoding="utf-8")
    (OUTPUT_DIR / "chess_dark.svg").write_text(dark_svg, encoding="utf-8")

    print("SVG de xadrez gerado com sucesso.")
    print(f"Usuário: {USERNAME}")
    print(f"Total de contribuições: {calendar['totalContributions']}")


if __name__ == "__main__":
    main()