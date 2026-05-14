import streamlit as st
import fitz
import re
import pandas as pd
import os
from datetime import datetime
import plotly.express as px


# =========================================================
# 1. 기본 설정
# =========================================================

st.set_page_config(
    page_title="건설 시방서 체크리스트 검토 AI",
    page_icon="🏗️",
    layout="wide"
)

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================================================
# 2. 체크리스트 DB
# =========================================================

CHECKLIST = [
    {
        "카테고리": "철근콘크리트",
        "검토항목": "철근 피복두께 기준",
        "필수키워드": ["철근", "피복"],
        "보조키워드": ["두께", "설계도서", "기준"],
        "수정권고": "철근 피복두께를 설계도서 및 표준시방서 기준 이상으로 확보하도록 명시하세요."
    },
    {
        "카테고리": "철근콘크리트",
        "검토항목": "콘크리트 양생 기준",
        "필수키워드": ["콘크리트", "양생"],
        "보조키워드": ["기간", "온도", "습윤", "보온"],
        "수정권고": "콘크리트 타설 후 양생 방법, 기간, 온도 조건을 구체적으로 명시하세요."
    },
    {
        "카테고리": "철근콘크리트",
        "검토항목": "콘크리트 타설 전 청소",
        "필수키워드": ["타설", "청소"],
        "보조키워드": ["거푸집", "이물질", "제거"],
        "수정권고": "콘크리트 타설 전 거푸집 내부 이물질 제거 기준을 명시하세요."
    },
    {
        "카테고리": "철근콘크리트",
        "검토항목": "콘크리트 강도 기준",
        "필수키워드": ["콘크리트", "강도"],
        "보조키워드": ["압축강도", "설계기준", "시험"],
        "수정권고": "콘크리트 설계기준강도 및 압축강도 시험 기준을 명시하세요."
    },
    {
        "카테고리": "품질관리",
        "검토항목": "품질시험 및 검사 기준",
        "필수키워드": ["시험", "검사"],
        "보조키워드": ["품질", "기준", "빈도", "방법"],
        "수정권고": "품질시험의 방법, 기준, 검사 빈도 및 판정 기준을 명시하세요."
    },
    {
        "카테고리": "품질관리",
        "검토항목": "자재 반입 검사",
        "필수키워드": ["자재", "반입"],
        "보조키워드": ["검사", "승인", "품질", "성적서"],
        "수정권고": "자재 반입 시 검사 절차, 품질성적서 확인 및 승인 절차를 명시하세요."
    },
    {
        "카테고리": "품질관리",
        "검토항목": "부적합 자재 처리",
        "필수키워드": ["부적합", "자재"],
        "보조키워드": ["반출", "교체", "재검사", "승인"],
        "수정권고": "부적합 자재 발견 시 반출, 교체, 재검사 절차를 명시하세요."
    },
    {
        "카테고리": "시공관리",
        "검토항목": "시공 전 승인 절차",
        "필수키워드": ["승인", "시공"],
        "보조키워드": ["감독자", "착수", "검토", "제출"],
        "수정권고": "시공 착수 전 감독자 승인 및 관련 자료 제출 절차를 명시하세요."
    },
    {
        "카테고리": "시공관리",
        "검토항목": "시공 오차 허용기준",
        "필수키워드": ["오차", "허용"],
        "보조키워드": ["기준", "측정", "검사"],
        "수정권고": "시공 오차의 허용범위와 측정 및 검사 기준을 명시하세요."
    },
    {
        "카테고리": "시공관리",
        "검토항목": "하자 보수 기준",
        "필수키워드": ["하자", "보수"],
        "보조키워드": ["기간", "책임", "조치", "재시공"],
        "수정권고": "하자 발생 시 보수 책임, 조치 절차 및 보수 기간을 명시하세요."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "작업자 보호구 착용",
        "필수키워드": ["보호구", "착용"],
        "보조키워드": ["안전모", "안전화", "작업자"],
        "수정권고": "작업자의 안전모, 안전화 등 보호구 착용 의무를 명시하세요."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "추락 방지 조치",
        "필수키워드": ["추락", "방지"],
        "보조키워드": ["안전난간", "안전대", "작업발판"],
        "수정권고": "고소작업 시 추락 방지시설, 안전대 착용 및 작업발판 설치 기준을 명시하세요."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "화재 예방 조치",
        "필수키워드": ["화재", "예방"],
        "보조키워드": ["용접", "소화기", "인화물", "감시자"],
        "수정권고": "용접 등 화기작업 시 소화기 비치, 인화물 제거, 화재감시자 배치 기준을 명시하세요."
    },
    {
        "카테고리": "안전관리",
        "검토항목": "위험성 평가",
        "필수키워드": ["위험성", "평가"],
        "보조키워드": ["작업", "위험요인", "대책"],
        "수정권고": "공종별 위험성 평가와 위험요인별 관리대책 수립 절차를 명시하세요."
    },
    {
        "카테고리": "환경관리",
        "검토항목": "비산먼지 관리",
        "필수키워드": ["비산먼지", "관리"],
        "보조키워드": ["살수", "방진", "덮개", "세륜"],
        "수정권고": "비산먼지 발생 억제를 위한 살수, 방진덮개, 차량 세륜 기준을 명시하세요."
    },
    {
        "카테고리": "환경관리",
        "검토항목": "건설폐기물 처리",
        "필수키워드": ["폐기물", "처리"],
        "보조키워드": ["분리", "보관", "반출", "적법"],
        "수정권고": "건설폐기물의 분리보관, 반출, 적법 처리 절차를 명시하세요."
    },
    {
        "카테고리": "토공",
        "검토항목": "되메우기 다짐 기준",
        "필수키워드": ["되메우기", "다짐"],
        "보조키워드": ["층별", "다짐도", "시험", "기준"],
        "수정권고": "되메우기 시 층별 다짐두께, 다짐도 기준 및 시험 방법을 명시하세요."
    },
    {
        "카테고리": "토공",
        "검토항목": "굴착 안전관리",
        "필수키워드": ["굴착", "안전"],
        "보조키워드": ["흙막이", "붕괴", "경사", "점검"],
        "수정권고": "굴착 시 흙막이, 사면 안정, 붕괴 방지 및 점검 기준을 명시하세요."
    },
    {
        "카테고리": "방수공사",
        "검토항목": "방수층 시공 기준",
        "필수키워드": ["방수", "시공"],
        "보조키워드": ["방수층", "두께", "겹침", "누수"],
        "수정권고": "방수층의 두께, 겹침길이, 시공 방법 및 누수 검사 기준을 명시하세요."
    },
    {
        "카테고리": "책임 및 절차",
        "검토항목": "감독자 승인 및 보고 절차",
        "필수키워드": ["감독자", "승인"],
        "보조키워드": ["보고", "제출", "검토", "확인"],
        "수정권고": "주요 공정 착수 전 감독자 승인, 보고 및 제출 절차를 명시하세요."
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
# 3. PDF 텍스트 추출
# =========================================================

def extract_text_from_pdf(uploaded_file):
    text = ""

    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            text += f"\n--- Page {page_num} ---\n"
            text += page_text

    return text


# =========================================================
# 4. 텍스트 전처리
# =========================================================

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
# 5. 체크리스트 판단 로직
# =========================================================

def find_evidence(text, keywords, max_count=3):
    sentences = split_sentences(text)
    evidence = []

    for sentence in sentences:
        hit_count = sum(1 for keyword in keywords if keyword in sentence)

        if hit_count >= 1:
            evidence.append(sentence)

    return evidence[:max_count]


def evaluate_checklist_item(text, item):
    required_keywords = item["필수키워드"]
    optional_keywords = item["보조키워드"]

    required_hits = [k for k in required_keywords if k in text]
    optional_hits = [k for k in optional_keywords if k in text]

    all_keywords = required_keywords + optional_keywords
    evidence = find_evidence(text, all_keywords)

    required_ratio = len(required_hits) / len(required_keywords)
    optional_count = len(optional_hits)

    score = 0
    score += len(required_hits) * 2
    score += len(optional_hits) * 1

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
        "발견된 필수키워드": ", ".join(required_hits) if required_hits else "없음",
        "발견된 보조키워드": ", ".join(optional_hits) if optional_hits else "없음",
        "근거 문장": " / ".join(evidence) if evidence else "관련 문장 발견 안 됨",
        "수정권고": recommendation
    }


def evaluate_all_checklists(text):
    results = []

    for item in CHECKLIST:
        result = evaluate_checklist_item(text, item)
        results.append(result)

    return pd.DataFrame(results)


# =========================================================
# 6. 모호표현 탐지
# =========================================================

def detect_vague_expressions(text):
    sentences = split_sentences(text)
    results = []

    for sentence in sentences:
        found_words = [word for word in VAGUE_WORDS if word in sentence]

        if found_words:
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
# 7. 엑셀 저장
# =========================================================

def save_excel(checklist_df, vague_df):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(OUTPUT_DIR, f"시방서_체크리스트_검토결과_{now}.xlsx")

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        checklist_df.to_excel(writer, sheet_name="체크리스트 검토", index=False)
        vague_df.to_excel(writer, sheet_name="모호표현 검토", index=False)

        summary_df = pd.DataFrame({
            "항목": ["총 검토항목", "충족", "미흡", "누락", "모호표현 발견"],
            "개수": [
                len(checklist_df),
                len(checklist_df[checklist_df["판단"] == "충족"]),
                len(checklist_df[checklist_df["판단"] == "미흡"]),
                len(checklist_df[checklist_df["판단"] == "누락"]),
                len(vague_df)
            ]
        })

        summary_df.to_excel(writer, sheet_name="요약", index=False)

    return output_path


# =========================================================
# 8. UI 디자인
# =========================================================

st.title("🏗️ 체크리스트 기반 건설 시방서 검토 Agent")
st.caption("PDF 일반시방서를 업로드하면 체크리스트별 충족 / 미흡 / 누락 여부를 자동 판단합니다.")

st.markdown("---")

with st.sidebar:
    st.header("⚙️ 검토 기준")

    st.markdown("""
    ### 판단 기준

    **충족**
    - 필수 키워드가 모두 확인됨
    - 보조 키워드가 1개 이상 확인됨

    **미흡**
    - 필수 키워드가 일부만 확인됨

    **누락**
    - 필수 키워드가 거의 확인되지 않음
    """)

    st.markdown("---")

    st.info(
        "현재 버전은 키워드 기반 Rule-Based 판단입니다. "
        "추후 Retrieval Agent 또는 LLM Agent와 연결하면 근거 문장 판단 정확도를 높일 수 있습니다."
    )


uploaded_pdf = st.file_uploader(
    "검토할 일반시방서 PDF를 업로드하세요.",
    type=["pdf"]
)


if uploaded_pdf is not None:
    with st.spinner("PDF 텍스트 추출 및 체크리스트 검토 중입니다..."):
        raw_text = extract_text_from_pdf(uploaded_pdf)
        text = clean_text(raw_text)

        if len(text) < 50:
            st.error("PDF에서 텍스트를 충분히 추출하지 못했습니다. 스캔본 PDF일 가능성이 있습니다.")
            st.stop()

        checklist_df = evaluate_all_checklists(text)
        vague_df = detect_vague_expressions(text)
        excel_path = save_excel(checklist_df, vague_df)

    total_count = len(checklist_df)
    satisfied_count = len(checklist_df[checklist_df["판단"] == "충족"])
    insufficient_count = len(checklist_df[checklist_df["판단"] == "미흡"])
    missing_count = len(checklist_df[checklist_df["판단"] == "누락"])
    vague_count = len(vague_df)

    st.success("검토가 완료되었습니다.")

    st.markdown("## 📌 검토 요약")

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("총 검토항목", f"{total_count}개")
    col2.metric("충족", f"{satisfied_count}개")
    col3.metric("미흡", f"{insufficient_count}개")
    col4.metric("누락", f"{missing_count}개")
    col5.metric("모호표현", f"{vague_count}개")

    st.markdown("---")

    # 판단 결과 그래프
    st.markdown("## 📊 판단 결과 시각화")

    status_count_df = checklist_df["판단"].value_counts().reset_index()
    status_count_df.columns = ["판단", "개수"]

    fig = px.pie(
        status_count_df,
        names="판단",
        values="개수",
        title="체크리스트 판단 비율"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 카테고리별 판단 현황
    category_status_df = checklist_df.groupby(["카테고리", "판단"]).size().reset_index(name="개수")

    fig2 = px.bar(
        category_status_df,
        x="카테고리",
        y="개수",
        color="판단",
        barmode="group",
        title="카테고리별 판단 결과"
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # 결과 필터
    st.markdown("## ✅ 체크리스트 검토 결과")

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

    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=450
    )

    st.markdown("---")

    # 누락/미흡 항목만 따로 보여주기
    st.markdown("## 🚨 보완 필요 항목")

    problem_df = checklist_df[checklist_df["판단"].isin(["미흡", "누락"])]

    if len(problem_df) == 0:
        st.success("미흡 또는 누락 항목이 없습니다.")
    else:
        for idx, row in problem_df.iterrows():
            with st.expander(f"[{row['판단']}] {row['카테고리']} - {row['검토항목']}"):
                st.write(f"**위험도:** {row['위험도']}")
                st.write(f"**발견된 필수키워드:** {row['발견된 필수키워드']}")
                st.write(f"**발견된 보조키워드:** {row['발견된 보조키워드']}")
                st.write(f"**근거 문장:** {row['근거 문장']}")
                st.warning(row["수정권고"])

    st.markdown("---")

    # 모호표현 결과
    st.markdown("## 📝 모호표현 검토 결과")

    if len(vague_df) == 0:
        st.success("모호표현이 발견되지 않았습니다.")
    else:
        st.dataframe(
            vague_df,
            use_container_width=True,
            height=350
        )

    st.markdown("---")

    # 원문 텍스트 확인
    with st.expander("📄 추출된 PDF 원문 텍스트 확인"):
        st.text_area(
            "추출 텍스트",
            raw_text[:10000],
            height=400
        )

    # 엑셀 다운로드
    with open(excel_path, "rb") as file:
        st.download_button(
            label="📥 엑셀 결과 다운로드",
            data=file,
            file_name=os.path.basename(excel_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("왼쪽 또는 위의 업로드 영역에서 PDF 파일을 업로드하면 검토가 시작됩니다.")

    st.markdown("""
    ### 사용 흐름

    1. 일반시방서 PDF 업로드  
    2. PDF 텍스트 자동 추출  
    3. 체크리스트별 키워드 탐지  
    4. 충족 / 미흡 / 누락 판단  
    5. 근거 문장 및 수정권고 확인  
    6. 엑셀 결과 다운로드  
    """)