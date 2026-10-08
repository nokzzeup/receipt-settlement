"""OCR + 파싱 정확도 측정 — npm run ocr:eval

    npm run ocr:eval                    # dataset/ 전부 채점
    npm run ocr:eval -- r0001 r0007     # 일부만
    npm run ocr:eval -- --refresh       # OCR부터 다시 (전처리·엔진 설정을 바꿨을 때)
    npm run ocr:eval -- -v              # 틀린 항목의 정답/인식 값까지 출력

데이터: dataset/images/<이름>.jpg|png|webp + dataset/labels/<이름>.json (형식: dataset/README.md)
OCR 결과는 마스킹해서 dataset/ocr-cache/ 에 저장해 두고 다시 쓴다 → 파서만 고쳤으면 몇 초 만에 다시 채점
(사진이 바뀌었거나 엔진 설정(ENGINE_SIGNATURE)이 바뀌면 자동으로 다시 인식)

채점 기준 (영수증 한 장마다)
- 가게명: 띄어쓰기·대소문자 무시하고 같으면 정답 (OCR이 띄어쓰기를 자주 빼먹음)
- 결제일시: 분 단위까지 같으면 정답 (화면 입력도 분 단위)
- 합계: 같으면 정답
- 품목: 정답 품목마다 이름(띄어쓰기 무시)·수량·금액이 모두 같은 인식 품목이 있으면 맞힘
  → 재현율(정답 중 맞힌 비율), 정밀도(인식한 것 중 맞은 비율), 품목 전부 정확한 영수증 비율
  단가는 채점하지 않음 (영수증에 안 찍힌 경우가 많고, 화면에서 수량×단가로 다시 계산되므로)
"""

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import REPO_ROOT
from app.ocr.schemas import OcrRawResult
from app.parsing import ReceiptFields, ReceiptItem, parse

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")


# ---------- 채점 (순수 함수 — 테스트에서도 같은 기준으로 씀) ----------


def normalize_name(name: str | None) -> str:
    return re.sub(r"\s+", "", name or "").lower()


def _item_key(item: ReceiptItem) -> tuple[str, int, int]:
    return normalize_name(item.name), item.quantity, item.amount


@dataclass(frozen=True)
class Score:
    store_name: bool
    paid_at: bool
    total_amount: bool
    items_expected: int
    items_found: int
    items_matched: int

    @property
    def items_exact(self) -> bool:
        return self.items_matched == self.items_expected == self.items_found


def score(label: ReceiptFields, got: ReceiptFields) -> Score:
    def minute(value):  # noqa: ANN001, ANN202
        return value.replace(second=0, microsecond=0) if value else None

    remaining = [_item_key(item) for item in got.items]
    matched = 0
    for item in label.items:
        key = _item_key(item)
        if key in remaining:
            remaining.remove(key)
            matched += 1
    return Score(
        store_name=normalize_name(label.store_name) == normalize_name(got.store_name),
        paid_at=minute(label.paid_at) == minute(got.paid_at),
        total_amount=label.total_amount == got.total_amount,
        items_expected=len(label.items),
        items_found=len(got.items),
        items_matched=matched,
    )


# ---------- OCR 결과 캐시 ----------


@dataclass
class Sample:
    name: str
    image: Path
    label: ReceiptFields


def find_samples(dataset: Path, names: list[str]) -> tuple[list[Sample], list[str]]:
    """(채점할 영수증, 경고 메시지)"""
    samples: list[Sample] = []
    warnings: list[str] = []
    for label_file in sorted((dataset / "labels").glob("*.json")):
        name = label_file.stem
        if names and name not in names:
            continue
        image = next((p for s in IMAGE_SUFFIXES if (p := dataset / "images" / f"{name}{s}").is_file()), None)
        if image is None:
            warnings.append(f"{name}: 사진이 없어서 건너뜀 (dataset/images/{name}.jpg)")
            continue
        try:
            label = ReceiptFields.model_validate_json(label_file.read_text(encoding="utf-8"))
        except ValueError as error:
            warnings.append(f"{name}: 라벨 형식 오류로 건너뜀 → {str(error).splitlines()[0]}")
            continue
        samples.append(Sample(name, image, label))
    return samples, warnings


def _cache_file(dataset: Path, name: str) -> Path:
    return dataset / "ocr-cache" / f"{name}.json"


def load_cached(dataset: Path, sample: Sample, signature: str) -> OcrRawResult | None:
    """같은 사진·같은 엔진 설정으로 인식해 둔 결과가 있으면"""
    file = _cache_file(dataset, sample.name)
    if not file.is_file():
        return None
    data = json.loads(file.read_text(encoding="utf-8"))
    digest = hashlib.sha256(sample.image.read_bytes()).hexdigest()
    if data.get("image_sha256") != digest or data.get("engine") != signature:
        return None
    return OcrRawResult.model_validate(data["raw"])


def save_cached(dataset: Path, sample: Sample, signature: str, raw: OcrRawResult, seconds: float) -> None:
    file = _cache_file(dataset, sample.name)
    file.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "image_sha256": hashlib.sha256(sample.image.read_bytes()).hexdigest(),
        "engine": signature,
        "seconds": round(seconds, 2),
        "raw": json.loads(raw.model_dump_json()),
    }
    file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ---------- 실행 ----------


def _pct(part: int, whole: int) -> str:
    return f"{part / whole * 100:5.1f}%" if whole else "    -"


def _mark(ok: bool) -> str:
    return "O" if ok else "X"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="npm run ocr:eval --", description="OCR + 파싱 정확도 측정")
    parser.add_argument("names", nargs="*", help="채점할 영수증 이름 (비우면 전부)")
    parser.add_argument("--dataset", type=Path, default=REPO_ROOT / "dataset")
    parser.add_argument("--refresh", action="store_true", help="저장해 둔 OCR 결과를 무시하고 다시 인식")
    parser.add_argument("-v", "--verbose", action="store_true", help="틀린 항목의 정답/인식 값 출력")
    args = parser.parse_args(argv)

    from app.ocr.paddle import ENGINE_SIGNATURE  # paddle 패키지 없이도 import 됨 (실제 로딩은 엔진 만들 때)
    from app.receipts.masking import mask_ocr_result

    samples, warnings = find_samples(args.dataset, args.names)
    for warning in warnings:
        print(f"[주의] {warning}")
    if not samples:
        print("채점할 영수증이 없어요. dataset/images 에 사진, dataset/labels 에 같은 이름의 정답 JSON을 넣으세요")
        return 1

    engine = None
    scores: list[tuple[Sample, Score, float | None]] = []
    skipped = 0
    for sample in samples:
        raw = None if args.refresh else load_cached(args.dataset, sample, ENGINE_SIGNATURE)
        seconds = None
        if raw is None:
            if engine is None:
                try:
                    from app.ocr.paddle import PaddleOcrEngine

                    print("OCR 엔진 준비 중... (사진을 새로 인식해야 해서)")
                    engine = PaddleOcrEngine()
                except Exception as error:  # noqa: BLE001
                    print(f"[오류] 실제 OCR을 쓸 수 없어요: {error}")
                    print("       새로 인식해야 하는 사진은 건너뜁니다 → npm run setup:ocr 후 다시 실행")
                    engine = False
            if engine is False:
                skipped += 1
                continue
            started = time.perf_counter()
            raw = mask_ocr_result(engine.recognize(sample.image.read_bytes()))
            seconds = time.perf_counter() - started
            save_cached(args.dataset, sample, ENGINE_SIGNATURE, raw, seconds)
        got = parse(raw)
        result = score(sample.label, got)
        scores.append((sample, result, seconds))

        items = f"{result.items_matched}/{result.items_expected}"
        extra = f" (인식 {result.items_found}개)" if result.items_found != result.items_expected else ""
        took = f"  OCR {seconds:.1f}초" if seconds is not None else ""
        print(
            f"{sample.name:<12} 가게명 {_mark(result.store_name)}  결제일시 {_mark(result.paid_at)}  "
            f"합계 {_mark(result.total_amount)}  품목 {items}{extra}{took}"
        )
        if args.verbose:
            _print_details(sample.label, got, result)

    if not scores:
        return 1
    n = len(scores)
    expected = sum(s.items_expected for _, s, _ in scores)
    found = sum(s.items_found for _, s, _ in scores)
    matched = sum(s.items_matched for _, s, _ in scores)
    print(f"\n=== {n}장 채점" + (f" (OCR 못 해서 건너뜀 {skipped}장)" if skipped else "") + " ===")
    print(f"가게명      {_pct(sum(s.store_name for _, s, _ in scores), n)}")
    print(f"결제일시    {_pct(sum(s.paid_at for _, s, _ in scores), n)}")
    print(f"합계        {_pct(sum(s.total_amount for _, s, _ in scores), n)}")
    print(f"품목 재현율 {_pct(matched, expected)}   (정답 품목 중 맞힌 비율)")
    print(f"품목 정밀도 {_pct(matched, found)}   (인식한 품목 중 맞은 비율)")
    print(f"품목 전부 정확한 영수증 {_pct(sum(s.items_exact for _, s, _ in scores), n)}")
    timed = [t for _, _, t in scores if t is not None]
    if timed:
        print(f"OCR 평균 {sum(timed) / len(timed):.1f}초/장 (이번에 새로 인식한 {len(timed)}장 기준)")
    return 0


def _print_details(label: ReceiptFields, got: ReceiptFields, result: Score) -> None:
    if not result.store_name:
        print(f"    가게명   정답 {label.store_name!r}  인식 {got.store_name!r}")
    if not result.paid_at:
        print(f"    결제일시 정답 {label.paid_at}  인식 {got.paid_at}")
    if not result.total_amount:
        print(f"    합계     정답 {label.total_amount}  인식 {got.total_amount}")
    if not result.items_exact:
        want = {_item_key(i) for i in label.items}
        have = {_item_key(i) for i in got.items}
        for name, qty, amount in sorted(want - have):
            print(f"    품목 못 맞힘  {name} x{qty} = {amount:,}")
        for name, qty, amount in sorted(have - want):
            print(f"    품목 잘못 읽음 {name} x{qty} = {amount:,}")


if __name__ == "__main__":
    sys.exit(main())
