"""Abrufkorpus v1: baut eine frische Datenbank nur über die CLI und misst `recall`.

Aufruf:
  python3 examples/retrieval/run.py VMIND_BINARY AUSGABEORDNER
  python3 examples/retrieval/run.py --self-test

Plan und Kriterien: docs/experiments/abruf-korpus-plan.md. Kein Sprachmodell beteiligt.
"""
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

CORPUS = Path(__file__).with_name('corpus.json')
LIMIT = 5  # in der CLI fest eingestellt; hier nur zur Dokumentation


def cli(binary, *args, scope=None):
    cmd = [binary, '--json', *(['--scope', scope] if scope else []), *map(str, args)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode:
        raise RuntimeError(f'{args}: {out.stderr.strip()}')
    return json.loads(out.stdout)


def build(binary, db, entries):
    """Legt alle Einträge in Dateireihenfolge an und gibt id -> key zurück."""
    cli(binary, 'init', db)
    keys = {}
    for e in entries:
        made = cli(binary, 'add', db, 'error_solution', e['problem'], e['solution'], 'Abrufkorpus v1',
                   scope=e['scope'])
        keys[made['id']] = e['key']
        if e['status'] in ('validated', 'invalidated'):
            cli(binary, 'validate', db, made['id'], 'Abrufkorpus', 'synthetischer Korpuseintrag')
        if e['status'] == 'invalidated':
            cli(binary, 'invalidate', db, made['id'], 'Abrufkorpus', e['invalidation_reason'])
    return keys


def run_queries(binary, db, queries, keys):
    rows = []
    for q in queries:
        hits = cli(binary, 'recall', db, q['text'], scope=q['scope'])
        rows.append({
            'id': q['id'], 'scope': q['scope'], 'category': q['category'], 'text': q['text'],
            'hits': [{'id': h['id'], 'key': keys.get(h['id']), 'scope': h['scope'],
                      'status': h['status'], 'invalidated': h.get('invalidated_by') is not None}
                     for h in hits],
        })
    return rows


def leaks(row, query):
    """Verstöße gegen die harten Kriterien in einer Trefferliste."""
    out = []
    for h in row['hits']:
        if h['scope'] not in (query['scope'], 'global'):
            out.append(('bereich', h['key']))
        if h['status'] != 'validated' or h['invalidated']:
            out.append(('status', h['key']))
        if h['key'] in query.get('forbidden', []):
            out.append(('verboten', h['key']))
    return out


def rank(row, key):
    keys = [h['key'] for h in row['hits']]
    return keys.index(key) + 1 if key in keys else None


def score(rows, queries):
    by_id = {q['id']: q for q in queries}
    per = defaultdict(lambda: dict(n=0, at1=0, at5=0, rr=0.0, empty=0, returned=0,
                                   before_distractor=0, distractor_n=0))
    violations = []
    for row in rows:
        q = by_id[row['id']]
        violations += [(row['id'], *v) for v in leaks(row, q)]
        positive = bool(q['expected'])
        c = per[(q['category'], 'positiv' if positive else 'negativ')]
        c['n'] += 1
        if positive:
            r = rank(row, q['expected'][0])
            c['at1'] += r == 1
            c['at5'] += r is not None
            c['rr'] += 1 / r if r else 0.0
            for d in q.get('distractors', []):
                c['distractor_n'] += 1
                rd = rank(row, d)
                c['before_distractor'] += r is not None and (rd is None or r < rd)
        else:
            c['empty'] += not row['hits']
            c['returned'] += len(row['hits'])
    summary = {}
    for (cat, kind), c in sorted(per.items()):
        s = {'fragen': c['n']}
        if kind == 'positiv':
            s.update(treffer_at1=c['at1'], treffer_at5=c['at5'], mrr=round(c['rr'] / c['n'], 3))
            if c['distractor_n']:
                s['vor_ablenker'] = c['before_distractor']
        else:
            s.update(leer=c['empty'], mittlere_treffer=round(c['returned'] / c['n'], 2))
        summary[f'{cat}/{kind}'] = s
    return summary, violations


def self_test():
    queries = [
        {'id': 'a', 'scope': 'alpha', 'category': 'k', 'expected': ['x'], 'distractors': ['y']},
        {'id': 'b', 'scope': 'alpha', 'category': 'n', 'expected': [], 'forbidden': ['z']},
    ]
    hit = lambda key, scope='alpha', status='validated', inv=False: dict(
        id=0, key=key, scope=scope, status=status, invalidated=inv)
    rows = [{'id': 'a', 'hits': [hit('y'), hit('x')]},
            {'id': 'b', 'hits': [hit('z'), hit('p', scope='beta'), hit('q', status='pending'),
                                 hit('r', inv=True), hit('g', scope='global')]}]
    summary, violations = score(rows, queries)
    assert summary['k/positiv'] == {'fragen': 1, 'treffer_at1': 0, 'treffer_at5': 1,
                                    'mrr': 0.5, 'vor_ablenker': 0}, summary
    assert summary['n/negativ'] == {'fragen': 1, 'leer': 0, 'mittlere_treffer': 5.0}, summary
    assert sorted(violations) == [('b', 'bereich', 'p'), ('b', 'status', 'q'),
                                  ('b', 'status', 'r'), ('b', 'verboten', 'z')], violations
    empty, none = score([{'id': 'a', 'hits': []}, {'id': 'b', 'hits': []}], queries)
    assert empty['k/positiv']['mrr'] == 0.0 and empty['n/negativ']['leer'] == 1 and not none
    print('Selbsttest bestanden: Rang, MRR, Ablenker, leere Listen und alle Leckarten.')


def main():
    if sys.argv[1:] == ['--self-test']:
        return self_test()
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    binary, out_dir = sys.argv[1], Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=False)
    corpus = json.loads(CORPUS.read_text(encoding='utf-8'))
    runs = []
    for attempt in (1, 2):
        with tempfile.TemporaryDirectory(prefix='vmind-abruf-') as folder:
            db = Path(folder) / 'korpus.db'
            keys = build(binary, db, corpus['entries'])
            runs.append(run_queries(binary, db, corpus['queries'], keys))
    reproducible = [[h['id'] for h in r['hits']] for r in runs[0]] == \
                   [[h['id'] for h in r['hits']] for r in runs[1]]
    summary, violations = score(runs[0], corpus['queries'])
    _, violations_2 = score(runs[1], corpus['queries'])
    result = {
        'limit': LIMIT,
        'reproduzierbar': reproducible,
        'verstoesse': violations + violations_2,
        'harte_kriterien_bestanden': reproducible and not violations and not violations_2,
        'kennzahlen': summary,
    }
    with open(out_dir / 'results.jsonl', 'w', encoding='utf-8') as f:
        for row in runs[0]:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    (out_dir / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                          encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
