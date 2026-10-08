"""Windows: 실제 OCR에 필요한 'Microsoft Visual C++ 재배포 가능 패키지'가 있는지 확인.

PaddleOCR가 쓰는 파일 중 두 개가 이 패키지(Windows에 따로 설치)에 있는 DLL을 쓴다.
파이썬(python.org)에도, pip로 받는 설치 파일(wheel)에도 안 들어 있다 (2026-10-08 Windows wheel의 DLL 의존성 확인):
- pyclipper(_pyclipper.cp313-win_amd64.pyd) → msvcp140.dll
- paddlepaddle(paddle/libs/mkldnn.dll)    → vcomp140.dll
없으면 import가 "DLL load failed while importing _pyclipper: 지정된 모듈을 찾을 수 없습니다"로 실패한다
(2026-10-08 실제 발생: 팀 노트북).

    python -m app.ocr.winprereq   → 없으면 설치 안내를 찍고 종료 코드 1 (npm run setup:ocr 가 설치 전에 부름)
"""

import sys

# Microsoft 공식 상시 링크 (Visual C++ v14, x64). https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist
VC_REDIST_URL = "https://aka.ms/vc14/vc_redist.x64.exe"
REQUIRED_DLLS = ("msvcp140.dll", "vcomp140.dll")


def missing_runtime_dlls(platform: str | None = None) -> list[str]:
    """불러올 수 없는 DLL 이름 목록. Windows가 아니면 항상 빈 목록 (platform은 테스트용).

    파이썬 확장 모듈이 의존 DLL을 찾는 곳(파이썬 설치 폴더·System32·add_dll_directory)과 같은 범위에서 찾는다
    """
    if (platform or sys.platform) != "win32":
        return []
    import ctypes

    missing = []
    for name in REQUIRED_DLLS:
        try:
            ctypes.WinDLL(name)
        except OSError:
            missing.append(name)
    return missing


def install_hint(missing: list[str]) -> str:
    return (
        f"Windows에 'Microsoft Visual C++ 재배포 가능 패키지(x64)'가 없어서 실제 OCR을 켤 수 없어요 "
        f"(없는 파일: {', '.join(missing)}).\n"
        f"  → {VC_REDIST_URL} 를 받아서 설치한 뒤 다시 실행하세요 (Microsoft 공식, 무료)"
    )


def main() -> int:
    missing = missing_runtime_dlls()
    if missing:
        print(f"[오류] {install_hint(missing)}")
        return 1
    print("Microsoft Visual C++ 재배포 가능 패키지 확인 완료" if sys.platform == "win32" else "Windows가 아니라서 확인할 것 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
