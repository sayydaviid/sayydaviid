import datetime as dt
import html
import json
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

    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build_svg(calendar: dict, dark: bool = True) -> str:
    total = calendar["totalContributions"]

    width = 1000
    height = 620
    duration = 28

    bg = "#05050b"
    wall = "#312b92"
    wall_inner = "#4f46d9"
    pellet = "#ff7a1a"
    text = "#f8fafc"
    muted = "#94a3b8"
    pacman = "#ffc928"
    red = "#ff4b3e"
    pink = "#ff72b6"
    blue = "#58c7f3"
    orange = "#ff9f2f"
    green = "#57c785"

    svg = []

    svg.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Pacman animado de contribuições de {html.escape(USERNAME)}">'
    )

    svg.append("<defs>")
    svg.append(
        '<filter id="shadow">'
        '<feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.55"/>'
        "</filter>"
    )
    svg.append("</defs>")

    svg.append(f'<rect width="{width}" height="{height}" fill="{bg}"/>')

    svg.append(
        f'<text x="500" y="48" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="800" fill="{text}">'
        f'{html.escape(USERNAME)} no mapa dos commits'
        f"</text>"
    )

    svg.append(
        f'<text x="500" y="78" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="15" fill="{muted}">'
        f'SCORE {total}'
        f"</text>"
    )

    def wall_path(d: str) -> None:
        svg.append(
            f'<path d="{d}" fill="none" stroke="#080625" stroke-width="34" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )
        svg.append(
            f'<path d="{d}" fill="none" stroke="{wall}" stroke-width="24" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )
        svg.append(
            f'<path d="{d}" fill="none" stroke="{wall_inner}" stroke-width="4" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
        )

    svg.append('<g id="maze">')

    wall_path("M 70 110 H 930 V 520 H 70 Z")

    wall_path("M 120 160 H 250 V 250 H 120")
    wall_path("M 750 160 H 880 V 250 H 750")

    wall_path("M 120 380 H 250 V 470 H 120")
    wall_path("M 750 380 H 880 V 470 H 750")

    wall_path("M 315 160 H 460")
    wall_path("M 540 160 H 685")

    wall_path("M 315 470 H 460")
    wall_path("M 540 470 H 685")

    wall_path("M 315 220 V 355")
    wall_path("M 685 220 V 355")

    wall_path("M 390 250 H 610")
    wall_path("M 390 380 H 610")

    wall_path("M 440 300 H 560 V 350 H 440 Z")

    wall_path("M 70 310 H 210")
    wall_path("M 790 310 H 930")

    wall_path("M 250 250 V 380")
    wall_path("M 750 250 V 380")

    wall_path("M 315 410 H 685")

    svg.append("</g>")

    pellets = []
    for y in range(140, 500, 35):
        for x in range(105, 900, 35):
            blocked = False

            blocked_areas = [
                (95, 135, 275, 275),
                (725, 135, 905, 275),
                (95, 355, 275, 495),
                (725, 355, 905, 495),
                (295, 135, 480, 185),
                (520, 135, 705, 185),
                (295, 445, 480, 495),
                (520, 445, 705, 495),
                (290, 210, 340, 365),
                (660, 210, 710, 365),
                (365, 225, 635, 275),
                (365, 355, 635, 405),
                (415, 275, 585, 375),
                (40, 285, 230, 335),
                (770, 285, 960, 335),
            ]

            for x1, y1, x2, y2 in blocked_areas:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    blocked = True
                    break

            if not blocked:
                pellets.append((x, y))

    pacman_path = (
        "M 140 310 "
        "H 250 V 185 H 460 "
        "V 250 H 610 "
        "V 185 H 860 "
        "V 310 H 750 "
        "V 445 H 860 "
        "V 470 H 685 "
        "V 410 H 315 "
        "V 470 H 140 "
        "V 380 H 250 "
        "V 250 H 140 "
        "Z"
    )

    svg.append('<g id="pellets">')
    for index, (x, y) in enumerate(pellets):
        delay = round((index % 80) * 0.16, 2)

        svg.append(
            f'<circle cx="{x}" cy="{y}" r="4" fill="{pellet}">'
            f'<animate attributeName="opacity" values="1;1;0;0;1" '
            f'keyTimes="0;0.55;0.58;0.92;1" dur="{duration}s" '
            f'begin="{delay}s" repeatCount="indefinite"/>'
            f"</circle>"
        )
    svg.append("</g>")

    svg.append('<g id="bonus">')

    svg.append('<g transform="translate(300 160)">')
    svg.append(f'<circle cx="-8" cy="12" r="9" fill="#ff4b2b"/>')
    svg.append(f'<circle cx="10" cy="9" r="9" fill="#ff4b2b"/>')
    svg.append(f'<path d="M -5 2 C 6 -18 15 -22 22 -28" fill="none" stroke="{green}" stroke-width="3"/>')
    svg.append(f'<path d="M 22 -28 C 10 -31 5 -25 -1 -18" fill="{green}"/>')
    svg.append("</g>")

    svg.append('<g transform="translate(702 160) rotate(38)">')
    svg.append('<rect x="-7" y="-23" width="14" height="46" rx="7" fill="#ffffff"/>')
    svg.append('<rect x="-7" y="0" width="14" height="23" rx="7" fill="#ff563d"/>')
    svg.append("</g>")

    svg.append('<g transform="translate(500 485)">')
    svg.append(f'<circle cx="-8" cy="12" r="9" fill="#ff4b2b"/>')
    svg.append(f'<circle cx="10" cy="9" r="9" fill="#ff4b2b"/>')
    svg.append(f'<path d="M -5 2 C 6 -18 15 -22 22 -28" fill="none" stroke="{green}" stroke-width="3"/>')
    svg.append(f'<path d="M 22 -28 C 10 -31 5 -25 -1 -18" fill="{green}"/>')
    svg.append("</g>")

    svg.append("</g>")

    svg.append('<g id="characters" filter="url(#shadow)">')

    svg.append("<g>")
    svg.append(
        f'<animateMotion dur="{duration}s" repeatCount="indefinite" rotate="auto" path="{pacman_path}"/>'
    )
    svg.append(f'<circle cx="0" cy="0" r="22" fill="{pacman}"/>')
    svg.append(f'<polygon points="0,0 27,-15 27,15" fill="{bg}">')
    svg.append(
        '<animate attributeName="points" '
        'values="0,0 27,-15 27,15;0,0 27,-3 27,3;0,0 27,-15 27,15" '
        'dur="0.25s" repeatCount="indefinite"/>'
    )
    svg.append("</polygon>")
    svg.append('<circle cx="5" cy="-12" r="5" fill="#ffffff"/>')
    svg.append('<circle cx="7" cy="-12" r="2" fill="#111827"/>')
    svg.append("</g>")

    def ghost(color: str, path: str, delay: str) -> None:
        svg.append("<g>")
        svg.append(
            f'<animateMotion dur="{duration}s" begin="{delay}" repeatCount="indefinite" rotate="auto" path="{path}"/>'
        )
        svg.append(
            f'<path d="M -16 16 L -16 -5 C -16 -20 -8 -28 0 -28 C 8 -28 16 -20 16 -5 L 16 16 '
            f'L 10 10 L 5 16 L 0 10 L -5 16 L -10 10 Z" fill="{color}"/>'
        )
        svg.append('<circle cx="-6" cy="-11" r="4.5" fill="#ffffff"/>')
        svg.append('<circle cx="6" cy="-11" r="4.5" fill="#ffffff"/>')
        svg.append('<circle cx="-5" cy="-11" r="2" fill="#111827"/>')
        svg.append('<circle cx="7" cy="-11" r="2" fill="#111827"/>')
        svg.append("</g>")

    ghost(red, "M 500 310 H 610 V 250 H 390 V 380 H 610 V 310 H 500", "0s")
    ghost(pink, "M 170 420 H 250 V 250 H 315 V 470 H 170 Z", "2s")
    ghost(blue, "M 830 420 H 750 V 250 H 685 V 470 H 830 Z", "4s")
    ghost(orange, "M 500 185 H 860 V 310 H 750 V 445 H 500 Z", "6s")

    svg.append("</g>")

    svg.append(
        f'<text x="500" y="575" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="15" fill="{muted}">'
        f'{total} commits nos últimos meses'
        f"</text>"
    )

    svg.append("</svg>")

    return "\n".join(svg)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN não encontrado.")

    calendar = fetch_contributions(USERNAME, TOKEN)

    svg = build_svg(calendar, dark=False)
    svg_dark = build_svg(calendar, dark=True)

    (OUTPUT_DIR / "pacman_contribution_graph.svg").write_text(svg, encoding="utf-8")
    (OUTPUT_DIR / "pacman_contribution_graph_dark.svg").write_text(svg_dark, encoding="utf-8")

    print("Pacman gerado com sucesso.")
    print(f"Usuário: {USERNAME}")
    print(f"Total de contribuições: {calendar['totalContributions']}")


if __name__ == "__main__":
    main()