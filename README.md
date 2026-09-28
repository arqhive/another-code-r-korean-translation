# 어나더 코드 R 기억의 문 (Wii) 한글 패치

*Another Code: R — A Journey into Lost Memories* (Wii, 유럽판 `RNOP01`) 비공식 한국어 팬 패치입니다.
대사는 일본어판(『アナザーコード：R 記憶の扉』) 원문을 기준으로 번역했고, 유럽판 디스크에 넣었습니다.

**제작: arqhive** · **상태: 시험판(배포 전)**

- 대사 전체를 한글화했습니다(본편, 조사·상호작용 대사, 줄거리, 퍼즐).
- 인물·아이템 설명, DAS 메일, 기억 퀴즈, 세이브·오류 메시지, 장 이름, 장소 이름을 한글화했습니다.
- 타이틀 로고, 장소 이름 띠, 지도, 인물 소개 카드, 대화창 이름표, DAS 메뉴, 장 제목, 오프닝 날짜·장소 자막, 엔딩 이름, 리모컨 스트랩 경고 화면, 세이브 배너 등 그림 글씨를 한글화했습니다.
- 게임 폰트 4벌에 한글 2,350자를 넣었습니다(맑은 고딕, 흰 글씨·검은 테두리).
- 본체 언어 설정과 관계없이 한국어로 나옵니다.
- **파일 단위 패처**라서 덤프 형태(정본 ISO, WBFS, WBFS에서 변환한 ISO, 업데이트 파티션을 뺀 덤프)가 달라도 게임 파일만 같으면 적용됩니다.

> 이 저장소에는 **게임 데이터(롬·디스크 이미지, 추출한 원문 대사, 원본 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 만들거나 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 유럽판 디스크 이미지(`RNOP01`). 일본판·북미판에는 적용할 수 없습니다.
- Windows 10 이상. 패처에 필요한 도구(wit, xdelta3)가 함께 들어 있어 따로 설치할 것은 없습니다.
- 빈 공간 약 10GB.

### 지원 형식

| 원본 | 결과 |
|---|---|
| ISO (정본 덤프, WBFS에서 변환한 ISO) | ISO |
| WBFS | WBFS |
| CISO, WIA, WDF | ISO |
| RVZ | 지원 안 함. Dolphin에서 ISO로 변환한 뒤 적용 |
| NKit | 지원 안 함. 원본 ISO로 복원한 뒤 적용 |

### 적용 방법

1. 배포 페이지에서 `AnotherCodeR_KO_v<버전>.zip`을 받아 압축을 풉니다.
2. 원본 이미지를 `패치하기.bat` 위에 끌어다 놓습니다. 원본을 같은 폴더에 두고 더블클릭해도 됩니다.
3. "완료"가 나오면 원본과 같은 폴더에 `Another Code R (Korean) [RNOP01].iso`(WBFS 원본이면 `.wbfs`)가 생깁니다. 원본은 바뀌지 않습니다.

결과 형식을 바꾸려면 두 번째 인자로 결과 파일을 지정합니다.

```
powershell -ExecutionPolicy Bypass -File patch.ps1 "원본.iso" "결과.wbfs"
```

유럽판이지만 60Hz(EuRGB60)로 실행됩니다. 영상도 29.97fps로 일본판과 같습니다.
그래서 UWUVCI로 Wii U에 주입할 때는 영상 모드 패치(PAL to NTSC)를 **끄세요**. 켜면 업데이트 파티션이 없는 이미지에서 `wii-vmc.exe` 경로 오류로 주입이 실패합니다.

### 실행 환경

- **확인함**: Dolphin, Wii U vWii(UWUVCI 주입, 60Hz).

### 알려진 문제

- 영상에 박혀 있는 영어(엔딩의 헌사 문구 등)는 그대로입니다. 영상을 다시 인코딩하지 않았습니다.
- 장 제목의 "Chapter 1" 같은 장 번호 글씨는 영어 그대로 두었습니다.
- 퍼즐의 얼굴 인증 화면에서 한 줄짜리 문구가 상자 아래쪽에 걸쳐 나옵니다. 읽는 데는 문제가 없습니다.

## 개발자용: 직접 빌드

### 요구 사항

- Python 3.11 이상. `pip install -r requirements.txt`로 numpy, Pillow를 설치합니다. `kiwipiepy`는 마침표 검수 도구(`tools/period_check.py`)에만 필요합니다.
- **유럽판 ISO와 일본판 ISO 둘 다.** 패치는 유럽판에 넣지만, 빌드할 때 일본판의 레이아웃 묶음·메시지 구조·문자열 위치를 참조합니다.
  저장소 루트(또는 바로 아래 폴더)에 `Another Code - R [RNOP01].iso`, `Another Code - R [RNOJ01].iso`로 두거나 환경 변수 `ACR_EU_ISO`, `ACR_JP_ISO`로 지정합니다.
- 맑은 고딕(`C:/Windows/Fonts/malgunbd.ttf`). 한글 폰트와 이름표를 그리는 데 씁니다.
- [wit](https://wit.wiimm.de/)(Wiimms ISO Tools). 추출과 원본 배치 유지 ISO 조립에 씁니다. `tools/bin/wit-v3.05a-r8638-cygwin64/`에 두거나 PATH, 환경 변수 `WIT`로 지정합니다.
- xdelta3. 배포용 패처를 만들 때만 필요하며, `tools/bin/xdelta3.exe`나 PATH, 환경 변수 `XDELTA3`로 둡니다.

### 빌드

```bash
# 한글 ISO 만들기 (work/AnotherCodeR_KO.iso, 원본 배치 유지)
python tools/build.py

# 배포용 패처 만들기 (release/AnotherCodeR_KO_v0.1/ 과 .zip)
python tools/make_patcher.py 0.1
```

처음 실행하면 두 ISO를 `work/eu`, `work/jp`에 추출합니다. 폰트 4벌, 대사 파일 83개, 이미지(레이아웃 묶음 약 200개), 대화창 이름표, 기타 텍스트 11개, `main.dol` 패치를 `work/build`에 만듭니다.
- `build.py`는 원본 배치를 유지한 ISO를 조립하고, 결과 ISO의 파일 7,054개를 모두 빌드 결과·원본과 비교해 검증합니다.
- `make_patcher.py`는 바뀐 파일 303개마다 유럽판 원본과의 xdelta 차분을 만들고, [`patcher/`](patcher)의 `패치하기.bat`·`patch.ps1`, wit, xdelta3, [`release/README_한국어.txt`](release/README_한국어.txt)와 함께 zip으로 묶습니다.
  배포 전에는 zip을 푼 사본으로 원본 ISO와 WBFS에 적용해 보고, 결과를 추출해 모든 파일을 비교합니다.
Windows Git Bash에서는 `PYTHONIOENCODING=utf-8`을 붙이세요.

### 번역 수정

- 번역: [`translation/ko/*.json`](translation/ko)의 `ko` 값을 고친 뒤 빌드합니다. 파일 하나가 게임 텍스트 파일 하나입니다.
  - 대사 파일(`*.BMG.json`): 메시지 번호(`id`) → 대화창(`boxes`)마다 화자(`speaker`, 게임 내부 키라 일본어 그대로)와 한국어.
  - 그 밖(`*.MESS.json` 등): 일본판 파일 안 위치(`offset`/`block`/`part`/`record`)와 한국어.
- 원문 대조: `python tools/export_text.py`를 실행하면 일본어 원문·루비·번역을 나란히 담은 대조본이 `work/text_full/`에 만들어집니다. 대조본의 `ko`를 고친 뒤 `python tools/ko_import.py`로 되돌려 넣을 수 있습니다.
- 마침표 검수: `python tools/period_check.py`가 종결어미로 끝났는데 마침표가 없는 곳을 `work/period_candidates.csv`로 뽑습니다.
- 표기·말투 원칙은 [`translation/GLOSSARY.md`](translation/GLOSSARY.md)를 참고하세요.
- 그림 글씨: [`tools/assets/`](tools/assets)의 PNG를 원본과 같은 크기로 고친 뒤 빌드합니다. 대화창 이름표는 [`tools/data/nameplates.json`](tools/data/nameplates.json)의 이름으로 도구가 직접 그립니다.

`translation/ko/*.json`에는 **번역문과 위치 키만** 들어 있습니다. 일본어 원문은 게임 데이터라 넣지 않았습니다.

### 폴더 구조

```
tools/             빌드·원문 대조 도구 (paths.py가 기준 경로를 잡음)
  assets/jp/       일본판 그림에 대응하는 한글화 이미지(분류별)와 대응 목록
  assets/eu_only/  유럽판에만 있는 그림(장 제목, 엔딩 이름, 오프닝 자막 등)의 한글화 이미지
  data/            대화창 이름표 이름
  bin/             (git 제외) wit, xdelta3
patcher/           사용자용 파일 단위 패처(패치하기.bat, patch.ps1)
release/           패처 설명서(README_한국어.txt), 패처 폴더·zip은 git 제외
translation/
  ko/              번역 JSON (위치 키, 화자, 한국어)
  GLOSSARY.md      인물·장소·표기 원칙
docs/
  TECHNICAL.md     파일 포맷과 한글화 방식
work/              (git 제외) 추출본·빌드 결과·원문 대조본
```

### 기술 문서

파일 포맷, 유럽판에 일본판 번역을 넣는 방식, 원본 배치 유지 ISO 조립, 크래시 원인과 해결은 [`docs/TECHNICAL.md`](docs/TECHNICAL.md)에 정리했습니다.

## 변경 내역

전체 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있습니다.

## 크레딧·라이선스

- 이 저장소의 도구 코드, 한국어 번역문, 문서: [MIT License](LICENSE) (© 2026 arqhive).
- `tools/inplace.py`, `tools/wiidisc.py`는 같은 제작자의 「돌격!! 패미컴 워즈 VS」·「죄와 벌 우주의 후계자」 한글 패치 도구를, `tools/gxtex.py`는 「디재스터 데이 오브 크라이시스」 한글 패치 도구를 바탕으로 했습니다.

## 면책

비공식 팬 번역이며 Nintendo와 관련이 없습니다. 「어나더 코드 R 기억의 문」 관련 상표·저작권은 Nintendo와 CING에 있습니다.
패치를 적용한 게임 파일의 배포를 금지합니다.
