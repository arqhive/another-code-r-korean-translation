어나더 코드 R 기억의 문 한글패치 v0.1 (Wii / 유럽판 기준)
============================================================

■ 준비물
  - 유럽판 디스크 이미지 (게임 ID RNOP01)
  - Windows 10 이상 (따로 설치할 프로그램은 없습니다)
  - 빈 공간 약 10GB (풀어 둔 파일 약 5GB + 결과 이미지)

■ 지원 형식
  원본                                   결과
  ISO (정본 덤프, WBFS에서 변환한 ISO)   → ISO
  WBFS                                   → WBFS
  CISO, WIA, WDF                         → ISO
  RVZ   ×  Dolphin에서 ISO로 변환한 뒤 적용
  NKit  ×  NKit 도구로 원본 ISO로 복원한 뒤 적용

  덤프·변환 방법에 따라 MD5가 달라도 게임 파일만 같으면 적용됩니다.
  일본판·북미판에는 적용할 수 없습니다.

■ 적용 방법
  1) 압축을 풉니다.
  2) 원본 이미지(ISO 또는 WBFS)를 "패치하기.bat" 위에 끌어다 놓습니다.
     - 원본을 이 폴더에 넣고 "패치하기.bat"을 더블클릭해도 됩니다.
     - 이미지가 여러 개 있으면 경로를 물어봅니다. 파일을 창에 끌어다 놓고 Enter.
  3) "완료"가 나올 때까지 기다립니다(1~3분). 진행 중에는 창을 닫지 마세요.
  4) 원본과 같은 폴더에 결과 파일이 생깁니다. 원본은 바뀌지 않습니다.
       ISO 원본  → Another Code R (Korean) [RNOP01].iso
       WBFS 원본 → Another Code R (Korean) [RNOP01].wbfs

  ※ 결과 형식 바꾸기 (예: ISO 원본 → WBFS 결과)
     이 폴더에서 PowerShell을 열고 결과 파일 확장자를 지정합니다.
       powershell -ExecutionPolicy Bypass -File patch.ps1 "원본.iso" "결과.wbfs"

  ※ 결과 파일의 MD5는 원본에 따라 달라질 수 있습니다. 게임 내용은 같습니다.

■ 실행 방법
  - Dolphin: 결과 ISO나 WBFS를 게임 목록 폴더에 넣거나 직접 엽니다.
  - Wii·Wii U vWii (USB Loader GX): WBFS를 권합니다(FAT32 USB는 4GB 넘는 파일 불가).
      wbfs/Another Code R (Korean) [RNOP01]/RNOP01.wbfs
    처럼 넣습니다. ISO를 쓰려면 NTFS USB를 쓰세요.
  - Wii U (UWUVCI 주입): 결과 ISO를 넣고, 영상 모드 패치(PAL to NTSC)는 끕니다.

  유럽판이지만 60Hz(EuRGB60)로 실행되므로 영상 모드 패치가 필요 없습니다.

■ 오류가 날 때
  - "… (RNOP01)가 아닙니다": 일본판·북미판이거나 다른 게임입니다.
  - "원본 게임 파일이 다릅니다": 이미 패치한 이미지거나 손상된 덤프입니다.
  - "RVZ는 지원하지 않습니다": Dolphin 게임 목록에서 우클릭 → 파일 변환 → ISO.
  - "wit.exe 실행 실패": 빈 공간이 모자라거나 원본 파일이 손상됐습니다.

■ 한글화 범위
  - 대사: 본편, 조사·상호작용 대사, 줄거리, 퍼즐
  - 텍스트: 인물·아이템 설명, DAS 메일, 기억 퀴즈, 세이브·오류 메시지, 장 이름, 장소 이름
  - 그래픽: 타이틀 로고, 장소 이름 띠, 지도, 인물 소개 카드, 대화창 이름표, DAS 메뉴, 장 제목,
            오프닝 날짜·장소 자막, 엔딩 이름, 리모컨 스트랩 경고 화면, 세이브 배너
  - 본체 언어 설정과 관계없이 한국어로 나옵니다.

■ 확인 환경
  - Dolphin 에뮬레이터
  - Wii U vWii (UWUVCI 주입)

■ 알려진 문제
  - 영상에 박혀 있는 영어(엔딩의 헌사 문구 등)는 그대로입니다.
  - 장 제목의 "Chapter 1" 같은 장 번호 글씨는 영어 그대로 두었습니다.
  - 퍼즐의 얼굴 인증 화면에서 한 줄짜리 문구가 상자 아래쪽에 걸쳐 나옵니다.

■ 동봉 도구
  - wit (Wiimms ISO Tools, GPL-2.0, https://wit.wiimm.de/) — bin/wit-gpl-2.0.txt
  - xdelta3 (Apache-2.0, https://github.com/jmacd/xdelta)

■ 기타
  비공식 팬 번역이며 Nintendo와 관련이 없습니다.
  패치를 적용한 게임 파일의 배포를 금지합니다.
