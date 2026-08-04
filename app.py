from __future__ import annotations

import calendar
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

YEAR = 2026
MONTH = 8
MONTH_NAME = "August"
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# The whole group (used to figure out who hasn't given their availability yet,
# and to populate the selectable people list on the right).
ALL_MEMBERS = [
    "Gaia", "Joel", "Adam", "Alessandra", "Beyza", "Chloe", "Cleo", "Eylul",
    "Ivana", "Minh", "Nina", "Owen", "Theodora", "Vicky", "Will", "Alicja",
    "Amzu", "Bartu", "Isaline", "Lara", "Laura", "Mustafa", "Nishi", "Ole",
    "Shania", "Mikolaj",
]

# People without whom dinner can't happen at all: if even one of these is
# missing (and selected), the day is normally marked "bad" (gray) — unless
# only a small number of people are missing overall (see MAX_MISSING_FOR_OK).
KEY_PEOPLE = {"Gaia", "Eylul", "Chloe", "Bartu", "Lara", "Nishi"}

# If a key person is missing but the TOTAL number of missing people that day
# is this many or fewer, we still call it "ok" instead of "bad" — a day
# where almost everyone (including a key person) is free still counts.
MAX_MISSING_FOR_OK = 4

# Days that have already gone by: no point planning a dinner on these.
PAST_DAYS = {1, 2, 3, 4}


def is_past(day: date) -> bool:
    return day.month == MONTH and day.day in PAST_DAYS


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def add_unavailability(
    unavailable_by_person: dict[str, set[date]],
    person: str,
    start_date: str,
    end_date: str | None = None,
) -> None:
    start = parse_date(start_date)
    end = parse_date(end_date) if end_date else start
    for day in daterange(start, end):
        unavailable_by_person[person].add(day)


def build_data() -> tuple[list[list[date]], dict[str, set[date]]]:
    unavailable_by_person: dict[str, set[date]] = defaultdict(set)

    add_unavailability(unavailable_by_person, "Gaia", "2026-08-31")
    add_unavailability(unavailable_by_person, "Joel", "2026-08-20", "2026-08-31")

    # Vicky already gave her availability in an earlier message and it wasn't
    # repeated in the latest update: kept as-is.
    add_unavailability(unavailable_by_person, "Vicky", "2026-08-15", "2026-08-19")
    add_unavailability(unavailable_by_person, "Vicky", "2026-08-03", "2026-08-14")

    # Alessandra is unavailable from the 14th to the 25th, but is free in the
    # evening of the 18th and the 25th: for a dinner we count those as free.
    add_unavailability(unavailable_by_person, "Alessandra", "2026-08-14", "2026-08-25")
    unavailable_by_person["Alessandra"].discard(parse_date("2026-08-18"))
    unavailable_by_person["Alessandra"].discard(parse_date("2026-08-25"))

    add_unavailability(unavailable_by_person, "Beyza", "2026-08-17", "2026-08-20")
    add_unavailability(unavailable_by_person, "Cleo", "2026-08-04", "2026-08-09")
    add_unavailability(unavailable_by_person, "Cleo", "2026-08-14", "2026-08-16")
    add_unavailability(unavailable_by_person, "Cleo", "2026-08-21", "2026-08-23")

    add_unavailability(unavailable_by_person, "Amzu", "2026-08-23", "2026-08-31")
    add_unavailability(unavailable_by_person, "Eylul", "2026-08-13", "2026-08-31")
    add_unavailability(unavailable_by_person, "Minh", "2026-08-08", "2026-08-23")

    add_unavailability(unavailable_by_person, "Mikolaj", "2026-08-30", "2026-08-31")
    add_unavailability(unavailable_by_person, "Will", "2026-08-01", "2026-08-12")
    add_unavailability(unavailable_by_person, "Will", "2026-08-30", "2026-08-31")

    add_unavailability(unavailable_by_person, "Nina", "2026-08-01", "2026-08-26")

    # Mustafa is unavailable from the 27th onward
    add_unavailability(unavailable_by_person, "Mustafa", "2026-08-27", "2026-08-31")

    # Ole is only available from the 17th to the 26th
    add_unavailability(unavailable_by_person, "Ole", "2026-08-01", "2026-08-16")
    add_unavailability(unavailable_by_person, "Ole", "2026-08-27", "2026-08-31")

    add_unavailability(unavailable_by_person, "Isaline", "2026-08-12", "2026-08-16")
    add_unavailability(unavailable_by_person, "Isaline", "2026-08-21", "2026-08-23")

    # Nina (1-26) and Ole (1-16) already cover the 3rd-14th, no change needed
    # for them. Ivana and Laura are new.
    add_unavailability(unavailable_by_person, "Ivana", "2026-08-03", "2026-08-14")
    add_unavailability(unavailable_by_person, "Laura", "2026-08-03", "2026-08-14")

    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(YEAR, MONTH)

    return weeks, unavailable_by_person


def day_unavailable_people(day: date, unavailable_by_person: dict[str, set[date]]) -> list[str]:
    return sorted([person for person, days in unavailable_by_person.items() if day in days])


def day_status(day: date, unavailable_by_person: dict[str, set[date]]) -> tuple[str, list[str]]:
    unavailable_today = day_unavailable_people(day, unavailable_by_person)
    key_missing = [p for p in unavailable_today if p in KEY_PEOPLE]

    if is_past(day):
        return "bad", unavailable_today
    if key_missing and len(unavailable_today) > MAX_MISSING_FOR_OK:
        return "bad", unavailable_today
    if unavailable_today:
        return "ok", unavailable_today
    return "perfect", []


def render_html() -> str:
    weeks, unavailable_by_person = build_data()

    month_days = [d for w in weeks for d in w if d.month == MONTH]

    status_by_day: dict[date, str] = {}
    unavailable_by_day: dict[date, list[str]] = {}

    for d in month_days:
        st, unav = day_status(d, unavailable_by_person)
        status_by_day[d] = st
        unavailable_by_day[d] = unav

    week_rows = []
    for week in weeks:
        cells = []
        for day in week:
            in_month = day.month == MONTH
            classes = ["day-cell"]
            data_attr = ""

            if not in_month:
                classes.append("outside")
                note_html = ""
            else:
                st = status_by_day[day]
                classes.append(st)
                data_attr = f' data-date="{day.isoformat()}"'

                unavailable_today = unavailable_by_day[day]

                if st == "perfect":
                    note_html = '<div class="note note-ok">Everyone available</div>'
                elif st == "bad":
                    if unavailable_today:
                        names = ", ".join(unavailable_today)
                        note_html = f'<div class="note note-bad">Missing: {names}</div>'
                    else:
                        note_html = '<div class="note note-bad">Not good</div>'
                else:
                    names = ", ".join(unavailable_today)
                    note_html = f'<div class="note">Missing: {names}</div>'

            cells.append(
                "".join(
                    [
                        f'<div class="{" ".join(classes)}"{data_attr}>',
                        f'<div class="date">{day.day}</div>',
                        note_html,
                        "</div>",
                    ]
                )
            )

        week_rows.append(f'<div class="week-row">{"".join(cells)}</div>')

    tracked_set = set(unavailable_by_person.keys())
    tracked = ", ".join(sorted(tracked_set)) or "none"

    not_tracked = sorted(name for name in ALL_MEMBERS if name not in tracked_set)
    not_tracked_html = (
        "".join(f'<span class="chip">{name}</span>' for name in not_tracked)
        if not_tracked
        else '<span class="chip chip-ok">Everyone has responded!</span>'
    )

    # Data handed off to the client so the sidebar checkboxes can
    # recompute each day's status without reloading the page.
    people_payload = {
        name: sorted(d.isoformat() for d in dates)
        for name, dates in unavailable_by_person.items()
    }
    client_data = {
        "people": people_payload,
        "keyPeople": sorted(KEY_PEOPLE),
        "allMembers": ALL_MEMBERS,
        "pastDates": [d.isoformat() for d in month_days if is_past(d)],
        "maxMissingForOk": MAX_MISSING_FOR_OK,
    }
    client_data_json = json.dumps(client_data, ensure_ascii=False)

    checkbox_items = "".join(
        f'<label><input type="checkbox" value="{name}" checked> {name}</label>'
        for name in sorted(ALL_MEMBERS)
    )

    priority_chips_html = "".join(
        f'<span class="chip">{name}</span>' for name in sorted(KEY_PEOPLE)
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>August 2026 Calendar</title>
  <style>
    :root {{
      --bg: #f5f5f7;
      --panel: #ffffff;
      --text: #1d1d1f;
      --muted: #6e6e73;
      --grid: #d2d2d7;
      --outside: rgba(210, 210, 215, 0.35);
      --bad: rgba(119, 119, 126, 0.30);
      --ok-border: #ff9f0a;
      --perfect-border: #34c759;
      --radius: 10px;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      padding: 28px;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }}

    .wrap {{
      max-width: 1260px;
      margin: 0 auto;
      background: var(--panel);
      border: 1px solid #e5e5ea;
      border-radius: 14px;
      padding: 20px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.04);
    }}

    h1 {{
      margin: 0;
      font-size: 34px;
      line-height: 1.1;
    }}

    /* --- LEGEND --- */
    .legend {{
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      align-items: center;
    }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--text);
    }}

    .swatch {{
      width: 16px;
      height: 16px;
      border-radius: 5px;
      flex-shrink: 0;
    }}

    .swatch-perfect {{ border: 2.5px solid var(--perfect-border); background: #fff; }}
    .swatch-ok {{ border: 2.5px solid var(--ok-border); background: #fff; }}
    .swatch-bad {{ background: var(--bad); border: 1px solid var(--grid); }}

    /* --- GRID --- */
    .weekday-row,
    .week-row {{
      display: grid;
      grid-template-columns: repeat(7, minmax(120px, 1fr));
      gap: 8px;
    }}

    .weekday-row {{
      margin-top: 18px;
      margin-bottom: 8px;
    }}

    .weekday {{
      text-align: center;
      color: #8e8e93;
      font-weight: 600;
      font-size: 13px;
    }}

    .week-row {{
      margin-bottom: 8px;
    }}

    .day-cell {{
      min-height: 110px;
      border: 1px solid var(--grid);
      border-radius: var(--radius);
      background: #fff;
      padding: 10px;
      position: relative;
      overflow: hidden;
    }}

    .day-cell.outside {{
      background: var(--outside);
      color: #a1a1a6;
    }}

    .day-cell.bad {{
      background: var(--bad);
    }}

    .day-cell.ok {{
      border: 2.5px solid var(--ok-border);
    }}

    .day-cell.perfect {{
      border: 2.5px solid var(--perfect-border);
    }}

    .date {{
      font-size: 18px;
      font-weight: 650;
    }}

    .note {{
      margin-top: 10px;
      color: #4e4e55;
      font-size: 12px;
      font-weight: 600;
      line-height: 1.3;
    }}

    .note-bad {{ color: #48484c; }}
    .note-ok {{ color: #1f7a41; }}

    .footer {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }}

    .not-tracked {{
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid #e5e5ea;
    }}

    .not-tracked h2 {{
      margin: 0 0 10px 0;
      font-size: 15px;
      color: var(--text);
    }}

    .chip {{
      display: inline-block;
      padding: 5px 10px;
      margin: 0 6px 6px 0;
      background: #f2f2f7;
      border: 1px solid #e5e5ea;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      color: #6e6e73;
    }}

    .chip-ok {{
      background: #e6f7ec;
      border-color: #34c759;
      color: #1f7a41;
    }}

    /* --- SIDE PANEL --- */
    .people-toggle {{
      position: fixed;
      top: 0;
      right: 0;
      height: 100%;
      width: 48px;
      z-index: 20;
      display: flex;
      align-items: flex-start;
      justify-content: center;
      padding-top: 24px;
      background: var(--panel);
      color: var(--text);
      border: none;
      border-left: 1px solid #e5e5ea;
      cursor: pointer;
      box-shadow: -4px 0 16px rgba(0, 0, 0, 0.04);
      transition: right 0.25s ease, background 0.15s ease;
    }}

    .people-toggle:hover {{
      background: #f5f5f7;
    }}

    .people-toggle svg {{
      width: 18px;
      height: 18px;
      flex-shrink: 0;
    }}

    .people-toggle.open {{
      right: 260px;
      background: #f0f0f2;
    }}

    .people-panel {{
      position: fixed;
      top: 0;
      right: 0;
      height: 100%;
      width: 260px;
      background: #fff;
      border-left: 1px solid #e5e5ea;
      box-shadow: -8px 0 30px rgba(0, 0, 0, 0.08);
      padding: 22px;
      transform: translateX(100%);
      transition: transform 0.25s ease;
      z-index: 15;
      overflow-y: auto;
    }}

    .people-panel.open {{
      transform: translateX(0);
    }}

    .people-panel h2 {{
      margin: 0 0 4px 0;
      font-size: 16px;
    }}

    .people-panel-sub {{
      margin: 0 0 14px 0;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.4;
    }}

    .people-actions {{
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }}

    .people-actions button {{
      flex: 1;
      font-size: 12px;
      font-weight: 600;
      padding: 6px 8px;
      border-radius: 6px;
      border: 1px solid #d2d2d7;
      background: #f5f5f7;
      color: var(--text);
      cursor: pointer;
    }}

    .people-list label {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      padding: 7px 2px;
      border-bottom: 1px solid #f2f2f7;
      cursor: pointer;
    }}

    .people-list input {{
      width: 15px;
      height: 15px;
      cursor: pointer;
    }}

    .priority-details {{
      margin-bottom: 14px;
      border: 1px solid #e5e5ea;
      border-radius: 8px;
      padding: 8px 10px;
    }}

    .priority-details summary {{
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      color: var(--text);
      list-style: none;
    }}

    .priority-details summary::-webkit-details-marker {{
      display: none;
    }}

    .priority-details summary::before {{
      content: "▸";
      display: inline-block;
      margin-right: 6px;
      color: var(--muted);
      transition: transform 0.15s ease;
    }}

    .priority-details[open] summary::before {{
      transform: rotate(90deg);
    }}

    .priority-chips {{
      margin-top: 10px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    @media (max-width: 980px) {{
      body {{ padding: 14px; }}
      .wrap {{ padding: 14px; }}
      .weekday-row,
      .week-row {{
        grid-template-columns: repeat(7, minmax(90px, 1fr));
        gap: 6px;
      }}
      .day-cell {{ min-height: 96px; padding: 8px; }}
      .date {{ font-size: 16px; }}
      .note {{ font-size: 11px; }}
      .people-panel {{ width: 82vw; }}
      .people-toggle.open {{ right: 82vw; }}
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>{MONTH_NAME} {YEAR}</h1>

    <div class="legend">
      <div class="legend-item"><span class="swatch swatch-perfect"></span>Perfect — everyone available</div>
      <div class="legend-item"><span class="swatch swatch-ok"></span>OK</div>
      <div class="legend-item"><span class="swatch swatch-bad"></span>Not good</div>
    </div>

    <section class="weekday-row">
      {''.join(f'<div class="weekday">{w}</div>' for w in WEEKDAY_LABELS)}
    </section>

    <section>
      {''.join(week_rows)}
    </section>

    <div class="footer">Tracked people: {tracked}</div>

    <div class="not-tracked">
      <h2>Not yet responded</h2>
      {not_tracked_html}
    </div>
  </main>

  <button id="people-toggle" class="people-toggle" type="button" aria-label="Toggle people list">
    <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2.5" y="3.5" width="15" height="13" rx="3" stroke="currentColor" stroke-width="1.4"/>
      <line x1="12.5" y1="3.5" x2="12.5" y2="16.5" stroke="currentColor" stroke-width="1.4"/>
    </svg>
  </button>
  <aside id="people-panel" class="people-panel">
    <h2>People</h2>
    <p class="people-panel-sub">Untick someone to see how the calendar looks without them.</p>

    <details class="priority-details">
      <summary>Priority people</summary>
      <div class="priority-chips">{priority_chips_html}</div>
    </details>

    <div class="people-actions">
      <button type="button" id="select-all">Select all</button>
      <button type="button" id="select-none">Select none</button>
    </div>
    <div id="people-list" class="people-list">
      {checkbox_items}
    </div>
  </aside>

  <script id="calendar-data" type="application/json">{client_data_json}</script>
  <script>
    const DATA = JSON.parse(document.getElementById('calendar-data').textContent);
    const selected = new Set(DATA.allMembers);

    function computeStatus(dateStr) {{
      const unavailable = [];
      for (const person in DATA.people) {{
        if (selected.has(person) && DATA.people[person].includes(dateStr)) {{
          unavailable.push(person);
        }}
      }}
      unavailable.sort();
      const keyMissing = unavailable.filter(p => DATA.keyPeople.includes(p));
      if (DATA.pastDates.includes(dateStr)) {{
        return {{ status: 'bad', unavailable }};
      }}
      if (keyMissing.length > 0 && unavailable.length > DATA.maxMissingForOk) {{
        return {{ status: 'bad', unavailable }};
      }}
      if (unavailable.length > 0) return {{ status: 'ok', unavailable }};
      return {{ status: 'perfect', unavailable: [] }};
    }}

    function updateCalendar() {{
      document.querySelectorAll('.day-cell[data-date]').forEach(cell => {{
        const dateStr = cell.dataset.date;
        const {{ status, unavailable }} = computeStatus(dateStr);

        cell.classList.remove('perfect', 'ok', 'bad');
        cell.classList.add(status);

        const noteEl = cell.querySelector('.note');
        if (!noteEl) return;

        noteEl.classList.remove('note-ok', 'note-bad');
        if (status === 'perfect') {{
          noteEl.textContent = 'Everyone available';
          noteEl.classList.add('note-ok');
        }} else {{
          noteEl.textContent = unavailable.length > 0 ? ('Missing: ' + unavailable.join(', ')) : 'Not good';
          if (status === 'bad') noteEl.classList.add('note-bad');
        }}
      }});
    }}

    const toggleBtn = document.getElementById('people-toggle');
    const panel = document.getElementById('people-panel');
    toggleBtn.addEventListener('click', () => {{
      const isOpen = panel.classList.toggle('open');
      toggleBtn.classList.toggle('open', isOpen);
    }});

    document.querySelectorAll('#people-list input[type="checkbox"]').forEach(box => {{
      box.addEventListener('change', () => {{
        if (box.checked) {{
          selected.add(box.value);
        }} else {{
          selected.delete(box.value);
        }}
        updateCalendar();
      }});
    }});

    document.getElementById('select-all').addEventListener('click', () => {{
      document.querySelectorAll('#people-list input[type="checkbox"]').forEach(box => {{
        box.checked = true;
        selected.add(box.value);
      }});
      updateCalendar();
    }});

    document.getElementById('select-none').addEventListener('click', () => {{
      document.querySelectorAll('#people-list input[type="checkbox"]').forEach(box => {{
        box.checked = false;
        selected.delete(box.value);
      }});
      updateCalendar();
    }});
  </script>
</body>
</html>
"""


class CalendarHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        html = render_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


class ReusableHTTPServer(HTTPServer):
    # Allows the server to restart quickly on the same port without
    # hitting the "Address already in use" error.
    allow_reuse_address = True


def run_server(port: int = 8000) -> None:
    server = ReusableHTTPServer(("127.0.0.1", port), CalendarHandler)
    print(f"Server started at http://127.0.0.1:{port}")
    print("Press CTRL+C to stop")
    server.serve_forever()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
