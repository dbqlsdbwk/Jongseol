# -*- coding: utf-8 -*-
"""
건종설 PDF 시방서 Parsing Agent
- 현재 프로젝트 폴더 구조 기준:

건종설/
├─ input/                  # PDF 원본 넣는 폴더
├─ output/                 # CSV 결과 저장 폴더
├─ UI/
│  └─ outputs/             # Streamlit UI에서 읽을 결과 저장 폴더, 필요 없으면 꺼도 됨
├─ main.py
├─ parser_agent.py
├─ parsing_agent_keyword_csv.py  # 이 파일
└─ requirements.txt

실행:
    python parsing_agent_keyword_csv.py

필요 패키지:
    pip install PyMuPDF
"""

import csv
import os
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError as e:
    raise ImportError(
        "PyMuPDF가 설치되어 있지 않습니다. 터미널에서 `pip install PyMuPDF` 실행 후 다시 돌리세요."
    ) from e


# =========================================================
# 1. 경로 설정
# =========================================================
# [수정 포인트 1] 프로젝트 루트 폴더를 자동으로 잡습니다.
# 이 파일이 건종설 폴더 바로 아래에 있으면 수정할 필요 없습니다.
BASE_DIR = Path(__file__).resolve().parent

# [수정 포인트 2] PDF 원본 폴더명입니다.
# 현재 구조상 건종설/input 폴더에 PDF를 넣으면 됩니다.
INPUT_DIR = BASE_DIR / "input"

# [수정 포인트 3] CSV 결과 저장 폴더명입니다.
# 현재 구조상 건종설/output 폴더에 결과가 생성됩니다.
OUTPUT_DIR = BASE_DIR / "output"

# [수정 포인트 4] Streamlit UI가 UI/outputs 폴더를 읽는 구조면 True로 두세요.
# UI에서 output 폴더만 읽게 할 거면 False로 바꿔도 됩니다.
COPY_TO_UI_OUTPUTS = True
UI_OUTPUT_DIR = BASE_DIR / "UI" / "outputs"

# [수정 포인트 5] 특정 PDF만 돌리고 싶으면 아래 리스트에 파일명을 직접 넣으세요.
# 예시: TARGET_PDFS = ["일반2.pdf", "normal.pdf"]
# 비워두면 input 폴더 안의 모든 .pdf 파일을 자동으로 처리합니다.
TARGET_PDFS = []

# [수정 포인트 6] 결과 CSV 파일명입니다. 필요하면 파일명만 바꾸면 됩니다.
DETAIL_CSV_NAME = "spec_keyword_classification.csv"
SUMMARY_CSV_NAME = "spec_category_summary.csv"


# =========================================================
# 2. 키워드 분류 사전
# =========================================================
# [수정 포인트 7] 분류 기준을 바꾸고 싶으면 아래 CATEGORY_KEYWORDS만 수정하면 됩니다.
# - 왼쪽: CSV에 찍힐 카테고리명
# - 오른쪽: 해당 카테고리로 잡을 키워드 목록
CATEGORY_KEYWORDS = {
    "공사개요/총칙": [
        "공사개요", "적용범위", "공사의 위치", "공사명", "대지 위치", "공사 기간",
        "설계도서", "계약문서", "용어", "발주자", "수급인", "시공자", "담당원",
        "감리자", "관련법규", "적용규정", "법령",
    ],
    "관리/행정/공정": [
        "현장대리인", "공사감독자", "공사관리", "공정관리", "예정공정표", "공정표",
        "시공계획서", "작업착수회의", "공사일지", "주간공정", "월별공정", "기성검사",
        "준공서류", "설계변경", "하도급", "협의", "보고", "제출", "승인", "검사", "입회",
    ],
    "자재관리": [
        "자재", "재료", "공급원", "사급자재", "지급자재", "반입", "보관", "운반", "취급",
        "수불부", "견본", "배합", "불합격", "원산지", "품질기준", "한국산업규격", "KS",
    ],
    "품질관리/시험": [
        "품질관리", "품질시험", "품질검사", "시험성적서", "품질보증", "현장시험실",
        "검사대장", "시험기관", "재시험", "시공검사", "압축강도", "지내력 시험",
        "평판재하시험", "강도시험",
    ],
    "안전/보건": [
        "안전", "보건", "안전관리계획", "안전관리자", "안전담당자", "안전조치",
        "안전점검", "안전검사", "안전교육", "산업안전보건", "보호구", "안전모", "안전화",
        "추락", "낙하", "붕괴", "화재", "전기사고", "위험물", "응급조치", "재해", "사고보고",
    ],
    "환경관리": [
        "환경", "환경관리", "환경오염", "비산먼지", "폐기물", "소음", "진동", "수질", "대기",
        "지하수", "폐유", "오니", "민원", "경관", "환경보전", "오염방지", "방음", "살수",
    ],
    "가설공사/비계": [
        "가설", "현장사무소", "재료창고", "가설울타리", "규준틀", "비계", "발판",
        "강관비계", "틀비계", "달비계", "비계다리", "난간", "방호선반", "추락방지",
        "가설동력", "공사용 도로",
    ],
    "토공사/기초": [
        "토공사", "기초", "터파기", "굴토", "절토", "되메우기", "성토", "배수", "흙막이",
        "지하수위", "지반", "토질", "지내력", "밑창콘크리트", "잔토", "발파", "토류판", "기초공사",
    ],
    "철근콘크리트": [
        "철근", "콘크리트", "거푸집", "레미콘", "양생", "부어넣기", "다짐", "피복두께",
        "정착", "이음", "슬래브", "압축강도", "코어", "공시체", "긴결철물", "받침기둥",
    ],
    "철골공사": [
        "철골", "강재", "앵커볼트", "고력볼트", "용접", "스터드", "현장접합", "주각",
        "가조립", "도장", "녹막이", "볼트접합", "용접재료", "정착",
    ],
    "지붕/홈통/방수": [
        "지붕", "홈통", "방수", "옥상", "누수", "시트방수", "도막방수", "아스팔트",
        "우레탄", "배수구", "드레인", "피로티", "외벽방수", "지붕마감",
    ],
    "금속/창호/유리": [
        "금속", "창호", "유리", "새시", "샷시", "알루미늄", "스테인리스", "문틀", "창틀",
        "강화유리", "복층유리", "코킹", "실링", "앵커", "철물",
    ],
    "마감/미장/도장/수장/단열": [
        "미장", "도장", "수장", "단열", "마감", "페인트", "도료", "석고보드", "천장",
        "벽지", "장판", "몰탈", "모르타르", "단열재", "보온재", "바탕", "면처리",
    ],
    "철거/해체/자원재활용": [
        "철거", "해체", "부분철거", "자원재활용", "폐기물", "분별해체", "반출", "해체공사",
        "철거물", "잔재", "석면", "폐콘크리트", "폐아스콘",
    ],
}


# =========================================================
# 3. 본문 처리 함수
# =========================================================
SECTION_PATTERNS = [
    re.compile(r"제\s*\d+\s*장\s*[:：]?\s*([^\n\r]+)"),
    re.compile(r"(\d+-\d+(?:-\d+)?)\s*([^\n\r]{2,40})"),
    re.compile(r"^\s*(\d+\.\s*\d+(?:\.\s*\d+)?)\s*([^\n\r]{2,40})", re.M),
]


def clean_text(text: str) -> str:
    """PDF에서 추출한 텍스트의 공백/줄바꿈을 정리합니다."""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def compact_for_match(text: str) -> str:
    """띄어쓰기 깨짐에 대응하기 위해 공백 제거 버전으로도 매칭합니다."""
    return re.sub(r"\s+", "", text)


def find_section(text: str, current_section: str) -> str:
    """페이지 상단에서 장/절 제목을 추정합니다."""
    first_lines = "\n".join(text.splitlines()[:12])
    for pattern in SECTION_PATTERNS:
        match = pattern.search(first_lines)
        if match:
            value = " ".join(g.strip() for g in match.groups() if g and g.strip())
            value = re.sub(r"[|ㆍ・]{2,}.*$", "", value).strip()
            if len(value) >= 2:
                return value[:80]
    return current_section


def project_name_from_page1(text: str, filename: str) -> str:
    """표지 텍스트에서 공사명을 간단히 추정합니다."""
    text_one = re.sub(r"\s+", " ", text)

    if "중앙대학교" in text_one:
        return "중앙대학교 다빈치캠퍼스 905관 장애인용 승강기 설치공사"
    if "국토교통인재개발원" in text_one:
        return "국토교통인재개발원 옥상정원 보수공사"

    # [수정 포인트 8] 특정 발주처/공사명을 더 잡고 싶으면 위 if문을 추가하면 됩니다.
    return filename


def split_sentences(text: str):
    """페이지 본문을 문장/항목 단위로 쪼개서 대표 excerpt 후보를 만듭니다."""
    raw_chunks = re.split(r"(?<=[다요함음됨임료])\.\s*|\n+|(?=\(?\d+\)|[가-하]\.\s)", text)
    chunks = []
    for chunk in raw_chunks:
        chunk = re.sub(r"\s+", " ", chunk).strip(" -·ㆍ|\t")
        if len(chunk) >= 25:
            chunks.append(chunk)
    return chunks or [re.sub(r"\s+", " ", text)[:500]]


def best_excerpt(text: str, keywords) -> str:
    """매칭 키워드가 가장 많이 들어간 대표 문장을 뽑습니다."""
    chunks = split_sentences(text)
    best = ""
    best_score = -1

    for chunk in chunks:
        compact_chunk = compact_for_match(chunk)
        score = sum(1 for keyword in keywords if keyword in chunk or compact_for_match(keyword) in compact_chunk)
        if score > best_score:
            best_score = score
            best = chunk

    return re.sub(r"\s+", " ", best).strip()[:500]


def classify_page(text: str):
    """페이지 텍스트를 카테고리별 키워드 점수로 분류합니다."""
    compact_text = compact_for_match(text)
    results = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        matched = []
        for keyword in keywords:
            if keyword in text or compact_for_match(keyword) in compact_text:
                matched.append(keyword)

        if matched:
            results.append({
                "category": category,
                "matched_keywords": matched,
                "keyword_score": len(matched),
                "text_excerpt": best_excerpt(text, matched),
            })

    results.sort(key=lambda x: x["keyword_score"], reverse=True)
    return results


def get_pdf_files():
    """처리할 PDF 목록을 반환합니다."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET_PDFS:
        pdf_files = [INPUT_DIR / name for name in TARGET_PDFS]
    else:
        pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    missing = [str(path) for path in pdf_files if not path.exists()]
    if missing:
        raise FileNotFoundError("다음 PDF 파일을 찾을 수 없습니다:\n" + "\n".join(missing))

    if not pdf_files:
        raise FileNotFoundError(
            f"{INPUT_DIR} 폴더에 PDF가 없습니다. input 폴더에 .pdf 파일을 넣고 다시 실행하세요."
        )

    return pdf_files


# =========================================================
# 4. CSV 생성 메인 로직
# =========================================================
def run_parsing_agent():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if COPY_TO_UI_OUTPUTS:
        UI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    summary = Counter()
    file_category_pages = defaultdict(set)

    pdf_files = get_pdf_files()
    print("[Parsing Agent] 처리 대상 PDF")
    for pdf_path in pdf_files:
        print(f"  - {pdf_path.name}")

    for pdf_path in pdf_files:
        file_name = pdf_path.name

        with fitz.open(pdf_path) as doc:
            first_text = clean_text(doc.load_page(0).get_text("text")) if doc.page_count else ""
            project_name = project_name_from_page1(first_text, file_name)
            current_section = ""

            for page_index in range(doc.page_count):
                page_no = page_index + 1
                text = clean_text(doc.load_page(page_index).get_text("text"))
                if not text:
                    continue

                current_section = find_section(text, current_section)
                classifications = classify_page(text)
                if not classifications:
                    continue

                # [수정 포인트 9] 페이지당 저장할 카테고리 개수입니다.
                # 3이면 한 페이지에서 가장 강하게 잡힌 상위 3개 카테고리만 CSV에 저장합니다.
                TOP_N_CATEGORY_PER_PAGE = 3

                for rank, item in enumerate(classifications[:TOP_N_CATEGORY_PER_PAGE], start=1):
                    category = item["category"]
                    matched = item["matched_keywords"]

                    rows.append({
                        "source_file": file_name,
                        "project_name": project_name,
                        "page": page_no,
                        "section_hint": current_section,
                        "category_rank_on_page": rank,
                        "primary_category": category,
                        "keyword_score": item["keyword_score"],
                        "matched_keywords": "; ".join(matched),
                        "text_excerpt": item["text_excerpt"],
                    })

                    summary[(file_name, project_name, category)] += 1
                    file_category_pages[(file_name, category)].add(page_no)

    detail_csv_path = OUTPUT_DIR / DETAIL_CSV_NAME
    summary_csv_path = OUTPUT_DIR / SUMMARY_CSV_NAME

    detail_fields = [
        "source_file", "project_name", "page", "section_hint", "category_rank_on_page",
        "primary_category", "keyword_score", "matched_keywords", "text_excerpt",
    ]

    with open(detail_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=detail_fields)
        writer.writeheader()
        writer.writerows(rows)

    with open(summary_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["source_file", "project_name", "primary_category", "row_count", "pages"],
        )
        writer.writeheader()

        for (file_name, project_name, category), count in sorted(summary.items(), key=lambda x: (x[0][0], x[0][2])):
            pages = sorted(file_category_pages[(file_name, category)])
            if len(pages) > 30:
                page_text = ",".join(map(str, pages[:20])) + " ... " + ",".join(map(str, pages[-5:]))
            else:
                page_text = ",".join(map(str, pages))

            writer.writerow({
                "source_file": file_name,
                "project_name": project_name,
                "primary_category": category,
                "row_count": count,
                "pages": page_text,
            })

    if COPY_TO_UI_OUTPUTS:
        shutil.copy2(detail_csv_path, UI_OUTPUT_DIR / DETAIL_CSV_NAME)
        shutil.copy2(summary_csv_path, UI_OUTPUT_DIR / SUMMARY_CSV_NAME)

    print("\n[Parsing Agent] CSV 생성 완료")
    print(f"  - 상세 결과: {detail_csv_path}")
    print(f"  - 요약 결과: {summary_csv_path}")
    if COPY_TO_UI_OUTPUTS:
        print(f"  - UI 복사 위치: {UI_OUTPUT_DIR}")
    print(f"  - 상세 행 수: {len(rows)}")
    print(f"  - 요약 카테고리 수: {len(summary)}")

    return detail_csv_path, summary_csv_path


if __name__ == "__main__":
    run_parsing_agent()
