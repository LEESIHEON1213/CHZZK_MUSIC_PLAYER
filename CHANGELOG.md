# 니나마무's 플레이어 v3 변경사항

## 핵심 변경

### ffplay → mpv (python-mpv)
- **seek**: 즉시 반영 (기존: 재생 재시작 필요 → 자주 망가짐)
- **볼륨**: 실시간 반영 (기존: pycaw 타이밍 이슈)
- **재생 딜레이**: 최소화 (mpv가 스트리밍 직접 처리)

## 설치

```bash
pip install -r requirements.txt
python main.py
```

> 첫 실행 시 yt-dlp + mpv(libmpv-2.dll) 자동 다운로드

## requirements

```
PyQt6>=6.6.0
python-mpv>=1.0.7
```

## mpv 수동 설치 (자동 다운로드 실패 시)

1. https://mpv.io/installation/ 에서 Windows 빌드 다운로드
2. `mpv.exe` → `cache/` 폴더에
3. `libmpv-2.dll` → exe와 같은 폴더에
