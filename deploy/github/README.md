# GitHub 업로드

이 폴더는 Git이 설치되어 있지 않아도 GitHub API로 `kjysss2/fidelix-dashboard`에 파일을 올리는 보조 스크립트입니다.

## 필요한 것

GitHub fine-grained personal access token:

- Repository access: `kjysss2/fidelix-dashboard`
- Permissions: `Contents` → `Read and write`

## 실행

PowerShell에서:

```powershell
$env:GITHUB_TOKEN="발급한_토큰"
python .\deploy\github\upload_via_api.py
```

API 키가 들어 있는 `.env`, 캐시, 로그, `dist/`는 업로드하지 않습니다. DART 키는 GitHub 저장소의 `Settings → Secrets and variables → Actions`에서 `DART_API_KEY`로 따로 등록해야 합니다.
