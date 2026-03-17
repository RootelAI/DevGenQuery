"""
PDF 전처리 파이프라인
- PyMuPDF   : 본문 텍스트 추출
- pdfplumber : 표(Table) 추출 → 마크다운 변환
- 규칙 기반 정제 (줄바꿈 복원, 헤더/푸터 제거, 특수문자 정제)
"""

import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pdfplumber


# ──────────────────────────────────────────────
# 1. 특수문자 정제
# ──────────────────────────────────────────────
def clean_special_chars(text: str) -> str:
    """PDF 추출 시 생기는 깨진 문자·합자 등을 정제합니다."""
    ligatures = {
        "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff",
        "ﬃ": "ffi", "ﬄ": "ffl",
    }
    for lig, rep in ligatures.items():
        text = text.replace(lig, rep)

    # null 문자 제거
    text = text.replace("\x00", "")
    # 글머리 제거
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    # 불필요한 공백 정리 (연속 공백 → 단일 공백)
    text = re.sub(r"[ \t]+", " ", text)
    return text


# ──────────────────────────────────────────────
# 2. 헤더 / 푸터 감지 및 제거
# ──────────────────────────────────────────────
def remove_numbers(text: str) -> str:
    """숫자를 제거하여 텍스트 비교에 사용합니다."""
    return re.sub(r"\d+", "", text).strip()


def extract_zone_lines(page, page_height: float, tolerance: int = 5) -> tuple[dict, dict]:
    """상단/하단(Header / Footer)에 머릿말과 꼬릿말이 위치할 만한 영역 이내 단어를 줄 단위로 그룹화하여 반환합니다."""
    top_lines, bottom_lines = {}, {}

    for word in page.extract_words():
        y = round(word["top"] / tolerance) * tolerance
        entry = {"text": word["text"], "bottom": word["bottom"]}

        if word["top"] < page_height * 0.15:
            if y not in top_lines:
                top_lines[y] = {"text": "", "bottom": word["bottom"]}
            top_lines[y]["text"] += " " + word["text"]
            top_lines[y]["bottom"] = max(top_lines[y]["bottom"], word["bottom"])

        if word["top"] > page_height * 0.9:
            if y not in bottom_lines:
                bottom_lines[y] = {"text": "", "bottom": word["bottom"]}
            bottom_lines[y]["text"] += " " + word["text"]
            bottom_lines[y]["bottom"] = max(bottom_lines[y]["bottom"], word["bottom"])

    return top_lines, bottom_lines


def compare(page1, page2, page_height: float, tolerance: int = 5) -> dict | None:
    """
    두 페이지의 상단/하단(Header / Footer)에서 머릿말과 꼬릿말에 해당하는 텍스트를 비교하여
    공통 헤더/푸터 영역을 반환합니다. 없으면 None 반환.
    """
    top1, bottom1 = extract_zone_lines(page1, page_height, tolerance)
    top2, bottom2 = extract_zone_lines(page2, page_height, tolerance)

    def find_common(lines1, lines2) -> list:
        common = []
        for y1, d1 in lines1.items():
            for y2, d2 in lines2.items():
                if abs(y1 - y2) <= tolerance:
                    if remove_numbers(d1["text"]) == remove_numbers(d2["text"]):
                        common.append({"y": (y1 + y2) / 2, "bottom": max(d1["bottom"], d2["bottom"])})
        return common

    common_top = find_common(top1, top2)
    common_bottom = find_common(bottom1, bottom2)

    if not common_top and not common_bottom:
        return None

    return {
        "header_bottom": max(c["bottom"] for c in common_top) if common_top else 0,
        "footer_top": min(c["y"] for c in common_bottom) if common_bottom else page_height,
    }


def detect_header_footer_by_position(plumber_doc, start_page: int = 0, total_pages: int = None) -> dict:
    """
    mid-1,mid / mid,mid+1 / mid+1,mid+2 / mid+2,mid+3 순서로 비교하여
    헤더/푸터 영역을 감지합니다.
    """
    if total_pages is None:
        total_pages = len(plumber_doc.pages)

    page_height = plumber_doc.pages[start_page].height
    mid = total_pages // 2
    hf = None

    for i in range(4):
        idx1 = start_page + mid - 1 + i
        idx2 = start_page + mid + i

        # 유효한 인덱스 범위 확인
        if idx1 < start_page or idx2 >= start_page + total_pages:
            continue

        hf = compare(plumber_doc.pages[idx1], plumber_doc.pages[idx2], page_height)
        if hf:
            print(f"[헤더/푸터 감지] {idx1+1}, {idx2+1}페이지에서 패턴 발견")
            print(f"  헤더 영역: y=0 ~ y={hf['header_bottom']:.1f}")
            print(f"  푸터 영역: y={hf['footer_top']:.1f} ~ y={page_height:.1f}")
            break

    if not hf:
        print("[헤더/푸터 감지] 반복 패턴 없음 → 헤더/푸터 없음으로 판단")
        hf = {"header_bottom": 0, "footer_top": page_height}

    hf["page_height"] = page_height

    hf["header_bottom"] = min(hf["header_bottom"], page_height)
    hf["footer_top"] = min(hf["footer_top"], page_height)
    
    return hf


# ──────────────────────────────────────────────
# 3. 줄바꿈 복원 (핵심 로직)
# ──────────────────────────────────────────────
def split_inline_numbers(text: str) -> str:
    """문장 중간에 붙어있는 번호를 줄바꿈으로 분리합니다."""

    # 숫자. 패턴 - 띄어쓰기 허용 (예: "...지급기일 6.\n" → "...지급기일\n6.")
    text = re.sub(r"(\S)\s+(\d{1,2}\.\s*\n)", r"\1\n\2", text)

    # 숫자) 패턴
    text = re.sub(r"(\S)\s+(\d{1,2}\)\s*\n)", r"\1\n\2", text)

    # 원문자 패턴
    text = re.sub(r"(\S)\s+([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮])", r"\1\n\2", text)

    # 제N조 / 제 N 조 패턴 (띄어쓰기 허용)
    text = re.sub(r"(\S)\s+(제\s*\d+\s*조)", r"\1\n\2", text)

    # 제N장 / 제 N 장 패턴 (띄어쓰기 허용)
    text = re.sub(r"(\S)\s+(제\s*\d+\s*장)", r"\1\n\2", text)

    return text


def restore_line_breaks(text: str) -> str:
    lines = text.splitlines()
    result = []
    buffer = ""

    # 띄어쓰기 허용한 패턴으로 수정
    new_paragraph_patterns = [
        r"^제\s*\d+\s*조",       # 제 1 조, 제1조
        r"^제\s*\d+\s*장",       # 제 1 장, 제1장
        r"^제\s*\d+\s*절",       # 제 1 절, 제1절
        r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]",
        r"^\d{1,2}\.\s",         # 1. 2. 10.
        r"^\d{1,2}\)\s",         # 1) 2) 10)
        r"^[가나다라마바사아자차카타파하]\.\s",
        r"^부\s*칙",
        r"^\[별표",
        r"^\[별지",
        r"^다만,",
        r"^#{1,6}\s",
    ]

    # 번호만 있는 줄 패턴 (내용 없이 번호만 있는 경우)
    number_only_patterns = [
        r"^\d{1,2}\.$",           # "1." 만 있는 줄
        r"^\d{1,2}\)$",           # "1)" 만 있는 줄
        r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]$",  # 원문자만 있는 줄
    ]

    def is_new_paragraph(line: str) -> bool:
        line = line.strip()
        if not line:
            return True
        return any(re.match(p, line) for p in new_paragraph_patterns)

    def is_number_only(line: str) -> bool:
        """번호만 있는 줄인지 판단 (내용이 다음 줄에 있는 경우)"""
        line = line.strip()
        return any(re.match(p, line) for p in number_only_patterns)

    def ends_sentence(line: str) -> bool:
        line = line.strip()
        return bool(re.search(r"[.。!?。；]\s*$", line))

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # 빈 줄 → 단락 구분
        if not stripped:
            if buffer:
                result.append(buffer.strip())
                buffer = ""
            result.append("")
            i += 1
            continue

        # 번호만 있는 줄 → 다음 줄 내용과 이어붙이기
        if is_number_only(stripped):
            if buffer:
                result.append(buffer.strip())
                buffer = ""
            # 다음 줄이 있으면 이어붙이기
            if i + 1 < len(lines) and lines[i + 1].strip():
                buffer = stripped + " " + lines[i + 1].strip()
                i += 2
            else:
                buffer = stripped
                i += 1
            continue

        # 새 단락 시작
        if is_new_paragraph(stripped):
            if buffer:
                result.append(buffer.strip())
                buffer = ""
            buffer = stripped
        else:
            if buffer and ends_sentence(buffer):
                result.append(buffer.strip())
                buffer = stripped
            else:
                if buffer:
                    buffer = buffer.rstrip() + " " + stripped
                else:
                    buffer = stripped

        i += 1

    if buffer:
        result.append(buffer.strip())

    text = "\n".join(result)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ──────────────────────────────────────────────
# 4. 표 추출 및 마크다운 변환 (pdfplumber)
# ──────────────────────────────────────────────
def extract_tables_from_page(page) -> list[dict[str, Any]]:
    """
    pdfplumber 페이지에서 표를 추출하여 마크다운으로 변환합니다.
    반환: [{"bbox": (x0,y0,x1,y1), "markdown": "...", "y0": float}]
    """
    tables = []
    for table in page.extract_tables():
        if not table:
            continue

        # 완전히 빈 행만 제거 (셀 병합으로 생긴 빈 행 처리)
        table = [
            row for row in table
            if any(cell and str(cell).strip() for cell in row)
        ]
        if not table:
            continue

        # 마크다운 표 생성
        md_lines = []
        for i, row in enumerate(table):
            # None 셀을 빈 문자열로 처리
            cells = [str(cell).strip() if cell else "" for cell in row]
            md_lines.append("| " + " | ".join(cells) + " |")
            if i == 0:
                md_lines.append("|" + "|".join(["---"] * len(cells)) + "|")

        # 표의 위치(y좌표) 파악 - 텍스트와 순서 정렬에 사용
        bbox = page.find_tables()[len(tables)].bbox if page.find_tables() else None
        y0 = bbox[1] if bbox else 0

        tables.append({
            "y0": y0,
            "markdown": "\n".join(md_lines),
            "bbox": bbox,
        })

    return tables


# ──────────────────────────────────────────────
# 5. 텍스트에서 표 영역 제거 (중복 방지)
# ──────────────────────────────────────────────
def remove_table_area_from_text(page_fitz, table_bboxes: list) -> str:
    blocks = page_fitz.get_text("blocks")
    result_lines = []

    MARGIN = 3  # 좌표 오차 허용 여유값 추가

    for block in blocks:
        bx0, by0, bx1, by1, text = block[:5]
        in_table = False

        for tbbox in table_bboxes:
            if tbbox is None:
                continue
            tx0, ty0, tx1, ty1 = tbbox
            # MARGIN만큼 여유를 두고 겹침 판단
            if not (bx1 < tx0 - MARGIN or bx0 > tx1 + MARGIN or
                    by1 < ty0 - MARGIN or by0 > ty1 + MARGIN):
                in_table = True
                break

        if not in_table:
            result_lines.append(text.strip())

    return "\n".join(result_lines)


def remove_page_footer_patterns(text: str) -> str:
    # 짝수 페이지: 줄 시작에 숫자 | 텍스트
    text = re.sub(r"^\d+\s*\|.+$", "", text, flags=re.MULTILINE)

    # 홀수 페이지: 텍스트 | 숫자로 끝나는 줄
    text = re.sub(r"^.+\|\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # 추가 - 줄 중간에 "숫자 | 텍스트"가 붙어있는 경우
    text = re.sub(r"\s+\d+\s*\|\s*\d{4}년.+$", "", text, flags=re.MULTILINE)

    # 추가 - 짝수 페이지 헤더: "숫자 + 공백 + 텍스트"로 시작하는 줄
    text = re.sub(r"^\d+\s{2,}.+$", "", text, flags=re.MULTILINE)

    # 추가 - 홀수 페이지 헤더: "텍스트 + 공백 + 숫자"로 끝나는 줄
    text = re.sub(r"^.+\s{2,}\d+\s*$", "", text, flags=re.MULTILINE)

    # 빈 줄 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# ──────────────────────────────────────────────
# 6. 페이지 단위 병합 (텍스트 + 표를 y좌표 순서로)
# ──────────────────────────────────────────────
def merge_text_and_tables(clean_text, tables):
    parts = [clean_text]
    for t in tables:
        if t["markdown"].strip():
            parts.append("\n" + t["markdown"] + "\n")
    return "\n".join(parts)


# ──────────────────────────────────────────────
# 7. 다단 : 영역으로 찾아 텍스트 변환
# ──────────────────────────────────────────────
def detect_columns(words, page_width, tolerance=5):
    if not words:
        return 1, page_width / 2

    # y좌표 기준으로 줄 그룹화
    sorted_words = sorted(words, key=lambda w: w["top"])
    lines = []
    current_line = [sorted_words[0]]
    for word in sorted_words[1:]:
        if abs(word["top"] - current_line[0]["top"]) <= tolerance:
            current_line.append(word)
        else:
            lines.append(current_line)
            current_line = [word]
    lines.append(current_line)

    # 줄이 2개 이하면 1단
    if len(lines) < 3:
        return 1, page_width / 2

    # 줄 수에 따라 확인할 줄 범위 결정
    if len(lines) >= 8:
        target_lines = lines[4:8]  # 5~8번째 줄
    elif len(lines) >= 5:
        target_lines = lines[2:5]  # 3~5번째 줄
    else:
        target_lines = lines        # 전체 줄

    # 단어 간 큰 간격 찾기
    gap_positions = []
    for line in target_lines:
        line_sorted = sorted(line, key=lambda w: w["x0"])
        if len(line_sorted) < 2:
            continue
        gaps = [line_sorted[i+1]["x0"] - line_sorted[i]["x1"] for i in range(len(line_sorted)-1)]
        avg_gap = sum(gaps) / len(gaps)
        for i, gap in enumerate(gaps):
            if gap > avg_gap * 5:
                mid = (line_sorted[i]["x1"] + line_sorted[i+1]["x0"]) / 2
                gap_positions.append(mid)

    if not gap_positions:
        return 1, page_width / 2

    col_boundary = sum(gap_positions) / len(gap_positions)
    consistent = [mid for mid in gap_positions if abs(mid - col_boundary) <= tolerance * 5]

    # 2개 이상 일치하면 2단
    if len(consistent) >= 2:
        return 2, sum(consistent) / len(consistent)

    return 1, page_width / 2


# ──────────────────────────────────────────────
# 8. 메인 전처리 파이프라인
# ──────────────────────────────────────────────
def preprocess_pdf(pdf_path: str) -> list[dict[str, Any]]:
    """
    PDF 전처리 메인 함수.
    sample_pages: 헤더/푸터 감지에 사용할 샘플 페이지 인덱스 (0부터 시작)
                  None이면 자동으로 중간 페이지 2개 선택
    """
    pdf_path = Path(pdf_path)
    results = []

    doc_fitz = fitz.open(str(pdf_path))
    plumber_doc = pdfplumber.open(str(pdf_path))

    # start_page = 1
    # end_page = 3
    # fitz_pages = [doc_fitz[i] for i in range(start_page, end_page)]
    # plumber_pages = [plumber_doc.pages[i] for i in range(start_page, end_page)]
    # total_pages = len(plumber_pages)

    start_page = 0
    total_pages = len(plumber_doc.pages)

    # ── Step 1: y좌표 기반 헤더/푸터 영역 감지 (1회만 실행)
    hf_info = detect_header_footer_by_position(plumber_doc, start_page=start_page, total_pages=total_pages)

    # ── Step 2: 페이지별 처리
    for page_num, (fitz_page, plumber_page) in enumerate(
        zip(doc_fitz, plumber_doc.pages), start=start_page
    ):
    # for page_num, (fitz_page, plumber_page) in enumerate(
    #     zip(fitz_pages, plumber_pages), start=start_page
    # ):
        # 2-1. 표 추출 (pdfplumber)
        tables = extract_tables_from_page(plumber_page)
        table_bboxes = [t["bbox"] for t in tables]

        # header_bottom 조정
        page_hf_info = hf_info.copy()
        if table_bboxes:
            min_table_y0 = min(bbox[1] for bbox in table_bboxes if bbox)
            if page_hf_info["header_bottom"] > min_table_y0:
                page_hf_info["header_bottom"] = min_table_y0 - 1
                
        if table_bboxes:
            min_table_y0 = min(bbox[1] for bbox in table_bboxes if bbox)
            if hf_info["header_bottom"] > min_table_y0:
                hf_info["header_bottom"] = min_table_y0 - 1

        # 2-2. 단 감지
        words = plumber_page.extract_words()
        num_columns, col_boundary = detect_columns(words, plumber_page.width)

        # 2-3. fitz.Rect로 단 영역 텍스트 추출
        y0 = page_hf_info["header_bottom"] + 1
        y1 = min(page_hf_info["footer_top"], fitz_page.rect.height)
        width = fitz_page.rect.width

        if num_columns == 1:
            rects = [fitz.Rect(0, y0, width, y1)]
        else:
            rects = [
                fitz.Rect(0,            y0, col_boundary, y1),
                fitz.Rect(col_boundary, y0, width,        y1),
            ]

        raw_text = ""
        for rect in rects:
            raw_text += fitz_page.get_text("text", clip=rect).strip() + " "

        # 2-4. 특수문자 정제
        raw_text = clean_special_chars(raw_text)

        # 2-5. 푸터 패턴 제거
        raw_text = remove_page_footer_patterns(raw_text)

        # 2-6. 번호 줄바꿈 분리
        raw_text = split_inline_numbers(raw_text)

        # 2-7. 줄바꿈 복원
        clean_text = restore_line_breaks(raw_text)

        # 2-8. 텍스트 + 표 병합
        merged = merge_text_and_tables(clean_text, tables)


        results.append({
            "page": page_num,
            "text": clean_text,
            "tables": [t["markdown"] for t in tables],
            "merged": merged,
            "metadata": {
                "source": pdf_path.name,
                "page": page_num,
                "has_table": len(tables) > 0,
                "table_count": len(tables),
            },
        })
    
    # results = connect_tables_across_pages(results)

    doc_fitz.close()
    plumber_doc.close()
    print(f"[완료] 총 {len(results)} 페이지 처리됨")
    return results


# ──────────────────────────────────────────────
# 9. 사용 예시
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # pdf_path = "D:/project/2026_pro/ocr/documents/"
    # pdf_name = "OTKCRK240459건설경기.pdf"

    pdf_path = "D:/project/2025_pro/rag/rag_pr/data/"
    pdf_name = "jkafn-30-1-24.pdf"

    pages = preprocess_pdf(pdf_path + pdf_name)

    # for p in pages:
    #     print(f"\n{'='*60}")
    #     print(f"📄 페이지 {p['page']} | 표 {p['metadata']['table_count']}개")
    #     print(f"{'='*60}")
    #     print(p["merged"])

    output_filename = "output_fall.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        for p in pages:
            f.write(f"\n{'='*60}\n")
            f.write(f"📄 페이지 {p['page']} | 표 {p['metadata']['table_count']}개\n")
            f.write(f"{'='*60}\n")
            f.write(p["merged"])
            f.write("\n")

    print(f"저장 완료 : {output_filename}")