"""(검수용) 문장이 끝났는데 마침표가 없는 대화창·문자열을 찾는다(kiwipiepy 형태소 분석).
마지막 형태소가 종결어미(EF)일 때만 후보. 말줄임표·물결표·?·! 등으로 끝나면 제외.
결과: work/period_candidates.csv (파일, 위치, 번역 끝줄, 제안)"""
import csv, json, os, re, sys
from kiwipiepy import Kiwi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

END = re.compile(r'[.?!…」』)\]"”♪~～\-－＊*,]$')


def items():
    for fn in sorted(os.listdir(paths.KO)):
        if fn.startswith('_'): continue
        j = json.load(open(paths.KO / fn, encoding='utf-8'))
        if j['type'] == 'bmg':
            for m in j['messages']:
                for bi, b in enumerate(m['boxes']):
                    yield fn, f"{m['id']}-{bi}", b
        else:
            for s in j['strings']:
                yield fn, str(s['offset']), s


def main():
    kiwi = Kiwi(); rows = []; seen = {}
    for fn, pos, it in items():
        k = it['ko'].rstrip()
        if not k or END.search(k): continue
        last = k.split('\n')[-1]
        if last not in seen:
            toks = kiwi.tokenize(last)
            seen[last] = bool(toks) and toks[-1].tag == 'EF'
        if seen[last]:
            rows.append((fn, pos, last, last + '.'))
    with open(paths.WORK / 'period_candidates.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(['파일', '위치', '번역 끝줄', '제안']); w.writerows(rows)
    return rows, seen


if __name__ == '__main__':
    rows, seen = main()
    print('후보', len(rows), '고유 끝줄', len({r[2] for r in rows}))
    import collections
    print(collections.Counter(r[2][-1] for r in rows).most_common(20))
