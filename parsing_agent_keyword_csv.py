# -*- coding: utf-8 -*-
"""
PDF 시방서 Parsing Agent - 키워드 중심 분류 CSV 생성기
- 입력: input/일반2.pdf, input/normal.pdf
- 출력: output/spec_keyword_classification.csv
        output/spec_category_summary.csv
"""
import csv
import os
import re
from collections import Counter, defaultdict

import fitz  # PyMuPDF

PDF_FILES = [
    "input/일반2.pdf",
    "input/normal.pdf",
]

CATEGORY_KEYWORDS = {
    "공사개요/총칙": [
        "공사개요", "적용범위", "공사의 위치", "공사명", "대지 위치", "공사 기간", "설계도서", "계약문서", "용어", "발주자", "수급인", "시공자", "담당원", "감리자", "관련법규", "적용규정", "법령"
    ],
    "관리/행정/공정": [
        "현장대리인", "공사감독자", "공사관리", "공정관리", "예정공정표", "공정표", "시공계획서", "작업착수회의", "공사일지", "주간공정", "월별공정", "기성검사", "준공서류", "설계변경", "하도급", "협의", "보고", "제출", "승인", "검사", "입회"
    ],
    "자재관리": [
        "자재", "재료", "공급원", "사급자재", "지급자재", "반입", "보관", "운반", "취급", "수불부", "견본", "배합", "불합격", "원산지", "품질기준", "한국산업규격", "KS"
    ],
    "품질관리/시험": [
        "품질관리", "품질시험", "품질검사", "시험성적서", "품질보증", "현장시험실", "검사대장", "시험기관", "재시험", "시공검사", "압축강도", "지내력 시험", "평판재하시험", "강도시험"
    ],
    "안전/보건": [
        "안전", "보건", "안전관리계획", "안전관리자", "안전담당자", "안전조치", "안전점검", "안전검사", "안전교육", "산업안전보건", "보호구", "안전모", "안전화", "추락", "낙하", "붕괴", "화재", "전기사고", "위험물", "응급조치", "재해", "사고보고"
    ],
    "환경관리": [
        "환경", "환경관리", "환경오염", "비산먼지", "폐기물", "소음", "진동", "수질", "대기", "지하수", "폐유", "오니", "민원", "경관", "환경보전", "오염방지", "방음", "살수"
    ],
    "가설공사/비계": [
        "가설", "현장사무소", "재료창고", "가설울타리", "규준틀", "비계", "발판", "강관비계", "틀비계", "달비계", "비계다리", "난간", "방호선반", "추락방지", "가설동력", "공사용 도로"
    ],
    "토공사/기초": [
        "토공사", "기초", "터파기", "굴토", "절토", "되메우기", "성토", "배수", "흙막이", "지하수위", "지반", "토질", "지내력", "밑창콘크리트", "잔토", "발파", "토류판", "기초공사"
    ],
    "철근콘크리트": [
        "철근", "콘크리트", "거푸집", "레미콘", "양생", "부어넣기", "다짐", "피복두께", "정착", "이음", "슬래브", "압축강도", "코어", "공시체", "긴결철물", "받침기둥"
    ],
    "철골공사": [
        "철골", "강재", "앵커볼트", "고력볼트", "용접", "스터드", "현장접합", "주각", "가조립", "도장", "녹막이", "볼트접합", "용접재료", "정착"
    ],
    "지붕/홈통/방수": [
        "지붕", "홈통", "방수", "옥상", "누수", "시트방수", "도막방수", "아스팔트", "우레탄", "배수구", "드레인", "피로티", "외벽방수", "지붕마감"
    ],
    "금속/창호/유리": [
        "금속", "창호", "유리", "새시", "샷시", "알루미늄", "스테인리스", "문틀", "창틀", "강화유리", "복층유리", "코킹", "실링", "앵커", "철물"
    ],
    "마감/미장/도장/수장/단열": [
        "미장", "도장", "수장", "단열", "마감", "페인트", "도료", "석고보드", "천장", "벽지", "장판", "몰탈", "모르타르", "단열재", "보온재", "바탕", "면처리"
    ],
    "철거/해체/자원재활용": [
        "철거", "해체", "부분철거", "자원재활용", "폐기물", "분별해체", "반출", "해체공사", "철거물", "잔재", "석면", "폐콘크리트", "폐아스콘"
    ],
}

# 빠른 major section 탐지용
SECTION_PATTERNS = [
    re.compile(r"제\s*\d+\s*장\s*[:：]?\s*([^\n\r]+)"),
    re.compile(r"(\d+-\d+(?:-\d+)?)\s*([^\n\r]{2,40})"),
    re.compile(r"^\s*(\d+\.\s*\d+(?:\.\s*\d+)?)\s*([^\n\r]{2,40})", re.M),
]


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\t\r]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    return text.strip()


def compact_for_match(text: str) -> str:
    # OCR/추출 과정에서 띄어쓰기 깨진 경우까지 잡기 위해 공백 제거 버전도 사용
    return re.sub(r"\s+", "", text)


def find_section(text: str, current_section: str) -> str:
    first_lines = "\n".join(text.splitlines()[:12])
    for pat in SECTION_PATTERNS:
        m = pat.search(first_lines)
        if m:
            val = " ".join(g.strip() for g in m.groups() if g and g.strip())
            val = re.sub(r"[|ㆍ・]{2,}.*$", "", val).strip()
            if len(val) >= 2:
                return val[:80]
    return current_section


def project_name_from_page1(text: str, filename: str) -> str:
    text_one = re.sub(r"\s+", " ", text)
    if "중앙대학교" in text_one:
        return "중앙대학교 다빈치캠퍼스 905관 장애인용 승강기 설치공사"
    if "국토교통인재개발원" in text_one:
        return "국토교통인재개발원 옥상정원 보수공사"
    return os.path.basename(filename)


def split_sentences(text: str):
    # 너무 긴 페이지 텍스트를 문장/항목 단위 후보로 분리
    raw = re.split(r"(?<=[다요함음됨임료])\.\s*|\n+|(?=\(?\d+\)|[가-하]\.\s)", text)
    chunks = []
    for x in raw:
        x = re.sub(r"\s+", " ", x).strip(" -·ㆍ|\t")
        if len(x) >= 25:
            chunks.append(x)
    return chunks or [re.sub(r"\s+", " ", text)[:500]]


def best_excerpt(text: str, keywords):
    chunks = split_sentences(text)
    best = ""
    best_score = -1
    for c in chunks:
        c_match = compact_for_match(c)
        score = sum(1 for k in keywords if k in c or compact_for_match(k) in c_match)
        if score > best_score:
            best_score = score
            best = c
    best = re.sub(r"\s+", " ", best).strip()
    return best[:500]


def classify_page(text: str):
    norm = text
    compact = compact_for_match(text)
    results = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        matched = []
        for kw in kws:
            if kw in norm or compact_for_match(kw) in compact:
                matched.append(kw)
        if matched:
            results.append((cat, matched, len(matched), best_excerpt(text, matched)))
    results.sort(key=lambda x: x[2], reverse=True)
    return results


def main():
    rows = []
    summary = Counter()
    file_category_pages = defaultdict(set)

    for pdf_path in PDF_FILES:
        doc = fitz.open(pdf_path)
        file_name = os.path.basename(pdf_path)
        first_text = clean_text(doc.load_page(0).get_text("text")) if doc.page_count else ""
        project_name = project_name_from_page1(first_text, file_name)
        current_section = ""

        for idx in range(doc.page_count):
            page_no = idx + 1
            text = clean_text(doc.load_page(idx).get_text("text"))
            if not text:
                continue
            current_section = find_section(text, current_section)
            classifications = classify_page(text)
            if not classifications:
                continue

            # 페이지별 상위 3개 카테고리만 CSV 행으로 저장: 너무 많은 중복 방지
            for rank, (cat, matched, score, excerpt) in enumerate(classifications[:3], start=1):
                rows.append({
                    "source_file": file_name,
                    "project_name": project_name,
                    "page": page_no,
                    "section_hint": current_section,
                    "category_rank_on_page": rank,
                    "primary_category": cat,
                    "keyword_score": score,
                    "matched_keywords": "; ".join(matched),
                    "text_excerpt": excerpt,
                })
                summary[(file_name, project_name, cat)] += 1
                file_category_pages[(file_name, cat)].add(page_no)

    out_csv = "/mnt/data/spec_keyword_classification.csv"
    fields = [
        "source_file", "project_name", "page", "section_hint", "category_rank_on_page",
        "primary_category", "keyword_score", "matched_keywords", "text_excerpt"
    ]
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary_csv = "/mnt/data/spec_category_summary.csv"
    with open(summary_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["source_file", "project_name", "primary_category", "row_count", "pages"])
        writer.writeheader()
        for (file_name, project_name, cat), cnt in sorted(summary.items(), key=lambda x: (x[0][0], x[0][2])):
            pages = sorted(file_category_pages[(file_name, cat)])
            # 페이지가 너무 길면 앞뒤만 표시
            if len(pages) > 30:
                page_str = ",".join(map(str, pages[:20])) + " ... " + ",".join(map(str, pages[-5:]))
            else:
                page_str = ",".join(map(str, pages))
            writer.writerow({
                "source_file": file_name,
                "project_name": project_name,
                "primary_category": cat,
                "row_count": cnt,
                "pages": page_str,
            })

    print(f"saved: {out_csv} rows={len(rows)}")
    print(f"saved: {summary_csv} categories={len(summary)}")

if __name__ == "__main__":
    main()
