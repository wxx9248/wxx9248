#!/usr/bin/env python3
"""Render a GitHub contribution activity graph (last N days) as an SVG.

Usage: GITHUB_TOKEN=... python3 activity_graph.py <username> <output.svg> [days]
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

# github-dark palette
BG, TITLE, LINE, POINT, AXIS, GRID = "#0d1117", "#58a6ff", "#58a6ff", "#c3d1d9", "#8b949e", "#21262d"


def fetch(login, days, token):
    to = dt.datetime.now(dt.timezone.utc)
    frm = (to - dt.timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    body = json.dumps({"query": QUERY, "variables": {
        "login": login, "from": frm.isoformat(), "to": to.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "activity-graph"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors"):
        raise SystemExit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    out = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return out[-days:]


def nice_max(v):
    """Smallest 4 * step >= v, where step is 1, 2 or 5 times a power of ten."""
    need = max(1, -(-v // 4))
    mag = 1
    while True:
        for m in (1, 2, 5):
            if m * mag >= need:
                return 4 * m * mag
        mag *= 10


def render(login, points):
    W, H = 1200, 420
    L, R, T, B = 70, 30, 70, 70
    pw, ph = W - L - R, H - T - B
    ymax = nice_max(max((c for _, c in points), default=0))
    n = len(points)
    xs = [L + (pw * i / (n - 1) if n > 1 else pw / 2) for i in range(n)]
    ys = [T + ph - ph * c / ymax for _, c in points]

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
         '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
         f'<stop offset="0" stop-color="{LINE}" stop-opacity="0.45"/>'
         f'<stop offset="1" stop-color="{LINE}" stop-opacity="0.02"/></linearGradient></defs>',
         f'<rect width="{W}" height="{H}" fill="{BG}" rx="6"/>',
         f'<text x="{W/2}" y="40" fill="{TITLE}" font-size="22" font-weight="600" text-anchor="middle">'
         f'{escape(login)}\'s Contribution Graph</text>']
    for k in range(5):
        v = ymax * k / 4
        y = T + ph - ph * k / 4
        s.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="{GRID}"/>')
        s.append(f'<text x="{L-12}" y="{y+4:.1f}" fill="{AXIS}" font-size="12" text-anchor="end">{int(v)}</text>')
    for i, (date, _) in enumerate(points):
        s.append(f'<text x="{xs[i]:.1f}" y="{T+ph+22}" fill="{AXIS}" font-size="11" '
                 f'text-anchor="middle">{int(date[8:])}</text>')
    s.append(f'<text x="{W/2}" y="{H-14}" fill="{AXIS}" font-size="13" text-anchor="middle">Days</text>')
    s.append(f'<text x="20" y="{T+ph/2}" fill="{AXIS}" font-size="13" text-anchor="middle" '
             f'transform="rotate(-90 20 {T+ph/2})">Contributions</text>')
    if n:
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        s.append(f'<polygon points="{xs[0]:.1f},{T+ph} {line} {xs[-1]:.1f},{T+ph}" fill="url(#g)"/>')
        s.append(f'<polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round"/>')
        for (date, c), x, y in zip(points, xs, ys):
            s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{POINT}">'
                     f'<title>{date}: {c} contribution{"" if c == 1 else "s"}</title></circle>')
    s.append("</svg>")
    return "\n".join(s)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    login, out = sys.argv[1], sys.argv[2]
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 31
    token = os.environ.get("GITHUB_TOKEN") or sys.exit("GITHUB_TOKEN is not set")
    svg = render(login, fetch(login, days, token))
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
