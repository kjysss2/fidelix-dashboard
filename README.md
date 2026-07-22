# Fidelix Memory Radar

피델릭스와 Winbond, Nanya, Macronix, Dosilicon, 제주반도체의 실적·공시 일정을 추적하는 로컬 웹 대시보드입니다.

## 실행

PowerShell에서 다음 파일을 실행합니다.

```powershell
.\start.ps1
```

브라우저에서 `http://127.0.0.1:8765`를 엽니다. 외부 패키지 설치는 필요하지 않습니다.

## 자동 갱신 범위

- Winbond·Nanya·Macronix: 대만거래소 OpenAPI 최신 월매출 + MOPS 최근 36개월 월매출 그래프(키 불필요)
- Dosilicon: 상하이거래소 최근 공시 목록(키 불필요)
- 피델릭스·제주반도체: OpenDART 분기 재무와 공시(OpenDART 키 필요)
- GDS·VNET: 공식 IR 발표자료 기준 중국 IDC 신규수주(MW)와 백로그/확약용량
- 제주반도체 수출입 데이터: 사용자 제공 표 기준 월별 수출액·단가, 분기 수출액·매출액·OPM 결합 그래프

6개사 모두 최근 12개 분기의 매출·영업이익·순이익 막대와 영업이익률·순이익률 점선을 제공합니다. 4분기 값은 연간 누적 실적에서 1~3분기를 차감해 단일 분기로 환산합니다.

## OpenDART 연결

1. [OpenDART](https://opendart.fss.or.kr/)에서 인증키를 발급합니다.
2. `.env.example`을 `.env`로 복사합니다.
3. `.env`의 `DART_API_KEY=` 뒤에 키를 입력한 후 서비스를 다시 시작합니다.

인증키는 브라우저로 전달하지 않고 서버 프로세스에서만 사용합니다. 기본 갱신 시각은 매일 오전 8시(KST)이며 `.env`의 `REFRESH_AT`으로 변경할 수 있습니다.

`http://127.0.0.1:8765`는 이 PC에서만 열리는 로컬 주소입니다. 외부 접속에는 별도 HTTPS 배포 또는 인증이 적용된 보안 터널이 필요합니다.

## 상시 운영과 MYBOX

네이버 MYBOX는 파일 저장·동기화용 공간이라 Python 웹서버를 24시간 실행할 수 없습니다. 프로젝트 파일을 백업하거나 다른 PC로 옮기는 용도로는 쓸 수 있지만, 대시보드를 항상 켜두는 호스팅 용도로는 맞지 않습니다.

상시 운영 선택지는 다음 중 하나입니다.

- 현재 PC를 계속 켜두고 Windows 작업 스케줄러로 `start-public.ps1`을 자동 실행
- Cloudflare 계정 기반 Named Tunnel로 고정 주소와 접근제어 적용
- Naver Cloud Platform, AWS Lightsail, Oracle Cloud 같은 저가 서버에 배포

## NAVER Cloud Platform 배포

PC를 꺼도 홈페이지가 계속 열리게 하려면 NAVER Cloud Platform의 Ubuntu 서버에 올립니다.

배포 파일은 `deploy/naver-cloud/`에 있습니다.

1. NAVER Cloud Platform에서 Ubuntu 서버를 생성하고 공인 IP를 붙입니다.
2. ACG/방화벽에서 TCP 80과 SSH용 TCP 22를 엽니다. SSH 22번은 내 PC IP만 허용하는 편이 안전합니다.
3. PowerShell에서 아래 명령을 실행합니다.

```powershell
.\deploy\naver-cloud\deploy.ps1 -HostName "서버공인IP" -User "root"
```

배포가 끝나면 `http://서버공인IP/`로 접속합니다. 서버 안에서는 `systemd`가 대시보드를 자동 실행하고, `nginx`가 80번 포트로 공개합니다.

GDS/VNET 공식 IR 자동 연결은 일단 꺼두었습니다. 나중에 `/opt/fidelix-dashboard/.env`에서 `ENABLE_CHINA_IDC=1`로 바꾸면 다시 켤 수 있습니다.

## GitHub Pages 무료 배포

GitHub Pages는 Python 서버를 24시간 켜두는 방식이 아니라, 정적 홈페이지를 무료로 공개하고 GitHub Actions가 데이터를 주기적으로 갱신하는 방식입니다.

이 프로젝트는 GitHub Pages용 빌드를 지원합니다.

- 사이트 파일 생성: `python build_pages.py`
- 배포 워크플로: `.github/workflows/pages.yml`
- 자동 갱신 시각: 매일 08:05 KST 근처
- 공개 URL 예시: `https://kjysss2.github.io/fidelix-dashboard/`

처음 올린 뒤 GitHub에서 해야 할 일:

1. Repository `Settings → Pages`에서 Source를 `GitHub Actions`로 설정합니다.
2. `Settings → Secrets and variables → Actions`에서 `DART_API_KEY` Secret을 추가합니다.
3. `Actions → Build and deploy GitHub Pages → Run workflow`를 한 번 수동 실행합니다.

GDS/VNET 공식 IR 자동 연결은 현재 `ENABLE_CHINA_IDC=0`으로 꺼져 있습니다. GitHub Actions에서 다시 켜려면 `.github/workflows/pages.yml`의 `ENABLE_CHINA_IDC` 값을 `"1"`로 바꾸면 됩니다.

## 임시 외부 공개 URL

`start-public.ps1`을 실행하면 Cloudflare Quick Tunnel의 임시 HTTPS 주소가 만들어지고 `public-url.txt`에 기록됩니다. 주소를 알고 있는 사람은 접속할 수 있으므로 공개 범위에 주의해야 합니다. PC와 서버·터널 프로세스가 켜져 있어야 하며 재시작 시 주소가 바뀝니다. 고정 주소와 로그인 보호가 필요하면 Cloudflare 계정 기반 Named Tunnel 또는 별도 클라우드 배포를 사용해야 합니다.

## API

- `GET /api/dashboard` 현재 대시보드 데이터
- `POST /api/refresh` 수동 갱신 시작
- `GET /api/health` 서비스 상태

`data/cache.json`은 첫 갱신 이후 자동 생성됩니다.
