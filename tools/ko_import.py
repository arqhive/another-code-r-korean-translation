"""대조본(work/text_full/*.json)의 ko 를 translation/ko 에 되돌려 넣는다(원문·루비는 빼고 번역과 위치 키만).
사용: python tools/ko_import.py [대조본 폴더]      (기본 work/text_full)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

KEEP = ('offset', 'block', 'part', 'record', 'ko')


def main(src=paths.WORK / 'text_full'):
    n = 0
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.json'): continue
        j = json.load(open(os.path.join(src, fn), encoding='utf-8'))
        if j['type'] == 'bmg':
            out = {'file': j['file'], 'type': 'bmg', 'count': j['count'],
                   'messages': [{'id': m['id'], 'boxes': [{'speaker': b['speaker'], 'ko': b.get('ko', '')} for b in m['boxes']]}
                                for m in j['messages']]}
        else:  # 번역이 없는 항목(추출 때 잘못 잡힌 가짜 항목 등)은 뺀다
            out = {'file': j['file'], 'type': j['type'],
                   'strings': sorted(({k: s[k] for k in KEEP if k in s} for s in j['strings'] if s.get('ko')), key=lambda s: s['offset'])}
        json.dump(out, open(paths.KO / fn, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); n += 1
    print('translation/ko 갱신', n)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else paths.WORK / 'text_full')
