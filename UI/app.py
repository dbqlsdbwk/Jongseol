import streamlit as st
import fitz
import re
import pandas as pd
import os
from datetime import datetime


# =========================================================
# 1. 기본 설정
# =========================================================

st.set_page_config(
    page_title="건설 시방서 검토 Agentic AI",
    page_icon="🏗️",
    layout="wide"
)

OUTPUT_DIR = "outputs"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# =========================================================
# 2. 체크리스트 DB
# =========================================================

CHECKLIST = [
    {
        "카테고리": "철근콘크리트",
        "검토항목": "철근 피복두께 기준",
        "필수키워드": ["철근", "피복"],
        "보조키워드": ["두께", "설계도서", "기준"],
        "수정권고": "철근 피복두께를 설계도서 및 표준시방서 기준 이상으로 확보하도록 명시하세요.",
        "보완문장": "철근의 피복두께는 설계도서 및 관련 표준시방서에서 정한 기준 이상을 확보하여야 하며, 시공 전 감독자의 확인을 받아야 한다."
    },
    {
        "카테고리": "철근콘크리트",
        "검토항목": "콘크리트 양생 기준",
        "필수키워드": ["콘크리트", "양생"],
        "보조키워드": ["기간", "온도", "습윤", "보온"],
        "수정권고": "콘크리트 타설 후 양생 방법, 기간, 온도 조건을 구체적으로 명시하세요.",
        "보완문장": "콘크리트 타설 후에는 설계도서 및 표준시방서 기준에 따라 양생 기간, 온도 조건, 습윤 또는 보온 조치 등을 확보하여야 한다."
    },
    {
        "카테고리": "철근콘크리트",
        "검토항목": "콘크리트 타설 전 청소",
        "필수키워드": ["타설", "청소"],
        "보조키워드": ["거푸집", "이물질", "제거"],
        "수정권고": "콘크리트 타설 전 거푸집 내부 이물질 제거 기준을 명시하세요.",
        "보완문장": "콘크리트 타설 전에는 거푸집 내부의 이물질, 고인 물, 먼지 등을 제거하고 청소 상태를 확인한 후 타설하여야 한다."
    },
    {
        "카테고리": "철근콘크리트",
        "검토항목": "콘크리트 강도 기준",
        "필수키워드": ["콘크리트", "강도"],
        "보조키워드": ["압축강도", "설계기준", "시험"],
        "수정권고": "콘크리트 설계기준강도 및 압축강도 시험 기준을 명시하세요.",
        "보완문장": "콘크리트는 설계기준강도를 만족하여야 하며, 압축강도 시험을 통해 품질 적합 여부를 확인하여야 한다."
    },
    {
        "카테고리": "품질관리",
        "검토항목": "품질시험 및 검사 기준",
        "필수키워드": ["시험", "검사"],
        "보조키워드": ["품질", "기준", "빈도", "방법"],
        "수정권고": "품질시험의 방법, 기준, 검사 빈도 및 판정 기준을 명시하세요.",
        "보완문장": "품질시험 및 검사는 관련 기준에 따라 시험 방법, 검사 빈도, 판정 기준을 정하여 실시하고 그 결과를 기록·관리하여야 한다."
    },
    {
        "카테고리": "품질관리",
        "검토항목": "자재 반입 검사",
        "필수키워드": ["자재", "반입"],
        "보조키워드": ["검사", "승인", "품질", "성적서"],
        "수정권고": "자재 반입 시 검사 절차, 품질성적서 확인 및 승인 절차를 명시하세요.",
        "보완문장": "현장에 반입되는 자재는 사용 전 품질성적서, 규격, 수량, 외관 상태를 확인하고 감독자의 승인을 받은 후 사용하여야 한다."
    },
    {
        "카테고리": "품질관리",
        "검토항목": "부적합 자재 처리",
        "필수키워드": ["부적합", "자재"],
        "보조키워드": ["반출", "교체", "재검사", "승인"],
        "수정권고": "부적합 자재 발견 시 반출, 교체, 재검사 절차를 명시하세요.",
        "보완문장": "부적합 자재가 확인된 경우 즉시 사용을 중지하고, 감독자 보고 후 반출, 교체 또는 재검사 등의 조치를 실시하여야 한다."
    },
    {
        "카테고리": "시공관리",
        "검토항목": "시공 전 승인 절차",
        "필수키워드": ["승인", "시공"],
        "보조키워드": ["감독자", "착수", "검토", "제출"],
        "수정권고": "시공 착수 전 감독자 승인 및 관련 자료 제출 절차를 명시하세요.",
        "보완문장": "주요 공정 착수 전에는 시공계획서, 자재 승인서, 작업 절차서 등 관련 자료를 제출하고 감독자의 승인을 받아야 한다."
    },
    {
        "카테고리": "시공관리",
        "검토항목": "시공 오차 허용기준",
        "필수키워드": ["오차", "허용"],
        "보조키워드": ["기준", "측정", "검사"],
        "수정권고": "시공 오차의 허용범위와 측정 및 검사 기준을 명시하세요.",
        "보완문장": "시공 오차는 설계도서 및 관련 기준에서 정한 허용범위 이내로 관리하여야 하며, 측정 및 검사 결과를 기록하여야 한다."
    },
    {
        "카테고리": "시공관리",
        "검토항목": "하자 보수 기준",
        "필수키워드": ["하자", "보수"],
        "보조키워드": ["기간", "책임", "조치", "재시공"],
        "수정권고": "하자 발생 시 보수 책임, 조치 절차 및 보수 기간을 명시하세요.",
        "보완문장": "하자가 발생한 경우 원인을 확인하고 책임 범위에 따라 보수, 교체 또는 재시공 등의 조치를 실시하여야 한다."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "작업자 보호구 착용",
        "필수키워드": ["보호구", "착용"],
        "보조키워드": ["안전모", "안전화", "작업자"],
        "수정권고": "작업자의 안전모, 안전화 등 보호구 착용 의무를 명시하세요.",
        "보완문장": "모든 작업자는 작업 전 안전모, 안전화, 안전대 등 해당 작업에 필요한 개인보호구를 착용하여야 한다."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "추락 방지 조치",
        "필수키워드": ["추락", "방지"],
        "보조키워드": ["안전난간", "안전대", "작업발판"],
        "수정권고": "고소작업 시 추락 방지시설, 안전대 착용 및 작업발판 설치 기준을 명시하세요.",
        "보완문장": "고소작업 시에는 안전난간, 작업발판, 안전대 등 추락 방지 조치를 설치하고 작업 전 이상 유무를 점검하여야 한다."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "화재 예방 조치",
        "필수키워드": ["화재", "예방"],
        "보조키워드": ["용접", "소화기", "인화물", "감시자"],
        "수정권고": "용접 등 화기작업 시 소화기 비치, 인화물 제거, 화재감시자 배치 기준을 명시하세요.",
        "보완문장": "용접 등 화기작업 전에는 인화성 물질을 제거하고 소화기를 비치하며, 필요한 경우 화재감시자를 배치하여야 한다."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "위험성 평가",
        "필수키워드": ["위험성", "평가"],
        "보조키워드": ["작업", "위험요인", "대책"],
        "수정권고": "공종별 위험성 평가와 위험요인별 관리대책 수립 절차를 명시하세요.",
        "보완문장": "공종별 작업 착수 전 위험성 평가를 실시하고, 확인된 위험요인에 대해 관리대책을 수립한 후 작업하여야 한다."
    },
    {
        "카테고리": "환경관리",
        "검토항목": "비산먼지 관리",
        "필수키워드": ["비산먼지", "관리"],
        "보조키워드": ["살수", "방진", "덮개", "세륜"],
        "수정권고": "비산먼지 발생 억제를 위한 살수, 방진덮개, 차량 세륜 기준을 명시하세요.",
        "보완문장": "비산먼지 발생이 예상되는 작업 구간에는 살수, 방진덮개 설치, 차량 세륜 등 비산먼지 저감 조치를 실시하여야 한다."
    },
    {
        "카테고리": "환경관리",
        "검토항목": "건설폐기물 처리",
        "필수키워드": ["폐기물", "처리"],
        "보조키워드": ["분리", "보관", "반출", "적법"],
        "수정권고": "건설폐기물의 분리보관, 반출, 적법 처리 절차를 명시하세요.",
        "보완문장": "건설폐기물은 종류별로 분리 보관하고, 관련 법령과 처리 절차에 따라 적법하게 반출 및 처리하여야 한다."
    },
    {
        "카테고리": "토공",
        "검토항목": "되메우기 다짐 기준",
        "필수키워드": ["되메우기", "다짐"],
        "보조키워드": ["층별", "다짐도", "시험", "기준"],
        "수정권고": "되메우기 시 층별 다짐두께, 다짐도 기준 및 시험 방법을 명시하세요.",
        "보완문장": "되메우기는 층별로 실시하고, 각 층의 다짐두께와 다짐도 기준을 만족하는지 시험을 통해 확인하여야 한다."
    },
    {
        "카테고리": "토공",
        "검토항목": "굴착 안전관리",
        "필수키워드": ["굴착", "안전"],
        "보조키워드": ["흙막이", "붕괴", "경사", "점검"],
        "수정권고": "굴착 시 흙막이, 사면 안정, 붕괴 방지 및 점검 기준을 명시하세요.",
        "보완문장": "굴착 작업 전 지반 상태와 주변 시설물을 확인하고, 흙막이 설치, 사면 안정, 붕괴 방지 조치를 실시하여야 한다."
    },
    {
        "카테고리": "방수공사",
        "검토항목": "방수층 시공 기준",
        "필수키워드": ["방수", "시공"],
        "보조키워드": ["방수층", "두께", "겹침", "누수"],
        "수정권고": "방수층의 두께, 겹침길이, 시공 방법 및 누수 검사 기준을 명시하세요.",
        "보완문장": "방수층은 설계도서 및 관련 기준에 따라 시공하고, 두께, 겹침길이, 접합 상태 및 누수 여부를 확인하여야 한다."
    },
    {
        "카테고리": "책임 및 절차",
        "검토항목": "감독자 승인 및 보고 절차",
        "필수키워드": ["감독자", "승인"],
        "보조키워드": ["보고", "제출", "검토", "확인"],
        "수정권고": "주요 공정 착수 전 감독자 승인, 보고 및 제출 절차를 명시하세요.",
        "보완문장": "주요 공정의 착수, 변경, 완료 시에는 관련 자료를 감독자에게 보고하고 필요한 경우 승인을 받아야 한다."
    }
]


VAGUE_WORDS = [
    "적절히", "충분히", "필요시", "가능한", "주의하여",
    "철저히", "신속히", "현장 여건에 따라", "적합하게",
    "안전하게", "견고하게", "문제가 없도록"
]


REPLACEMENTS = {
    "적절히": "표준시방서 및 설계도서 기준에 따라",
    "충분히": "설계도서 및 관련 기준 이상으로",
    "필요시": "해당 조건이 발생한 경우 감독자 승인 후",
    "가능한": "관련 기준에서 허용하는 범위 내에서",
    "현장 여건에 따라": "현장 여건을 검토하고 감독자 승인을 받아",
    "안전하게": "산업안전보건기준 및 현장 안전관리계획에 따라",
    "철저히": "점검 항목과 확인 절차에 따라",
    "신속히": "지정된 보고 및 조치 절차에 따라",
    "적합하게": "관련 기준 및 승인 절차에 적합하게",
    "견고하게": "설계도서 및 구조 기준을 만족하도록",
    "문제가 없도록": "검사 기준을 만족하도록"
}


# =========================================================
# 3. Parsing Agent
# =========================================================

def extract_text_from_pdf(uploaded_file):
    text = ""
    file_bytes = uploaded_file.read()

    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            text += "\n--- Page " + str(page_num) + " ---\n"
            text += page_text

    return text


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text):
    raw_units = re.split(r"(?<=[.。다])\s+|\n", text)
    units = []

    for unit in raw_units:
        unit = clean_text(unit)
        if len(unit) >= 15:
            units.append(unit)

    return units


# =========================================================
# 4. Checklist Review Agent
# =========================================================

def find_evidence(text, keywords, max_count=3):
    sentences = split_sentences(text)
    evidence = []

    for sentence in sentences:
        hit_count = 0

        for keyword in keywords:
            if keyword in sentence:
                hit_count += 1

        if hit_count >= 1:
            evidence.append(sentence)

    return evidence[:max_count]


def evaluate_checklist_item(text, item):
    required_keywords = item["필수키워드"]
    optional_keywords = item["보조키워드"]

    required_hits = []
    optional_hits = []

    for keyword in required_keywords:
        if keyword in text:
            required_hits.append(keyword)

    for keyword in optional_keywords:
        if keyword in text:
            optional_hits.append(keyword)

    evidence = find_evidence(text, required_keywords + optional_keywords)

    required_ratio = len(required_hits) / len(required_keywords)
    optional_count = len(optional_hits)

    score = len(required_hits) * 2 + len(optional_hits)

    if required_ratio == 1 and optional_count >= 1:
        status = "충족"
        risk = "낮음"
        recommendation = "해당 항목은 기본적으로 충족된 것으로 판단됩니다. 다만 수치 기준, 승인 주체, 검사 방법의 명확성은 추가 검토할 수 있습니다."
    elif required_ratio >= 0.5:
        status = "미흡"
        risk = "중간"
        recommendation = item["수정권고"]
    else:
        status = "누락"
        risk = "높음"
        recommendation = item["수정권고"]

    return {
        "카테고리": item["카테고리"],
        "검토항목": item["검토항목"],
        "판단": status,
        "위험도": risk,
        "점수": score,
        "필수키워드": ", ".join(required_keywords),
        "보조키워드": ", ".join(optional_keywords),
        "발견된 필수키워드": ", ".join(required_hits) if len(required_hits) > 0 else "없음",
        "발견된 보조키워드": ", ".join(optional_hits) if len(optional_hits) > 0 else "없음",
        "근거 문장": " / ".join(evidence) if len(evidence) > 0 else "관련 문장 발견 안 됨",
        "수정권고": recommendation,
        "보완문장": item["보완문장"]
    }


def evaluate_all_checklists(text):
    results = []

    for item in CHECKLIST:
        results.append(evaluate_checklist_item(text, item))

    return pd.DataFrame(results)


# =========================================================
# 5. Ambiguity Detection Agent
# =========================================================

def detect_vague_expressions(text):
    sentences = split_sentences(text)
    results = []

    for sentence in sentences:
        found_words = []

        for word in VAGUE_WORDS:
            if word in sentence:
                found_words.append(word)

        if len(found_words) > 0:
            revised_sentence = sentence

            for old_word, new_word in REPLACEMENTS.items():
                revised_sentence = revised_sentence.replace(old_word, new_word)

            results.append({
                "원문 문장": sentence,
                "모호 표현": ", ".join(found_words),
                "수정 방향": "모호한 표현을 정량 기준, 절차, 승인 주체가 포함된 표현으로 수정하세요.",
                "예시 수정안": revised_sentence
            })

    return pd.DataFrame(results)


# =========================================================
# 6. Revision Agent
# =========================================================

def create_revision_plan(checklist_df, vague_df):
    revision_rows = []

    problem_df = checklist_df[checklist_df["판단"].isin(["미흡", "누락"])]

    for idx, row in problem_df.iterrows():
        if row["판단"] == "누락":
            action = "신규 조항 추가 필요"
            priority = "상"
        else:
            action = "기존 조항 보완 필요"
            priority = "중"

        revision_rows.append({
            "우선순위": priority,
            "카테고리": row["카테고리"],
            "검토항목": row["검토항목"],
            "현재 판단": row["판단"],
            "보완 유형": action,
            "문제 요약": row["수정권고"],
            "자동 보완 문장": row["보완문장"]
        })

    if len(vague_df) > 0:
        for idx, row in vague_df.iterrows():
            revision_rows.append({
                "우선순위": "중",
                "카테고리": "문장 표현",
                "검토항목": "모호표현 수정",
                "현재 판단": "미흡",
                "보완 유형": "표현 구체화 필요",
                "문제 요약": row["모호 표현"] + " 등의 표현이 모호하게 사용됨",
                "자동 보완 문장": row["예시 수정안"]
            })

    return pd.DataFrame(revision_rows)


def create_revised_clause_text(revision_df):
    if len(revision_df) == 0:
        return "보완이 필요한 조항이 발견되지 않았습니다."

    text = ""
    text += "[시방서 보완 조항 초안]\n\n"

    grouped = revision_df.groupby("카테고리")

    for category, group in grouped:
        text += "■ " + str(category) + "\n"

        for idx, row in group.iterrows():
            text += "- " + str(row["검토항목"]) + "\n"
            text += "  · 보완 유형: " + str(row["보완 유형"]) + "\n"
            text += "  · 보완 문장: " + str(row["자동 보완 문장"]) + "\n\n"

    return text


# =========================================================
# 7. Report Agent
# =========================================================

def generate_report(checklist_df, vague_df, revision_df, file_name):
    total = len(checklist_df)
    satisfied = len(checklist_df[checklist_df["판단"] == "충족"])
    insufficient = len(checklist_df[checklist_df["판단"] == "미흡"])
    missing = len(checklist_df[checklist_df["판단"] == "누락"])
    vague_count = len(vague_df)
    revision_count = len(revision_df)

    satisfied_ratio = round((satisfied / total) * 100, 1) if total > 0 else 0
    insufficient_ratio = round((insufficient / total) * 100, 1) if total > 0 else 0
    missing_ratio = round((missing / total) * 100, 1) if total > 0 else 0

    high_risk_df = checklist_df[checklist_df["위험도"] == "높음"]

    report = ""
    report += "건설 시방서 체크리스트 기반 검토 보고서\n"
    report += "========================================\n\n"

    report += "1. 검토 개요\n"
    report += "----------------------------------------\n"
    report += "- 검토 대상 파일: " + str(file_name) + "\n"
    report += "- 검토 방식: PDF 텍스트 추출 후 체크리스트 기반 Rule-Based 판단\n"
    report += "- 검토 항목 수: " + str(total) + "개\n"
    report += "- 구성 Agent: Parsing Agent, Checklist Review Agent, Ambiguity Detection Agent, Revision Agent, Report Agent\n\n"

    report += "2. 종합 검토 결과\n"
    report += "----------------------------------------\n"
    report += "- 충족: " + str(satisfied) + "개 (" + str(satisfied_ratio) + "%)\n"
    report += "- 미흡: " + str(insufficient) + "개 (" + str(insufficient_ratio) + "%)\n"
    report += "- 누락: " + str(missing) + "개 (" + str(missing_ratio) + "%)\n"
    report += "- 모호표현 발견: " + str(vague_count) + "개\n"
    report += "- 보완 필요 항목: " + str(revision_count) + "개\n\n"

    report += "3. 주요 위험 항목\n"
    report += "----------------------------------------\n"

    if len(high_risk_df) == 0:
        report += "- 위험도 높음 항목은 발견되지 않았습니다.\n\n"
    else:
        for idx, row in high_risk_df.iterrows():
            report += "- [" + row["카테고리"] + "] " + row["검토항목"] + ": " + row["수정권고"] + "\n"
        report += "\n"

    report += "4. 보완 필요 항목\n"
    report += "----------------------------------------\n"

    if len(revision_df) == 0:
        report += "- 보완 필요 항목이 발견되지 않았습니다.\n\n"
    else:
        for idx, row in revision_df.iterrows():
            report += "- 우선순위 " + row["우선순위"] + " | "
            report += "[" + row["카테고리"] + "] "
            report += row["검토항목"] + "\n"
            report += "  · 문제 요약: " + row["문제 요약"] + "\n"
            report += "  · 보완 문장: " + row["자동 보완 문장"] + "\n"

    report += "\n5. 종합 의견\n"
    report += "----------------------------------------\n"

    if missing > 0:
        report += "본 시방서는 일부 필수 검토항목이 누락된 것으로 판단되므로, 누락 항목에 대한 신규 조항 추가가 우선적으로 필요합니다. "
    elif insufficient > 0:
        report += "본 시방서는 주요 항목이 대체로 포함되어 있으나, 일부 조항의 기준, 절차, 승인 주체가 구체적으로 제시되지 않아 보완이 필요합니다. "
    else:
        report += "본 시방서는 주요 체크리스트 항목을 전반적으로 충족하는 것으로 판단됩니다. "

    if vague_count > 0:
        report += "또한 모호표현이 확인되므로 정량 기준, 검사 방법, 승인 절차 중심의 표현으로 수정하는 것이 바람직합니다. "
    else:
        report += "모호표현은 크게 확인되지 않았습니다. "

    report += "향후에는 표준시방서 및 관련 기준 문서를 Retrieval Agent로 연계하고, LLM Judgment Agent를 통해 문맥 기반 판단을 수행하면 검토 정확도를 높일 수 있습니다.\n\n"

    report += "6. 한계 및 향후 개선 방향\n"
    report += "----------------------------------------\n"
    report += "- 현재 시스템은 키워드 기반 판단이므로 문맥을 완전히 이해하지는 못합니다.\n"
    report += "- 같은 의미의 다른 표현은 누락으로 판단될 수 있습니다.\n"
    report += "- 향후 표준시방서 DB와 Retrieval Agent를 연결하여 기준 조항과 직접 비교할 수 있습니다.\n"
    report += "- LLM Judgment Agent를 추가하면 기준의 구체성, 수치 기준, 승인 절차, 검사 방법까지 의미 기반으로 판단할 수 있습니다.\n"

    return report


# =========================================================
# 8. 저장 기능
# =========================================================

def save_outputs(checklist_df, vague_df, revision_df, report_text, revised_clause_text):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")

    excel_path = os.path.join(OUTPUT_DIR, "시방서_검토결과_" + now + ".xlsx")
    report_path = os.path.join(OUTPUT_DIR, "시방서_검토보고서_" + now + ".txt")
    revision_path = os.path.join(OUTPUT_DIR, "시방서_보완조항초안_" + now + ".txt")

    summary_df = pd.DataFrame({
        "항목": ["총 검토항목", "충족", "미흡", "누락", "모호표현 발견", "보완 필요 항목"],
        "개수": [
            len(checklist_df),
            len(checklist_df[checklist_df["판단"] == "충족"]),
            len(checklist_df[checklist_df["판단"] == "미흡"]),
            len(checklist_df[checklist_df["판단"] == "누락"]),
            len(vague_df),
            len(revision_df)
        ]
    })

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="요약", index=False)
        checklist_df.to_excel(writer, sheet_name="체크리스트 검토", index=False)
        vague_df.to_excel(writer, sheet_name="모호표현 검토", index=False)
        revision_df.to_excel(writer, sheet_name="Revision Agent", index=False)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    with open(revision_path, "w", encoding="utf-8") as f:
        f.write(revised_clause_text)

    return excel_path, report_path, revision_path


def safe_download_button(label, path, mime_type):
    if hasattr(st, "download_button"):
        with open(path, "rb") as file:
            st.download_button(
                label=label,
                data=file,
                file_name=os.path.basename(path),
                mime=mime_type
            )
    else:
        st.info(label + " 파일이 생성되었습니다: " + path)


# =========================================================
# 9. UI Dashboard - 탭 없는 구버전 호환형
# =========================================================

st.title("🏗️ 건설 시방서 검토 Agentic AI")
st.write("PDF 일반시방서를 업로드하면 체크리스트 검토, 보완 문장 생성, 검토 보고서 작성까지 자동 수행합니다.")

st.markdown("---")

st.sidebar.header("Agent 구성")
st.sidebar.write("1. Parsing Agent")
st.sidebar.write("2. Checklist Review Agent")
st.sidebar.write("3. Ambiguity Detection Agent")
st.sidebar.write("4. Revision Agent")
st.sidebar.write("5. Report Agent")
st.sidebar.markdown("---")
st.sidebar.info("현재 버전은 구버전 Streamlit에서도 실행되도록 탭 기능 없이 제작되었습니다.")

uploaded_pdf = st.file_uploader(
    "검토할 일반시방서 PDF를 업로드하세요.",
    type=["pdf"]
)


if uploaded_pdf is not None:
    with st.spinner("Agent들이 시방서를 검토하고 있습니다..."):
        raw_text = extract_text_from_pdf(uploaded_pdf)
        cleaned_text = clean_text(raw_text)

        if len(cleaned_text) < 50:
            st.error("PDF에서 텍스트를 충분히 추출하지 못했습니다. 스캔본 PDF일 가능성이 있습니다.")
            st.stop()

        checklist_df = evaluate_all_checklists(cleaned_text)
        vague_df = detect_vague_expressions(cleaned_text)
        revision_df = create_revision_plan(checklist_df, vague_df)
        revised_clause_text = create_revised_clause_text(revision_df)
        report_text = generate_report(
            checklist_df,
            vague_df,
            revision_df,
            uploaded_pdf.name
        )

        excel_path, report_path, revision_path = save_outputs(
            checklist_df,
            vague_df,
            revision_df,
            report_text,
            revised_clause_text
        )

    total_count = len(checklist_df)
    satisfied_count = len(checklist_df[checklist_df["판단"] == "충족"])
    insufficient_count = len(checklist_df[checklist_df["판단"] == "미흡"])
    missing_count = len(checklist_df[checklist_df["판단"] == "누락"])
    vague_count = len(vague_df)
    revision_count = len(revision_df)

    st.success("검토가 완료되었습니다.")

    st.markdown("## 1. 검토 요약")

    summary_text = """
    - 총 검토항목: {0}개
    - 충족: {1}개
    - 미흡: {2}개
    - 누락: {3}개
    - 모호표현: {4}개
    - 보완 필요: {5}개
    """.format(
        total_count,
        satisfied_count,
        insufficient_count,
        missing_count,
        vague_count,
        revision_count
    )

    st.markdown(summary_text)

    st.markdown("## 2. 판단 결과 차트")

    status_count_df = checklist_df["판단"].value_counts().reset_index()
    status_count_df.columns = ["판단", "개수"]
    status_count_df = status_count_df.set_index("판단")
    st.bar_chart(status_count_df)

    category_count_df = checklist_df.groupby(["카테고리", "판단"]).size().reset_index(name="개수")
    pivot_df = category_count_df.pivot(index="카테고리", columns="판단", values="개수").fillna(0)

    st.write("### 카테고리별 판단 결과")
    st.bar_chart(pivot_df)

    st.markdown("---")

    st.markdown("## 3. 결과 보기")

    section = st.radio(
        "확인할 항목을 선택하세요.",
        [
            "체크리스트 검토 결과",
            "보완 필요 항목",
            "Revision Agent 결과",
            "Report Agent 결과",
            "모호표현 검토 결과",
            "원문 텍스트"
        ]
    )

    if section == "체크리스트 검토 결과":
        st.markdown("### 체크리스트 검토 결과")

        selected_status = st.multiselect(
            "판단 결과 필터",
            options=["충족", "미흡", "누락"],
            default=["충족", "미흡", "누락"]
        )

        selected_category = st.multiselect(
            "카테고리 필터",
            options=sorted(checklist_df["카테고리"].unique()),
            default=sorted(checklist_df["카테고리"].unique())
        )

        filtered_df = checklist_df[
            (checklist_df["판단"].isin(selected_status)) &
            (checklist_df["카테고리"].isin(selected_category))
        ]

        st.dataframe(filtered_df)

    elif section == "보완 필요 항목":
        st.markdown("### 보완 필요 항목 상세")

        problem_df = checklist_df[checklist_df["판단"].isin(["미흡", "누락"])]

        if len(problem_df) == 0:
            st.success("미흡 또는 누락 항목이 없습니다.")
        else:
            for idx, row in problem_df.iterrows():
                title = "[" + row["판단"] + "] " + row["카테고리"] + " - " + row["검토항목"]

                if hasattr(st, "expander"):
                    with st.expander(title):
                        st.write("위험도: " + row["위험도"])
                        st.write("발견된 필수키워드: " + row["발견된 필수키워드"])
                        st.write("발견된 보조키워드: " + row["발견된 보조키워드"])
                        st.write("근거 문장: " + row["근거 문장"])
                        st.warning(row["수정권고"])
                        st.success("자동 보완 문장: " + row["보완문장"])
                else:
                    st.write("#### " + title)
                    st.write("위험도: " + row["위험도"])
                    st.write("발견된 필수키워드: " + row["발견된 필수키워드"])
                    st.write("발견된 보조키워드: " + row["발견된 보조키워드"])
                    st.write("근거 문장: " + row["근거 문장"])
                    st.warning(row["수정권고"])
                    st.success("자동 보완 문장: " + row["보완문장"])

    elif section == "Revision Agent 결과":
        st.markdown("### Revision Agent 결과")

        if len(revision_df) == 0:
            st.success("Revision Agent가 보완 필요 항목을 발견하지 않았습니다.")
        else:
            st.dataframe(revision_df)

            st.markdown("### 시방서 보완 조항 초안")
            st.text_area(
                "자동 생성된 보완 조항",
                revised_clause_text,
                height=500
            )

    elif section == "Report Agent 결과":
        st.markdown("### Report Agent 결과")

        st.text_area(
            "자동 생성 검토 보고서",
            report_text,
            height=700
        )

    elif section == "모호표현 검토 결과":
        st.markdown("### 모호표현 검토 결과")

        if len(vague_df) == 0:
            st.success("모호표현이 발견되지 않았습니다.")
        else:
            st.dataframe(vague_df)

    elif section == "원문 텍스트":
        st.markdown("### 추출된 PDF 원문 텍스트")

        st.text_area(
            "추출 텍스트",
            raw_text[:15000],
            height=700
        )

    st.markdown("---")

    st.markdown("## 4. 결과 다운로드")

    safe_download_button(
        "엑셀 결과 다운로드",
        excel_path,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    safe_download_button(
        "검토 보고서 다운로드",
        report_path,
        "text/plain"
    )

    safe_download_button(
        "보완 조항 초안 다운로드",
        revision_path,
        "text/plain"
    )

else:
    st.info("PDF 파일을 업로드하면 Agent 기반 검토가 시작됩니다.")

    st.markdown("""
    ### 시스템 처리 흐름

    1. **Parsing Agent**  
       PDF에서 텍스트를 추출하고 문장 단위로 정리합니다.

    2. **Checklist Review Agent**  
       체크리스트별 필수키워드와 보조키워드를 기준으로 충족 / 미흡 / 누락을 판단합니다.

    3. **Ambiguity Detection Agent**  
       “적절히”, “충분히”, “필요시” 등 모호표현을 탐지합니다.

    4. **Revision Agent**  
       미흡·누락 항목에 대한 자동 보완 문장을 생성합니다.

    5. **Report Agent**  
       전체 검토 결과를 종합하여 보고서 형태로 정리합니다.

    6. **UI Dashboard**  
       검토 결과, 보완 조항, 보고서, 다운로드 파일을 제공합니다.
    """)