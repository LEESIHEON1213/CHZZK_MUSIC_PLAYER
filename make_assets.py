"""
make_assets.py — 니나마무 플레이어 GitHub 꾸미기 에셋 생성기
실행: python make_assets.py
결과: assets/ 폴더에 SVG 파일들 생성
"""

from pathlib import Path

ASSETS = Path("assets")
ASSETS.mkdir(exist_ok=True)

# ──────────────────────────────────────────
# 1. 로고 SVG
# ──────────────────────────────────────────
logo_svg = '''\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="120" height="120">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ff9a30"/>
      <stop offset="100%" stop-color="#c45000"/>
    </radialGradient>
    <filter id="shadow">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#00000060"/>
    </filter>
  </defs>
  <!-- 배경 원 -->
  <circle cx="60" cy="60" r="56" fill="url(#bg)" filter="url(#shadow)"/>
  <!-- 음표 -->
  <g fill="white" opacity="0.95">
    <!-- 음표 머리 1 -->
    <ellipse cx="44" cy="74" rx="11" ry="8" transform="rotate(-15,44,74)"/>
    <!-- 음표 줄기 1 -->
    <rect x="53" y="38" width="4" height="38" rx="2"/>
    <!-- 음표 머리 2 -->
    <ellipse cx="72" cy="68" rx="11" ry="8" transform="rotate(-15,72,68)"/>
    <!-- 음표 줄기 2 -->
    <rect x="81" y="32" width="4" height="38" rx="2"/>
    <!-- 연결 빔 -->
    <rect x="53" y="38" width="32" height="5" rx="2.5"/>
  </g>
</svg>
'''

# ──────────────────────────────────────────
# 2. 소셜 프리뷰 배너 SVG (1280×640)
#    GitHub 레포 → Settings → Social preview 에 업로드
# ──────────────────────────────────────────
banner_svg = '''\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 640" width="1280" height="640">
  <defs>
    <linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d0f14"/>
      <stop offset="100%" stop-color="#1a1200"/>
    </linearGradient>
    <radialGradient id="glow" cx="38%" cy="50%" r="45%">
      <stop offset="0%" stop-color="#f07800" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#f07800" stop-opacity="0"/>
    </radialGradient>
    <!-- 음파 클리핑 -->
    <clipPath id="clip"><rect width="1280" height="640"/></clipPath>
  </defs>

  <!-- 배경 -->
  <rect width="1280" height="640" fill="url(#grad)"/>
  <rect width="1280" height="640" fill="url(#glow)"/>

  <!-- 장식용 원형 링 -->
  <circle cx="960" cy="320" r="260" fill="none" stroke="#f07800" stroke-width="1" opacity="0.12"/>
  <circle cx="960" cy="320" r="200" fill="none" stroke="#f07800" stroke-width="1" opacity="0.10"/>
  <circle cx="960" cy="320" r="140" fill="none" stroke="#f07800" stroke-width="1.5" opacity="0.14"/>

  <!-- 음파 바 (오른쪽 장식) -->
  <g clip-path="url(#clip)" opacity="0.22">
    <rect x="820" y="220" width="14" height="200" rx="7" fill="#f07800"/>
    <rect x="850" y="170" width="14" height="300" rx="7" fill="#f5a830"/>
    <rect x="880" y="240" width="14" height="160" rx="7" fill="#f07800"/>
    <rect x="910" y="200" width="14" height="240" rx="7" fill="#f5a830"/>
    <rect x="940" y="255" width="14" height="130" rx="7" fill="#f07800"/>
    <rect x="970" y="185" width="14" height="270" rx="7" fill="#f5a830"/>
    <rect x="1000" y="235" width="14" height="170" rx="7" fill="#f07800"/>
    <rect x="1030" y="210" width="14" height="220" rx="7" fill="#f5a830"/>
    <rect x="1060" y="260" width="14" height="120" rx="7" fill="#f07800"/>
    <rect x="1090" y="195" width="14" height="250" rx="7" fill="#f5a830"/>
    <rect x="1120" y="240" width="14" height="160" rx="7" fill="#f07800"/>
    <rect x="1150" y="215" width="14" height="210" rx="7" fill="#f5a830"/>
    <rect x="1180" y="270" width="14" height="100" rx="7" fill="#f07800"/>
    <rect x="1210" y="200" width="14" height="240" rx="7" fill="#f5a830"/>
    <rect x="1240" y="250" width="14" height="140" rx="7" fill="#f07800"/>
  </g>

  <!-- 로고 원 -->
  <circle cx="148" cy="290" r="72" fill="#f07800" opacity="0.95"/>
  <g fill="white" opacity="0.95">
    <ellipse cx="133" cy="310" rx="16" ry="11" transform="rotate(-15,133,310)"/>
    <rect x="147" y="268" width="6" height="44" rx="3"/>
    <ellipse cx="163" cy="302" rx="16" ry="11" transform="rotate(-15,163,302)"/>
    <rect x="177" y="260" width="6" height="44" rx="3"/>
    <rect x="147" y="268" width="36" height="7" rx="3.5"/>
  </g>

  <!-- 타이틀 텍스트 -->
  <text x="248" y="278" font-family="'Segoe UI', 'Malgun Gothic', sans-serif"
        font-size="62" font-weight="800" fill="white" opacity="0.97"
        letter-spacing="-1">니나마무's 플레이어</text>

  <!-- 서브타이틀 -->
  <text x="250" y="330" font-family="'Segoe UI', 'Malgun Gothic', sans-serif"
        font-size="26" fill="#f5a830" opacity="0.9" letter-spacing="1">
    치지직 스트리머를 위한 유튜브 뮤직 플레이어
  </text>

  <!-- 태그 뱃지들 -->
  <g font-family="'Segoe UI', monospace" font-size="18" fill="white">
    <!-- yt-dlp -->
    <rect x="250" y="368" width="110" height="34" rx="6" fill="#f07800" opacity="0.9"/>
    <text x="305" y="390" text-anchor="middle" fill="white" font-weight="600">yt-dlp</text>
    <!-- PyQt6 -->
    <rect x="372" y="368" width="110" height="34" rx="6" fill="#2a2a3a" stroke="#f07800" stroke-width="1.2" opacity="0.9"/>
    <text x="427" y="390" text-anchor="middle">PyQt6</text>
    <!-- OBS -->
    <rect x="494" y="368" width="130" height="34" rx="6" fill="#2a2a3a" stroke="#f07800" stroke-width="1.2" opacity="0.9"/>
    <text x="559" y="390" text-anchor="middle">OBS 지원</text>
    <!-- ffmpeg -->
    <rect x="636" y="368" width="120" height="34" rx="6" fill="#2a2a3a" stroke="#f07800" stroke-width="1.2" opacity="0.9"/>
    <text x="696" y="390" text-anchor="middle">ffmpeg</text>
  </g>

  <!-- 하단 URL -->
  <text x="250" y="450" font-family="'Segoe UI', monospace" font-size="20"
        fill="#f07800" opacity="0.55" letter-spacing="1">
    github.com/YOUR_ID/YOUR_REPO
  </text>
</svg>
'''

# ──────────────────────────────────────────
# 3. 기능 배지 아이콘들 (README 인라인용)
#    feature_*.svg — 각 기능을 나타내는 소형 아이콘
# ──────────────────────────────────────────
def feature_badge(icon_path: str, label: str, color: str) -> str:
    """아이콘+텍스트 조합 뱃지 SVG 반환"""
    w = 10 + len(label) * 9 + 36
    return f'''\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 28" width="{w}" height="28">
  <rect width="{w}" height="28" rx="6" fill="#1a1a1a"/>
  <rect width="28" height="28" rx="6" fill="{color}"/>
  <text x="14" y="19" text-anchor="middle"
        font-family="'Segoe UI Emoji', sans-serif" font-size="14">{icon_path}</text>
  <text x="{28 + (w-28)//2}" y="19" text-anchor="middle"
        font-family="'Segoe UI', sans-serif" font-size="12"
        fill="white" font-weight="500">{label}</text>
</svg>'''

# ──────────────────────────────────────────
# 저장
# ──────────────────────────────────────────
(ASSETS / "logo.svg").write_text(logo_svg, encoding="utf-8")
print("✓ assets/logo.svg")

(ASSETS / "banner.svg").write_text(banner_svg, encoding="utf-8")
print("✓ assets/banner.svg  ← GitHub Social Preview 용 (Settings에서 업로드)")

badges = [
    ("search",    "🔍", "검색·재생",   "#f07800"),
    ("queue",     "📋", "재생 큐",     "#3b7dd8"),
    ("favorite",  "⭐", "즐겨찾기",    "#f5a830"),
    ("theme",     "🎨", "8가지 테마",  "#a855f7"),
    ("obs",       "📺", "OBS 지원",   "#22c55e"),
    ("update",    "🔧", "자동 업데이트","#64748b"),
]
for name, icon, label, color in badges:
    path = ASSETS / f"badge_{name}.svg"
    path.write_text(feature_badge(icon, label, color), encoding="utf-8")
    print(f"✓ assets/badge_{name}.svg")

print()
print("=" * 52)
print("  다음 단계:")
print("  1. assets/screenshot.png  — 앱 스크린샷 추가")
print("  2. assets/demo.gif        — 검색→재생 데모 GIF 추가")
print("  3. assets/banner.svg → PNG 변환 후 GitHub")
print("     Settings → Social preview 에 업로드")
print("  4. README.md 의 YOUR_ID/YOUR_REPO 를 실제 값으로 교체")
print("=" * 52)
