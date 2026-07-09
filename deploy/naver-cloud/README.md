# 네이버 클라우드 배포 메모

이 폴더는 `Fidelix Memory Radar`를 NAVER Cloud Platform의 Ubuntu 서버에 올려 PC를 꺼도 계속 접속되게 만드는 배포 파일입니다.

## 네이버 클라우드에서 먼저 할 일

1. NAVER Cloud Platform 콘솔에서 Ubuntu 서버를 만듭니다.
2. 공인 IP를 붙입니다.
3. ACG/방화벽에서 아래 포트를 엽니다.
   - SSH: TCP 22, 내 PC IP만 허용 권장
   - 웹: TCP 80, 접속할 사람 범위만 허용
4. 서버 접속용 비밀번호 또는 SSH 키를 준비합니다.

## 내 PC에서 업로드

PowerShell에서 프로젝트 폴더로 이동 후 실행합니다.

```powershell
.\deploy\naver-cloud\deploy.ps1 -HostName "서버공인IP" -User "root"
```

현재 PC의 `.env`까지 같이 올려 DART 키를 바로 적용하려면:

```powershell
.\deploy\naver-cloud\deploy.ps1 -HostName "서버공인IP" -User "root" -IncludeEnv
```

SSH 키를 쓰는 경우:

```powershell
.\deploy\naver-cloud\deploy.ps1 -HostName "서버공인IP" -User "root" -KeyPath "C:\path\to\key.pem"
```

완료 후 `http://서버공인IP/`로 접속합니다.

## DART 키

서버의 `/opt/fidelix-dashboard/.env`에 `DART_API_KEY=` 값을 넣으면 국내 공시/실적 갱신이 작동합니다.

```bash
sudo nano /opt/fidelix-dashboard/.env
sudo systemctl restart fidelix-dashboard
```

## 운영 명령

```bash
sudo systemctl status fidelix-dashboard --no-pager
sudo systemctl restart fidelix-dashboard
sudo journalctl -u fidelix-dashboard -n 100 --no-pager
```

## 지금은 꺼둔 항목

GDS/VNET 공식 IR 자동 연결은 `ENABLE_CHINA_IDC=0`으로 꺼두었습니다. 나중에 연결할 때 `/opt/fidelix-dashboard/.env`에서 `ENABLE_CHINA_IDC=1`로 바꾸고 서비스를 재시작하면 됩니다.
