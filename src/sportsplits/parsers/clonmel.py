"""Parsers for the Clonmel Camida 2026 plain-text result files.

Two layouts ship from the same event and share the Age_Group token vocabulary but
differ in column order and time precision, so each gets its own line parser:

* ``load_final`` — final results: ``Place. Firstname Lastname AgeGroup Grp_Rk Bib
  Club Class Finish Swim T1 Bike T2 Run``. Times are always HH:MM:SS; Finish is the
  first time on the line, splits follow.
* ``load_draft`` — earlier draft layout: ``Place. Bib Name AgeGroup [Grp_Rk] Class
  Club Swim T1 Bike T2 Run Finish``. Times may be M:SS or HH:MM:SS.

Both return a DataFrame in the standard 13-column format (data_format.md).
"""
import re
import pandas as pd

# Age-group vocabulary is common to both layouts.
GROUP_RE = re.compile(r'(From \d+ to \d+|OverAll|TBC|Relay Team)')


# ── Final results ─────────────────────────────────────────────────────────────
_FINAL_TIME_RE = re.compile(r'\d{2}:\d{2}:\d{2}')


def _to_timedelta_hms(t: str | None) -> pd.Timedelta:
    if not t:
        return pd.NaT
    h, m, s = t.split(':')
    return pd.Timedelta(hours=int(h), minutes=int(m), seconds=int(s))


def _parse_final_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None

    first_time = _FINAL_TIME_RE.search(line)
    if not first_time:
        return None

    pre = line[:first_time.start()].strip()
    times = _FINAL_TIME_RE.findall(line[first_time.start():])

    # Place number
    m = re.match(r'^(\d+)\.\s+(.*)', pre)
    if not m:
        return None
    place = int(m.group(1))
    rest = m.group(2).strip()

    # Age group token
    gm = GROUP_RE.search(rest)
    if gm:
        # Name = everything before age group (two tokens: Firstname Lastname)
        name = rest[:gm.start()].strip()
        age_group = gm.group(1)
        after_grp = rest[gm.end():].strip()
    else:
        name, age_group, after_grp = rest, '', ''

    # after_grp: Grp_Rk Bib Club Class  (Club may be absent)
    # Relay lines have extra RELAY token: "1 RELAY 1 339 RELAY" → grp_rank=1, bib=339, cls=RELAY
    relay_m = re.match(r'^(\d+)\s+RELAY\s+\d+\s+(\d+)\s+RELAY\s*$', after_grp)
    if relay_m:
        grp_rank = int(relay_m.group(1))
        bib      = int(relay_m.group(2))
        club, cls = '', 'RELAY'
    else:
        am = re.match(r'^(\d+)\s+(\d+)\s+(.*?)\s*(Open|Female|RELAY)\s*$', after_grp)
        if am:
            grp_rank = int(am.group(1))
            bib      = int(am.group(2))
            club     = am.group(3).strip()
            cls      = am.group(4)
        else:
            am2 = re.match(r'^(\d+)\s+(\d+)\s*(Open|Female|RELAY)\s*$', after_grp)
            if am2:
                grp_rank = int(am2.group(1))
                bib      = int(am2.group(2))
                club     = ''
                cls      = am2.group(3)
            else:
                grp_rank, bib, club, cls = None, 0, '', after_grp

    # Time order in file: Finish, Swim, T1, Bike, T2, Run
    if len(times) >= 6:
        finish, swim, t1, bike, t2, run = times[:6]
    elif len(times) == 1:
        finish = times[0]
        swim = t1 = bike = t2 = run = None
    else:
        finish = times[0] if times else None
        swim = times[1] if len(times) > 1 else None
        t1   = times[2] if len(times) > 2 else None
        bike = times[3] if len(times) > 3 else None
        t2   = times[4] if len(times) > 4 else None
        run  = times[5] if len(times) > 5 else None

    return {
        'Place':      place,
        'Bib':        bib,
        'Name':       name,
        'Age_Group':  age_group,
        'Group_Rank': grp_rank,
        'Class':      cls,
        'Club':       club,
        'Swim':       _to_timedelta_hms(swim),
        'T1':         _to_timedelta_hms(t1),
        'Bike':       _to_timedelta_hms(bike),
        'T2':         _to_timedelta_hms(t2),
        'Run':        _to_timedelta_hms(run),
        'Finish':     _to_timedelta_hms(finish),
    }


def load_final(path: str) -> pd.DataFrame:
    """Parse the Clonmel Camida 2026 final results file."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    records = [_parse_final_line(line) for line in lines[1:]]
    records = [r for r in records if r is not None]
    return pd.DataFrame(records)


# ── Draft results ─────────────────────────────────────────────────────────────
_DRAFT_TIME_RE = re.compile(r'\d{1,2}:\d{2}(?::\d{2})?')


def _to_timedelta_flex(t: str | None) -> pd.Timedelta:
    if not t:
        return pd.NaT
    parts = t.split(':')
    if len(parts) == 2:
        return pd.Timedelta(minutes=int(parts[0]), seconds=int(parts[1]))
    return pd.Timedelta(hours=int(parts[0]), minutes=int(parts[1]), seconds=int(parts[2]))


def _parse_draft_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None

    first_time = _DRAFT_TIME_RE.search(line)
    if not first_time:
        return None

    non_time = line[:first_time.start()].strip()
    times = _DRAFT_TIME_RE.findall(line[first_time.start():])

    m = re.match(r'^(\d+)\.\s+(\d+)\s+(.*)', non_time)
    if not m:
        return None
    place = int(m.group(1))
    bib   = int(m.group(2))
    rest  = m.group(3).strip()

    gm = GROUP_RE.search(rest)
    if gm:
        name       = rest[:gm.start()].strip()
        age_group  = gm.group(1)
        after_grp  = rest[gm.end():].strip()
    else:
        name, age_group, after_grp = rest, '', ''

    am = re.match(r'^(\d+\s+)?(Open|Female|RELAY)\s*(.*)', after_grp)
    if am:
        raw_rank  = am.group(1)
        grp_rank  = int(raw_rank.strip()) if raw_rank else None
        cls       = am.group(2)
        club      = am.group(3).strip()
    else:
        grp_rank, cls, club = None, after_grp, ''

    if len(times) >= 6:
        swim, t1, bike, t2, run, finish = times[:6]
    elif len(times) == 2:
        swim = t1 = bike = t2 = run = None
        finish = times[-1]
    else:
        split_keys = ['swim', 't1', 'bike', 't2', 'run', 'finish']
        vals = dict(zip(split_keys, times))
        swim   = vals.get('swim')
        t1     = vals.get('t1')
        bike   = vals.get('bike')
        t2     = vals.get('t2')
        run    = vals.get('run')
        finish = vals.get('finish')

    return {
        'Place':      place,
        'Bib':        bib,
        'Name':       name,
        'Age_Group':  age_group,
        'Group_Rank': grp_rank,
        'Class':      cls,
        'Club':       club,
        'Swim':       _to_timedelta_flex(swim),
        'T1':         _to_timedelta_flex(t1),
        'Bike':       _to_timedelta_flex(bike),
        'T2':         _to_timedelta_flex(t2),
        'Run':        _to_timedelta_flex(run),
        'Finish':     _to_timedelta_flex(finish),
    }


def load_draft(path: str) -> pd.DataFrame:
    """Parse the Clonmel Camida 2026 draft results file."""
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    records = [_parse_draft_line(line) for line in lines[1:]]
    records = [r for r in records if r is not None]
    return pd.DataFrame(records)
