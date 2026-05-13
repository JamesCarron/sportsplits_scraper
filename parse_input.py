import re
import pandas as pd

TIME_RE = re.compile(r'\d{1,2}:\d{2}(?::\d{2})?')
GROUP_RE = re.compile(r'(From \d+ to \d+|OverAll|TBC|Relay Team)')


def to_timedelta(t: str | None) -> pd.Timedelta:
    if not t:
        return pd.NaT
    parts = t.split(':')
    if len(parts) == 2:
        return pd.Timedelta(minutes=int(parts[0]), seconds=int(parts[1]))
    return pd.Timedelta(hours=int(parts[0]), minutes=int(parts[1]), seconds=int(parts[2]))


def parse_race_line(line: str) -> dict | None:
    line = line.strip()
    if not line:
        return None

    first_time = TIME_RE.search(line)
    if not first_time:
        return None

    non_time = line[:first_time.start()].strip()
    times = TIME_RE.findall(line[first_time.start():])

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
        'Swim':       to_timedelta(swim),
        'T1':         to_timedelta(t1),
        'Bike':       to_timedelta(bike),
        'T2':         to_timedelta(t2),
        'Run':        to_timedelta(run),
        'Finish':     to_timedelta(finish),
    }


def load_results(path: str = 'Clonmel.txt') -> pd.DataFrame:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    records = [parse_race_line(line) for line in lines[1:]]
    records = [r for r in records if r is not None]
    return pd.DataFrame(records)


if __name__ == '__main__':
    df = load_results()
    print(df.shape)
    print(df.head(10))
