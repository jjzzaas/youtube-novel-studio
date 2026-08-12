# YouTube Novel Studio

유튜브 연재형 웹소설 제작 자동화 저장소입니다.

## 원칙
- 기존 `jjzzaas/mongyeong` 비주얼노벨 저장소는 수정하지 않습니다.
- 작품 설정/원고와 제작 자동화 코드를 분리합니다.
- 1화 단위로 원고를 만들고, TTS → 자막 → 영상 렌더링까지 자동화합니다.
- 현재 1단계는 **무료 프로토타입**입니다.

## 현재 파이프라인
1. `episodes/<작품명>/epXXX.md`에 원고 저장
2. GitHub Actions 자동 실행
3. 한국어 TTS 생성
4. SRT 자막 생성
5. FFmpeg로 16:9 MP4 생성
6. 완성본을 GitHub Actions artifact로 저장

## 다음 단계
- Google Drive 설정집 자동 참조
- 화별 분량/러닝타임 자동 검수
- 작품별 성우 분리
- BGM/SFX
- YouTube 비공개 자동 업로드

## 비용
현재 저장소는 Public이므로 표준 GitHub-hosted runner의 Actions 실행은 무료입니다. TTS는 별도 API 키가 필요 없는 `edge-tts` 기반으로 시험합니다. 장기 안정성은 실제 1화 테스트 후 판단합니다.
