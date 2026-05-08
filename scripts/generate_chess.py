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

FILES = "abcdefgh"
RANKS = "12345678"

MOVE_BOOK = [
    ("e2", "e4"),
    ("e7", "e5"),
    ("g1", "f3"),
    ("b8", "c6"),
    ("f1", "c4"),
    ("f8", "c5"),
    ("c2", "c3"),
    ("g8", "f6"),
    ("d2", "d4"),
    ("e5", "d4"),
    ("c3", "d4"),
    ("c5", "b6"),
    ("b1", "c3"),
    ("d7", "d6"),
    ("c1", "g5"),
    ("h7", "h6"),
    ("g5", "h4"),
    ("g7", "g5"),
    ("f3", "g5"),
    ("h6", "g5"),
    ("h4", "g5"),
    ("c8", "e6"),
    ("d4", "d5"),
    ("c6", "e5"),
    ("d5", "e6"),
    ("f7", "e6"),
    ("d1", "a4"),
    ("d8", "d7"),
    ("a4", "d7"),
    ("e8", "d7"),
    ("c4", "e6"),
    ("d7", "e6"),
    ("c3", "d5"),
    ("e6", "d5"),
    ("a2", "a4"),
    ("a7", "a5"),
]


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


def read_active_days(calendar: dict) -> list[dict]:
    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            count = int(day["contributionCount"])

            if count > 0:
                days.append(
                    {
                        "date": day["date"],
                        "count": count,
                        "level": contribution_level(count),
                    }
                )

    if not days:
        today = dt.date.today().isoformat()
        days.append({"date": today, "count": 1, "level": 1})

    return days


def square_center(square: str, board_x: int, board_y: int, cell: int) -> tuple[float, float]:
    file_name = square[0]
    rank_name = square[1]

    file_index = FILES.index(file_name)
    rank_index = int(rank_name) - 1

    x = board_x + file_index * cell + cell / 2
    y = board_y + (7 - rank_index) * cell + cell / 2

    return x, y


def initial_game_state() -> tuple[dict, dict]:
    pieces = {}
    board = {}

    def add(piece_id: str, symbol: str, square: str, side: str, label: str) -> None:
        pieces[piece_id] = {
            "id": piece_id,
            "symbol": symbol,
            "square": square,
            "side": side,
            "label": label,
            "alive": True,
            "position_track": [],
            "opacity_track": [],
        }

        board[square] = piece_id

    for file_name in FILES:
        add(f"w_pawn_{file_name}", "♙", f"{file_name}2", "white", "peão branco")
        add(f"b_pawn_{file_name}", "♟", f"{file_name}7", "black", "peão preto")

    add("w_rook_a", "♖", "a1", "white", "torre branca")
    add("w_knight_b", "♘", "b1", "white", "cavalo branco")
    add("w_bishop_c", "♗", "c1", "white", "bispo branco")
    add("w_queen", "♕", "d1", "white", "dama branca")
    add("w_king", "♔", "e1", "white", "rei branco")
    add("w_bishop_f", "♗", "f1", "white", "bispo branco")
    add("w_knight_g", "♘", "g1", "white", "cavalo branco")
    add("w_rook_h", "♖", "h1", "white", "torre branca")

    add("b_rook_a", "♜", "a8", "black", "torre preta")
    add("b_knight_b", "♞", "b8", "black", "cavalo preto")
    add("b_bishop_c", "♝", "c8", "black", "bispo preto")
    add("b_queen", "♛", "d8", "black", "dama preta")
    add("b_king", "♚", "e8", "black", "rei preto")
    add("b_bishop_f", "♝", "f8", "black", "bispo preto")
    add("b_knight_g", "♞", "g8", "black", "cavalo preto")
    add("b_rook_h", "♜", "h8", "black", "torre preta")

    return pieces, board


def add_track(track: list, t: float, value: str) -> None:
    t = max(0.0, min(1.0, round(t, 6)))

    if track and abs(track[-1][0] - t) < 0.000001:
        track[-1] = (t, value)
    else:
        track.append((t, value))


def add_position(piece: dict, t: float, square: str, board_x: int, board_y: int, cell: int) -> None:
    x, y = square_center(square, board_x, board_y, cell)
    add_track(piece["position_track"], t, f"{round(x, 2)} {round(y, 2)}")


def add_opacity(piece: dict, t: float, value: float) -> None:
    add_track(piece["opacity_track"], t, str(value))


def normalize_track(track: list, default_value: str) -> tuple[str, str]:
    if not track:
        track = [(0.0, default_value), (1.0, default_value)]

    track = sorted(track, key=lambda item: item[0])

    if track[0][0] > 0:
        track.insert(0, (0.0, track[0][1]))

    if track[-1][0] < 1:
        track.append((1.0, track[-1][1]))

    cleaned = []

    for t, value in track:
        if cleaned and abs(cleaned[-1][0] - t) < 0.000001:
            cleaned[-1] = (t, value)
        else:
            cleaned.append((t, value))

    key_times = ";".join(
        format(t, ".6f").rstrip("0").rstrip(".") if t not in (0, 1) else str(int(t))
        for t, _ in cleaned
    )

    values = ";".join(value for _, value in cleaned)

    return key_times, values


def opacity_animation_keytimes(start: float, end: float) -> tuple[str, str]:
    eps = 0.0001

    start = max(0.0, min(1.0, start))
    end = max(0.0, min(1.0, end))

    if start <= 0 and end >= 1:
        return "0;1", "1;1"

    if start <= 0:
        t1 = max(0.0, end - eps)
        return f"0;{t1:.6f};{end:.6f};1", "1;1;0;0"

    if end >= 1:
        t0 = max(0.0, start - eps)
        return f"0;{t0:.6f};{start:.6f};1", "0;0;1;1"

    t0 = max(0.0, start - eps)
    t1 = max(0.0, end - eps)

    return f"0;{t0:.6f};{start:.6f};{t1:.6f};{end:.6f};1", "0;0;1;1;0;0"


def build_game(moves: list[tuple[str, str]], board_x: int, board_y: int, cell: int) -> tuple[dict, list[dict]]:
    pieces, board = initial_game_state()
    move_events = []
    total_moves = len(moves)

    for piece in pieces.values():
        add_position(piece, 0.0, piece["square"], board_x, board_y, cell)
        add_opacity(piece, 0.0, 1.0)

    for index, (source, target) in enumerate(moves):
        start_t = index / total_moves
        land_t = (index + 0.72) / total_moves
        end_t = (index + 1) / total_moves

        piece_id = board.get(source)

        if piece_id is None:
            continue

        piece = pieces[piece_id]
        captured_id = board.get(target)

        add_position(piece, start_t, source, board_x, board_y, cell)
        add_position(piece, land_t, target, board_x, board_y, cell)
        add_position(piece, end_t, target, board_x, board_y, cell)

        capture_label = None

        if captured_id is not None and captured_id != piece_id:
            captured = pieces[captured_id]

            add_position(captured, start_t, target, board_x, board_y, cell)
            add_opacity(captured, start_t, 1.0)
            add_opacity(captured, land_t, 0.0)
            add_opacity(captured, 1.0, 0.0)

            captured["alive"] = False
            capture_label = captured["label"]

        board.pop(source, None)
        board[target] = piece_id
        piece["square"] = target

        move_events.append(
            {
                "index": index,
                "source": source,
                "target": target,
                "piece": piece["symbol"],
                "side": piece["side"],
                "capture": capture_label,
                "start_t": start_t,
                "end_t": end_t,
                "land_t": land_t,
            }
        )

    for piece in pieces.values():
        add_position(piece, 1.0, piece["square"], board_x, board_y, cell)

        if piece["alive"]:
            add_opacity(piece, 1.0, 1.0)
        else:
            add_opacity(piece, 1.0, 0.0)

    return pieces, move_events


def select_moves(active_days: list[dict]) -> list[tuple[str, str]]:
    desired = min(len(MOVE_BOOK), max(18, min(36, len(active_days))))
    return MOVE_BOOK[:desired]


def build_svg(calendar: dict, dark: bool) -> str:
    active_days = read_active_days(calendar)
    moves = select_moves(active_days)

    width = 920
    height = 720

    board_x = 204
    board_y = 92
    cell = 64
    board_size = cell * 8

    total_duration = max(36, len(moves) * 1.45)

    pieces, move_events = build_game(moves, board_x, board_y, cell)

    if dark:
        bg = "#0d1117"
        panel = "#161b22"
        text = "#f0f6fc"
        muted = "#8b949e"
        light_square = "#f0d9b5"
        dark_square = "#b58863"
        white_piece = "#fff8dc"
        black_piece = "#111827"
        stroke = "#30363d"
        accent = "#58a6ff"
        capture = "#f2cc60"
        red = "#ff7b72"
    else:
        bg = "#ffffff"
        panel = "#f6f8fa"
        text = "#24292f"
        muted = "#57606a"
        light_square = "#f0d9b5"
        dark_square = "#b58863"
        white_piece = "#fff8dc"
        black_piece = "#111827"
        stroke = "#d0d7de"
        accent = "#0969da"
        capture = "#bf8700"
        red = "#cf222e"

    total = calendar["totalContributions"]

    svg = []

    svg.append(
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Partida de xadrez animada com contribuições de {html.escape(USERNAME)}">'
    )

    svg.append("<defs>")
    svg.append(
        '<filter id="pieceShadow">'
        '<feDropShadow dx="0" dy="3" stdDeviation="2.5" flood-color="#000000" flood-opacity="0.45"/>'
        "</filter>"
    )
    svg.append(
        f'<filter id="moveGlow">'
        f'<feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="{capture}" flood-opacity="0.95"/>'
        f"</filter>"
    )
    svg.append(
        f'<linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="0%">'
        f'<stop offset="0%" stop-color="{accent}"/>'
        f'<stop offset="100%" stop-color="{capture}"/>'
        f"</linearGradient>"
    )
    svg.append("</defs>")

    svg.append(f'<rect width="{width}" height="{height}" rx="24" fill="{bg}"/>')
    svg.append(
        f'<rect x="28" y="24" width="{width - 56}" height="{height - 48}" '
        f'rx="22" fill="{panel}" stroke="{stroke}"/>'
    )

    svg.append(
        f'<text x="{width / 2}" y="57" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="28" font-weight="800" fill="url(#titleGradient)">'
        f"Commits em xeque"
        f"</text>"
    )

    svg.append(
        f'<text x="{width / 2}" y="666" text-anchor="middle" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="15" fill="{muted}">'
        f"{total} contribuições alimentando uma partida animada de xadrez"
        f"</text>"
    )

    svg.append(f'<g id="board" transform="translate({board_x} {board_y})">')
    svg.append(f'<rect x="0" y="0" width="{board_size}" height="{board_size}" rx="16" fill="{stroke}"/>')

    for rank_from_top in range(8):
        for file_index in range(8):
            x = file_index * cell
            y = rank_from_top * cell
            is_light = (rank_from_top + file_index) % 2 == 0
            fill = light_square if is_light else dark_square

            svg.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{fill}"/>'
            )

    for file_index, file_name in enumerate(FILES):
        x = file_index * cell + cell / 2

        svg.append(
            f'<text x="{x}" y="{board_size + 24}" text-anchor="middle" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{muted}">{file_name}</text>'
        )

    for rank_index, rank_name in enumerate(reversed(RANKS)):
        y = rank_index * cell + cell / 2 + 5

        svg.append(
            f'<text x="-18" y="{y}" text-anchor="middle" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="14" fill="{muted}">{rank_name}</text>'
        )

    svg.append("</g>")

    for event_index, event in enumerate(move_events):
        source_x, source_y = square_center(event["source"], board_x, board_y, cell)
        target_x, target_y = square_center(event["target"], board_x, board_y, cell)

        key_times, values = opacity_animation_keytimes(event["start_t"], event["end_t"])

        commit = active_days[event_index % len(active_days)]
        capture_text = " com captura" if event["capture"] else ""
        side_text = "brancas" if event["side"] == "white" else "pretas"

        svg.append(f'<g opacity="0" filter="url(#moveGlow)">')
        svg.append(
            f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
            f'dur="{total_duration}s" repeatCount="indefinite"/>'
        )
        svg.append(
            f'<line x1="{source_x}" y1="{source_y}" x2="{target_x}" y2="{target_y}" '
            f'stroke="{red if event["capture"] else accent}" stroke-width="5" stroke-linecap="round" opacity="0.75"/>'
        )
        svg.append(
            f'<circle cx="{target_x}" cy="{target_y}" r="16" fill="none" '
            f'stroke="{red if event["capture"] else capture}" stroke-width="4"/>'
        )
        svg.append("</g>")

        svg.append(
            f'<text x="{width / 2}" y="622" text-anchor="middle" opacity="0" '
            f'font-family="Segoe UI, Arial, sans-serif" font-size="16" fill="{text}">'
        )
        svg.append(
            f'<animate attributeName="opacity" values="{values}" keyTimes="{key_times}" '
            f'dur="{total_duration}s" repeatCount="indefinite"/>'
        )
        svg.append(
            html.escape(
                f"Jogada {event_index + 1}: {event['piece']} {event['source']} para {event['target']} pelas {side_text}{capture_text} • {commit['count']} commit(s) em {commit['date']}"
            )
        )
        svg.append("</text>")

    svg.append('<g id="pieces">')

    for piece_id, piece in pieces.items():
        default_x, default_y = square_center(piece["square"], board_x, board_y, cell)

        position_key_times, position_values = normalize_track(
            piece["position_track"],
            f"{default_x} {default_y}",
        )

        opacity_key_times, opacity_values = normalize_track(piece["opacity_track"], "1")

        fill = white_piece if piece["side"] == "white" else black_piece
        stroke_piece = "#111827" if piece["side"] == "white" else "#f9fafb"

        svg.append(f'<g id="{piece_id}">')
        svg.append(
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{position_values}" keyTimes="{position_key_times}" '
            f'dur="{total_duration}s" repeatCount="indefinite"/>'
        )
        svg.append(
            f'<animate attributeName="opacity" values="{opacity_values}" keyTimes="{opacity_key_times}" '
            f'dur="{total_duration}s" repeatCount="indefinite"/>'
        )
        svg.append(
            f'<text x="0" y="0" text-anchor="middle" dominant-baseline="central" '
            f'font-family="Segoe UI Symbol, Noto Sans Symbols, DejaVu Sans, serif" '
            f'font-size="46" font-weight="800" fill="{fill}" stroke="{stroke_piece}" stroke-width="1.2" '
            f'paint-order="stroke fill" filter="url(#pieceShadow)">'
            f'{piece["symbol"]}'
            f"</text>"
        )
        svg.append("</g>")

    svg.append("</g>")

    progress_x = 250
    progress_y = 696
    progress_w = 420
    progress_h = 8

    svg.append(
        f'<rect x="{progress_x}" y="{progress_y}" width="{progress_w}" height="{progress_h}" '
        f'rx="4" fill="{stroke}"/>'
    )
    svg.append(
        f'<rect x="{progress_x}" y="{progress_y}" width="0" height="{progress_h}" rx="4" fill="{accent}">'
    )
    svg.append(
        f'<animate attributeName="width" values="0;{progress_w};0" keyTimes="0;0.97;1" '
        f'dur="{total_duration}s" repeatCount="indefinite"/>'
    )
    svg.append("</rect>")

    svg.append(
        f'<text x="{progress_x - 16}" y="{progress_y + 8}" text-anchor="end" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{muted}">início</text>'
    )
    svg.append(
        f'<text x="{progress_x + progress_w + 16}" y="{progress_y + 8}" text-anchor="start" '
        f'font-family="Segoe UI, Arial, sans-serif" font-size="12" fill="{muted}">mate</text>'
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

    print("Partida de xadrez gerada com sucesso.")
    print(f"Usuário: {USERNAME}")
    print(f"Total de contribuições: {calendar['totalContributions']}")


if __name__ == "__main__":
    main()
