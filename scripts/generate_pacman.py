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


def build_svg(calendar: dict) -> str:
    total = calendar["totalContributions"]

    # ── Dimensões ──────────────────────────────────────────────────────────────
    width  = 560
    height = 430
    duration = 24          # segundos de animação

    # ── Paleta clássica arcade ──────────────────────────────────────────────────
    bg           = "#000000"   # fundo preto puro
    wall_color   = "#2121de"   # azul clássico do Pac-Man
    wall_hi      = "#4f4fff"   # highlight interno (linha fina)
    pellet_color = "#ffffff"   # bolinhas brancas
    score_color  = "#ffff00"   # placar amarelo
    pacman_color = "#ffc928"   # amarelo do Pac-Man
    ghost_red    = "#ff0000"
    ghost_pink   = "#ffb8ff"
    ghost_blue   = "#00b8ff"
    ghost_orange = "#ffb847"

    svg = []

    # ── Cabeçalho SVG ──────────────────────────────────────────────────────────
    svg.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Contribuições de {html.escape(USERNAME)} no estilo Pac-Man">'
    )

    # ── Sombra suave nos personagens ───────────────────────────────────────────
    svg.append("<defs>")
    svg.append(
        '<filter id="glow">'
        '<feDropShadow dx="0" dy="0" stdDeviation="3" '
        'flood-color="#ffffff" flood-opacity="0.35"/>'
        "</filter>"
    )
    svg.append("</defs>")

    # ── Fundo ──────────────────────────────────────────────────────────────────
    svg.append(f'<rect width="{width}" height="{height}" fill="{bg}"/>')

    # ── Título clássico ────────────────────────────────────────────────────────
    svg.append(
        f'<text x="280" y="22" text-anchor="middle" '
        f'font-family="\'Courier New\', monospace" font-size="13" font-weight="bold" '
        f'fill="{score_color}" letter-spacing="2">'
        f'{html.escape(USERNAME.upper())}'
        f"</text>"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Labirinto clássico
    # Origem do labirinto: x=20, y=32   largura=520  altura=340
    # Célula base: 20×20 px  →  26 colunas × 17 linhas
    # ══════════════════════════════════════════════════════════════════════════
    MX, MY = 20, 32       # origem
    CW, CH = 20, 20       # tamanho da célula

    def gx(col): return MX + col * CW   # coordenada x pela coluna
    def gy(row): return MY + row * CH   # coordenada y pela linha

    # ── Desenha uma parede: duas linhas (cor base + highlight) ─────────────────
    def wall(d: str) -> None:
        svg.append(
            f'<path d="{d}" fill="none" stroke="{wall_color}" '
            f'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        svg.append(
            f'<path d="{d}" fill="none" stroke="{wall_hi}" '
            f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" '
            f'opacity="0.7"/>'
        )

    svg.append('<g id="maze">')

    # Borda externa
    wall(f"M {gx(0)} {gy(0)} H {gx(26)} V {gy(17)} H {gx(0)} Z")

    # ── Bloco superior-esquerdo ────────────────────────────────────────────────
    wall(f"M {gx(1)} {gy(1)} H {gx(5)} V {gy(4)} H {gx(1)}")
    wall(f"M {gx(7)} {gy(1)} H {gx(11)}")
    wall(f"M {gx(7)} {gy(1)} V {gy(3)}")
    wall(f"M {gx(1)} {gy(6)} H {gx(5)} V {gy(8)} H {gx(1)}")
    wall(f"M {gx(7)} {gy(4)} H {gx(11)} V {gy(8)} H {gx(7)}")

    # ── Bloco superior-direito (espelho) ───────────────────────────────────────
    wall(f"M {gx(25)} {gy(1)} H {gx(21)} V {gy(4)} H {gx(25)}")
    wall(f"M {gx(19)} {gy(1)} H {gx(15)}")
    wall(f"M {gx(19)} {gy(1)} V {gy(3)}")
    wall(f"M {gx(25)} {gy(6)} H {gx(21)} V {gy(8)} H {gx(25)}")
    wall(f"M {gx(19)} {gy(4)} H {gx(15)} V {gy(8)} H {gx(19)}")

    # ── Corredor central superior ──────────────────────────────────────────────
    wall(f"M {gx(12)} {gy(1)} H {gx(14)}")
    wall(f"M {gx(12)} {gy(3)} H {gx(14)} V {gy(6)} H {gx(12)} Z")

    # ── Túneis laterais (linhas abertas no meio) ───────────────────────────────
    wall(f"M {gx(1)} {gy(10)} H {gx(5)} V {gy(13)} H {gx(1)}")
    wall(f"M {gx(25)} {gy(10)} H {gx(21)} V {gy(13)} H {gx(25)}")

    # ── Bloco meio-esquerdo ────────────────────────────────────────────────────
    wall(f"M {gx(7)} {gy(10)} H {gx(11)} V {gy(12)}")
    wall(f"M {gx(7)} {gy(10)} V {gy(13)}")

    # ── Bloco meio-direito ─────────────────────────────────────────────────────
    wall(f"M {gx(19)} {gy(10)} H {gx(15)} V {gy(12)}")
    wall(f"M {gx(19)} {gy(10)} V {gy(13)}")

    # ── Casa dos fantasmas (centro) ────────────────────────────────────────────
    ghost_box = (
        f"M {gx(10)} {gy(7)} H {gx(16)} V {gy(10)} H {gx(10)} Z"
    )
    svg.append(
        f'<path d="{ghost_box}" fill="none" stroke="{wall_color}" '
        f'stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    svg.append(
        f'<path d="{ghost_box}" fill="none" stroke="{wall_hi}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>'
    )
    # Porta da casa (abertura no topo, linha rosa)
    portal_x1 = gx(12)
    portal_x2 = gx(14)
    portal_y  = gy(7)
    svg.append(
        f'<line x1="{portal_x1}" y1="{portal_y}" x2="{portal_x2}" y2="{portal_y}" '
        f'stroke="#ffb8ff" stroke-width="3"/>'
    )

    # ── Bloco inferior-esquerdo ────────────────────────────────────────────────
    wall(f"M {gx(1)} {gy(14)} H {gx(5)} V {gy(16)} H {gx(1)}")
    wall(f"M {gx(7)} {gy(13)} H {gx(11)} V {gy(16)} H {gx(7)}")
    wall(f"M {gx(12)} {gy(13)} H {gx(14)}")

    # ── Bloco inferior-direito (espelho) ───────────────────────────────────────
    wall(f"M {gx(25)} {gy(14)} H {gx(21)} V {gy(16)} H {gx(25)}")
    wall(f"M {gx(19)} {gy(13)} H {gx(15)} V {gy(16)} H {gx(19)}")

    svg.append("</g>")

    # ══════════════════════════════════════════════════════════════════════════
    # Pellets (bolinhas brancas)
    # Grade de 20×20 px; evita células de parede e casa dos fantasmas
    # ══════════════════════════════════════════════════════════════════════════

    # Regiões bloqueadas (col_min, row_min, col_max, row_max) — inclusive
    blocked_rects = [
        (0,  0, 0, 17),  (26, 0, 26, 17),   # bordas
        (0,  0, 26, 0),  (0, 17, 26, 17),
        (1,  1, 5,  4),  (21, 1, 25, 4),     # blocos sup
        (7,  1, 11, 0),  (15, 1, 19, 0),
        (7,  1, 7,  3),  (19, 1, 19, 3),
        (1,  6, 5,  8),  (21, 6, 25, 8),
        (7,  4, 11, 8),  (15, 4, 19, 8),
        (12, 1, 14, 1),  (12, 3, 14, 6),
        (10, 7, 16, 10),                      # casa dos fantasmas
        (1, 10, 5, 13),  (21,10, 25,13),     # blocos meio
        (7, 10, 11,12),  (15,10, 19,12),
        (7, 10, 7, 13),  (19,10, 19,13),
        (1, 14, 5, 16),  (21,14, 25,16),     # blocos inf
        (7, 13, 11,16),  (15,13, 19,16),
        (12,13, 14,13),
    ]

    def is_blocked(col, row):
        for x1, y1, x2, y2 in blocked_rects:
            if x1 <= col <= x2 and y1 <= row <= y2:
                return True
        return False

    pellets = []
    for row in range(1, 17):
        for col in range(1, 26):
            if not is_blocked(col, row):
                px = gx(col) + CW // 2
                py = gy(row) + CH // 2
                pellets.append((px, py))

    # Power pellets (4 cantos)
    power_positions = [
        (gx(1) + 10, gy(1) + 10),
        (gx(25) + 10, gy(1) + 10),
        (gx(1) + 10, gy(15) + 10),
        (gx(25) + 10, gy(15) + 10),
    ]

    svg.append('<g id="pellets">')
    for index, (px, py) in enumerate(pellets):
        delay = round((index % 60) * 0.18, 2)
        svg.append(
            f'<circle cx="{px}" cy="{py}" r="2.5" fill="{pellet_color}">'
            f'<animate attributeName="opacity" values="1;1;0;0;1" '
            f'keyTimes="0;0.50;0.54;0.96;1" dur="{duration}s" '
            f'begin="{delay}s" repeatCount="indefinite"/>'
            f"</circle>"
        )

    # Power pellets piscantes
    for px, py in power_positions:
        svg.append(
            f'<circle cx="{px}" cy="{py}" r="6" fill="{pellet_color}">'
            f'<animate attributeName="opacity" values="1;0;1" '
            f'keyTimes="0;0.5;1" dur="0.6s" repeatCount="indefinite"/>'
            f"</circle>"
        )
    svg.append("</g>")

    # ══════════════════════════════════════════════════════════════════════════
    # Rota do Pac-Man — percorre o labirinto em loop
    # ══════════════════════════════════════════════════════════════════════════
    pm = lambda c, r: f"{gx(c) + 10} {gy(r) + 10}"

    pacman_path = (
        f"M {pm(1,15)} "
        f"H {pm(25,15)} "
        f"V {pm(25,13)} "
        f"H {pm(20,13)} "
        f"V {pm(20,10)} "
        f"H {pm(25,10)} "
        f"V {pm(25,6)} "
        f"H {pm(20,6)} "
        f"V {pm(20,4)} "
        f"H {pm(25,4)} "
        f"V {pm(25,1)} "
        f"H {pm(20,1)} "
        f"V {pm(20,3)} "
        f"H {pm(15,3)} "
        f"V {pm(15,1)} "
        f"H {pm(12,1)} "
        f"V {pm(12,3)} "
        f"H {pm(7,3)} "
        f"V {pm(7,1)} "
        f"H {pm(1,1)} "
        f"V {pm(1,8)} "
        f"H {pm(6,8)} "
        f"V {pm(6,4)} "
        f"H {pm(12,4)} "
        f"V {pm(12,6)} "
        f"H {pm(14,6)} "
        f"V {pm(14,4)} "
        f"H {pm(20,4)} "
        f"V {pm(20,8)} "
        f"H {pm(25,8)} "
        f"V {pm(25,6)} "
        f"H {pm(20,6)} "
        f"V {pm(20,10)} "
        f"H {pm(12,10)} "
        f"V {pm(12,13)} "
        f"H {pm(15,13)} "
        f"V {pm(15,10)} "
        f"H {pm(20,10)} "
        f"H {pm(14,10)} "
        f"V {pm(14,13)} "
        f"H {pm(7,13)} "
        f"V {pm(7,10)} "
        f"H {pm(1,10)} "
        f"V {pm(1,15)} Z"
    )

    # ══════════════════════════════════════════════════════════════════════════
    # Personagens
    # ══════════════════════════════════════════════════════════════════════════
    svg.append('<g id="characters" filter="url(#glow)">')

    # ── Pac-Man ────────────────────────────────────────────────────────────────
    svg.append("<g>")
    svg.append(
        f'<animateMotion dur="{duration}s" repeatCount="indefinite" '
        f'rotate="auto" path="{pacman_path}"/>'
    )
    svg.append(f'<circle cx="0" cy="0" r="9" fill="{pacman_color}"/>')
    # boca animada
    svg.append(f'<polygon points="0,0 12,-7 12,7" fill="{bg}">')
    svg.append(
        '<animate attributeName="points" '
        'values="0,0 12,-7 12,7;0,0 12,-1 12,1;0,0 12,-7 12,7" '
        'dur="0.22s" repeatCount="indefinite"/>'
    )
    svg.append("</polygon>")
    svg.append("</g>")

    # ── Fantasmas ──────────────────────────────────────────────────────────────
    def ghost(color: str, path: str, delay: str) -> None:
        svg.append("<g>")
        svg.append(
            f'<animateMotion dur="{duration}s" begin="{delay}" '
            f'repeatCount="indefinite" rotate="auto" path="{path}"/>'
        )
        # corpo do fantasma
        svg.append(
            f'<path d="M -9 9 L -9 -4 '
            f'C -9 -14 -5 -18 0 -18 C 5 -18 9 -14 9 -4 L 9 9 '
            f'L 6 6 L 3 9 L 0 6 L -3 9 L -6 6 Z" fill="{color}"/>'
        )
        # olhos
        svg.append('<circle cx="-3.5" cy="-7" r="3" fill="#ffffff"/>')
        svg.append('<circle cx="3.5"  cy="-7" r="3" fill="#ffffff"/>')
        svg.append('<circle cx="-2.5" cy="-7" r="1.5" fill="#222aff"/>')
        svg.append('<circle cx="4.5"  cy="-7" r="1.5" fill="#222aff"/>')
        svg.append("</g>")

    # Rotas dos fantasmas (circulam pela casa e saem)
    ghost_path_red = (
        f"M {pm(13,8)} V {pm(13,6)} H {pm(8,6)} V {pm(8,13)} "
        f"H {pm(13,13)} V {pm(13,8)} Z"
    )
    ghost_path_pink = (
        f"M {pm(13,8)} V {pm(13,11)} H {pm(18,11)} V {pm(18,6)} "
        f"H {pm(13,6)} V {pm(13,8)} Z"
    )
    ghost_path_blue = (
        f"M {pm(13,8)} H {pm(8,8)} V {pm(8,2)} H {pm(18,2)} "
        f"V {pm(18,8)} H {pm(13,8)} Z"
    )
    ghost_path_orange = (
        f"M {pm(13,8)} H {pm(18,8)} V {pm(18,15)} H {pm(8,15)} "
        f"V {pm(8,8)} H {pm(13,8)} Z"
    )

    ghost(ghost_red,    ghost_path_red,    "0s")
    ghost(ghost_pink,   ghost_path_pink,   "2s")
    ghost(ghost_blue,   ghost_path_blue,   "4s")
    ghost(ghost_orange, ghost_path_orange, "6s")

    svg.append("</g>")

    # ══════════════════════════════════════════════════════════════════════════
    # Placar — estilo clássico, canto inferior esquerdo
    # ══════════════════════════════════════════════════════════════════════════
    score_y = MY + 17 * CH + 22
    svg.append(
        f'<text x="16" y="{score_y}" '
        f'font-family="\'Courier New\', monospace" font-size="15" font-weight="bold" '
        f'fill="{score_color}" letter-spacing="1">'
        f'SCORE: {total}'
        f"</text>"
    )

    svg.append("</svg>")
    return "\n".join(svg)


def main() -> None:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN não encontrado.")

    calendar = fetch_contributions(USERNAME, TOKEN)
    svg = build_svg(calendar)
    (OUTPUT_DIR / "pacman_contribution_graph.svg").write_text(svg, encoding="utf-8")

    print("Pacman gerado com sucesso.")
    print(f"Usuário: {USERNAME}")
    print(f"Total de contribuições: {calendar['totalContributions']}")


if __name__ == "__main__":
    main()