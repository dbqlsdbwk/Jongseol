import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

import fitz  # PyMuPDF
import pandas as pd
from tqdm import tqdm


class CivilSpecParsingAgent:
    """
    토목공사 표준일반시방서 2016 전용 Parsing Agent

    역할:
    1. PDF에서 페이지별 텍스트 추출
    2. 장/절/시방번호/조항번호 구조 인식
    3. 조항 단위 데이터 생성
    4. 안전 관련 키워드 태깅
    5. JSON, Excel, CSV 저장
    """

    def __init__(self):
        self.safety_keywords = [
            "안전", "위험", "산업재해", "보건", "보호구", "안전관리계획",
            "유해", "위험방지", "유해 위험방지", "안전점검", "정밀안전점검",
            "안전표지", "출입금지", "응급조치", "중대재해", "재난", "비상대책",
            "울타리", "방호", "방호울타리", "낙하물", "굴착", "터파기",
            "붕괴", "침하", "매설물", "폭발물", "발파", "조명", "통로",
            "비계", "동바리", "거푸집", "지보공", "작업장", "작업환경",
            "화재", "도난", "소음", "보호시설", "교통안전", "안전장구",
            "재해예방", "기상예보", "태풍", "홍수", "호우", "구급약",
            "의무실", "낙하", "감전", "보호", "점검", "검사"
        ]

        self.patterns = {
            "page_header": re.compile(
                r"^제\s*\d+\s*장\s+.+\s+\d{5}\s*-?\s*\d+$"
            ),
            "chapter": re.compile(
                r"^제\s*\d+\s*장\s+.+$"
            ),
            "section": re.compile(
                r"^제\s*\d+\s*절\s+.+$"
            ),
            "spec": re.compile(
                r"^(?P<code>\d{5})\s+(?P<title>.+)$"
            ),
            "level_1": re.compile(
                r"^(?P<id>\d+)\.\s+(?P<title>.+)$"
            ),
            "level_2": re.compile(
                r"^(?P<id>\d+\.\d+)\s+(?P<title>.+)$"
            ),
            "level_3": re.compile(
                r"^(?P<id>\d+\.\d+\.\d+)\s+(?P<title>.+)$"
            ),
            "paren_num": re.compile(
                r"^\((?P<id>\d+)\)\s*(?P<title>.+)$"
            ),
            "korean_item": re.compile(
                r"^(?P<id>[가-힣])\.\s*(?P<title>.+)$"
            ),
            "paren_korean": re.compile(
                r"^\((?P<id>[가-힣])\)\s*(?P<title>.+)$"
            )
        }

    def run(self, pdf_path: str, output_dir: str = "output") -> List[Dict[str, Any]]:
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print("[1] PDF 텍스트 추출 중...")
        pages = self.extract_pdf_pages(pdf_path)

        print("[2] 텍스트 전처리 중...")
        cleaned_pages = self.clean_pages(pages)

        print("[3] 조항 구조 파싱 중...")
        clauses = self.parse_structure(cleaned_pages, source_file=pdf_path.name)

        print("[4] 후처리 및 안전 키워드 태깅 중...")
        clauses = self.postprocess_clauses(clauses)

        print("[5] 결과 저장 중...")
        self.save_outputs(clauses, output_dir)

        print(f"\n완료: 총 {len(clauses)}개 조항 추출")
        print(f"저장 위치: {output_dir.resolve()}")

        return clauses

    def extract_pdf_pages(self, pdf_path: Path) -> List[Dict[str, Any]]:
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

        doc = fitz.open(pdf_path)
        pages = []

        for page_index in tqdm(range(len(doc)), desc="PDF pages"):
            page = doc[page_index]
            text = page.get_text("text")

            pages.append({
                "page": page_index + 1,
                "text": text
            })

        doc.close()
        return pages

    def clean_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned_pages = []

        for page in pages:
            page_no = page["page"]
            text = page["text"]

            # 특수 공백 정리
            text = text.replace("\u00a0", " ")
            text = text.replace("\ufeff", "")
            text = text.replace("․", "·")
            text = text.replace("：", ":")
            text = text.replace("–", "-")

            raw_lines = text.splitlines()
            clean_lines = []

            for line in raw_lines:
                line = line.strip()

                if not line:
                    continue

                # 여러 공백 정리
                line = re.sub(r"\s+", " ", line)

                # 단독 페이지 번호 제거
                if re.fullmatch(r"\d+", line):
                    continue

                # 페이지 헤더 제거
                if self.patterns["page_header"].match(line):
                    continue

                # 너무 짧은 장식문자 제거
                if line in ["-", "－", "—"]:
                    continue

                clean_lines.append(line)

            cleaned_pages.append({
                "page": page_no,
                "lines": clean_lines
            })

        return cleaned_pages

    def parse_structure(
        self,
        pages: List[Dict[str, Any]],
        source_file: str
    ) -> List[Dict[str, Any]]:
        clauses = []

        current_chapter = None
        current_section = None
        current_spec_code = None
        current_spec_title = None

        current_clause = None

        # 상위 조항 경로 관리
        current_level_1 = None
        current_level_2 = None
        current_level_3 = None
        current_paren_num = None
        current_korean = None

        for page in pages:
            page_no = page["page"]

            for line in page["lines"]:
                line = line.strip()

                if not line:
                    continue

                # 장 인식
                if self.is_chapter(line):
                    current_chapter = line
                    continue

                # 절 인식
                if self.is_section(line):
                    current_section = line
                    continue

                # 시방번호 인식
                spec_match = self.patterns["spec"].match(line)
                if spec_match:
                    # 이전 조항 저장
                    if current_clause is not None:
                        clauses.append(self.finalize_clause(current_clause))

                    current_spec_code = spec_match.group("code").strip()
                    current_spec_title = spec_match.group("title").strip()

                    current_clause = None
                    current_level_1 = None
                    current_level_2 = None
                    current_level_3 = None
                    current_paren_num = None
                    current_korean = None
                    continue

                clause_info = self.detect_clause(line)

                if clause_info:
                    # 새 조항 시작 전 기존 조항 저장
                    if current_clause is not None:
                        clauses.append(self.finalize_clause(current_clause))

                    clause_type = clause_info["type"]
                    clause_id = clause_info["id"]
                    clause_title = clause_info["title"]
                    clause_level = clause_info["level"]

                    # 계층 업데이트
                    if clause_type == "level_1":
                        current_level_1 = f"{clause_id} {clause_title}"
                        current_level_2 = None
                        current_level_3 = None
                        current_paren_num = None
                        current_korean = None

                    elif clause_type == "level_2":
                        current_level_2 = f"{clause_id} {clause_title}"
                        current_level_3 = None
                        current_paren_num = None
                        current_korean = None

                    elif clause_type == "level_3":
                        current_level_3 = f"{clause_id} {clause_title}"
                        current_paren_num = None
                        current_korean = None

                    elif clause_type == "paren_num":
                        current_paren_num = f"({clause_id}) {clause_title}"
                        current_korean = None

                    elif clause_type == "korean_item":
                        current_korean = f"{clause_id}. {clause_title}"

                    elif clause_type == "paren_korean":
                        current_korean = f"({clause_id}) {clause_title}"

                    parent_path = [
                        x for x in [
                            current_level_1,
                            current_level_2,
                            current_level_3,
                            current_paren_num,
                            current_korean
                        ]
                        if x is not None
                    ]

                    current_clause = {
                        "doc_id": "civil_standard_spec_2016",
                        "source_file": source_file,
                        "page_start": page_no,
                        "page_end": page_no,
                        "chapter": current_chapter,
                        "section": current_section,
                        "spec_code": current_spec_code,
                        "spec_title": current_spec_title,
                        "clause_type": clause_type,
                        "clause_level": clause_level,
                        "clause_id": clause_id,
                        "clause_title": clause_title,
                        "parent_path": parent_path,
                        "content_lines": []
                    }

                else:
                    # 조항이 아닌 일반 본문
                    if current_clause is not None:
                        current_clause["content_lines"].append(line)
                        current_clause["page_end"] = page_no
                    else:
                        # 시방번호 이전의 일반 텍스트는 무시
                        continue

        if current_clause is not None:
            clauses.append(self.finalize_clause(current_clause))

        return clauses

    def is_chapter(self, line: str) -> bool:
        # "제 1 장 총 칙" 형태
        if self.patterns["chapter"].match(line):
            # 페이지 헤더성 라인은 이미 제거했지만, 혹시 01510 - 1 같은 게 붙으면 제외
            if re.search(r"\d{5}\s*-?\s*\d+$", line):
                return False
            return True
        return False

    def is_section(self, line: str) -> bool:
        return bool(self.patterns["section"].match(line))

    def detect_clause(self, line: str) -> Optional[Dict[str, Any]]:
        """
        조항번호 탐지.
        level_3부터 먼저 검사해야 1.1.1이 1.1로 잘못 잡히지 않음.
        """

        check_order = [
            ("level_3", 3),
            ("level_2", 2),
            ("level_1", 1),
            ("paren_num", 4),
            ("paren_korean", 6),
            ("korean_item", 5)
        ]

        for key, level in check_order:
            match = self.patterns[key].match(line)
            if match:
                clause_id = match.group("id").strip()
                title = match.group("title").strip()

                # 너무 이상한 제목 방지
                if not title:
                    return None

                return {
                    "type": key,
                    "level": level,
                    "id": clause_id,
                    "title": title
                }

        return None

    def finalize_clause(self, clause: Dict[str, Any]) -> Dict[str, Any]:
        content = " ".join(clause.get("content_lines", []))
        content = self.clean_content(content)

        raw_text = f"{clause.get('clause_id', '')} {clause.get('clause_title', '')} {content}".strip()

        clause["content"] = content
        clause["raw_text"] = raw_text

        clause.pop("content_lines", None)

        return clause

    def clean_content(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    def postprocess_clauses(self, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed = []

        for idx, clause in enumerate(clauses, start=1):
            full_text = " ".join([
                str(clause.get("spec_title") or ""),
                str(clause.get("clause_title") or ""),
                str(clause.get("content") or "")
            ])

            matched_keywords = self.find_safety_keywords(full_text)

            clause["block_id"] = idx
            clause["sentences"] = self.split_sentences(clause.get("content", ""))
            clause["matched_keywords"] = matched_keywords
            clause["is_safety_related"] = len(matched_keywords) > 0

            # 안전 파트 우선순위 태그
            clause["safety_priority"] = self.get_safety_priority(clause)

            # 검색용 텍스트
            clause["search_text"] = self.make_search_text(clause)

            processed.append(clause)

        return processed

    def find_safety_keywords(self, text: str) -> List[str]:
        matched = []

        for keyword in self.safety_keywords:
            if keyword in text:
                matched.append(keyword)

        # 중복 제거
        return sorted(list(set(matched)))

    def split_sentences(self, text: str) -> List[str]:
        if not text:
            return []

        # 한국어 시방서 문장 종결 중심 분리
        sentence_end_pattern = r"(?<=[다함됨임음요\.])\s+"
        sentences = re.split(sentence_end_pattern, text)

        result = []
        for s in sentences:
            s = s.strip()
            if len(s) >= 2:
                result.append(s)

        return result

    def get_safety_priority(self, clause: Dict[str, Any]) -> int:
        """
        안전 검토에 쓸 우선순위.
        낮을수록 중요.
        """
        spec_code = clause.get("spec_code")
        text = clause.get("search_text", "")

        if spec_code == "01510":
            return 1

        high_priority_codes = {
            "01410",  # 임시시설물 및 임시관제
            "02110",  # 구조물해체공
            "02120",  # 지중 구조물 철거공
            "02220",  # 일반토공
            "02240",  # 물푸기 및 가배수
            "02250",  # 터파기 지보공
            "04110",  # 동바리공
            "04120",  # 거푸집공
            "04130"   # 철근공
        }

        if spec_code in high_priority_codes and clause.get("is_safety_related"):
            return 2

        if clause.get("is_safety_related"):
            return 3

        return 9

    def make_search_text(self, clause: Dict[str, Any]) -> str:
        parts = [
            clause.get("chapter"),
            clause.get("section"),
            clause.get("spec_code"),
            clause.get("spec_title"),
            clause.get("clause_id"),
            clause.get("clause_title"),
            " > ".join(clause.get("parent_path", [])),
            clause.get("content")
        ]

        return " ".join([str(p) for p in parts if p])

    def save_outputs(self, clauses: List[Dict[str, Any]], output_dir: Path):
        json_path = output_dir / "parsed_spec_all.json"
        csv_path = output_dir / "parsed_spec_all.csv"
        xlsx_path = output_dir / "parsed_spec_all.xlsx"

        safety_json_path = output_dir / "parsed_spec_safety_only.json"
        safety_xlsx_path = output_dir / "parsed_spec_safety_only.xlsx"

        # JSON 저장
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(clauses, f, ensure_ascii=False, indent=2)

        # DataFrame 변환
        df = pd.DataFrame(clauses)

        # parent_path, sentences, matched_keywords 리스트를 문자열로 변환
        for col in ["parent_path", "sentences", "matched_keywords"]:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: " | ".join(x) if isinstance(x, list) else x
                )

        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        df.to_excel(xlsx_path, index=False)

        # 안전 관련만 따로 저장
        safety_clauses = [
            c for c in clauses
            if c.get("is_safety_related") is True
        ]

        with open(safety_json_path, "w", encoding="utf-8") as f:
            json.dump(safety_clauses, f, ensure_ascii=False, indent=2)

        safety_df = pd.DataFrame(safety_clauses)

        if not safety_df.empty:
            for col in ["parent_path", "sentences", "matched_keywords"]:
                if col in safety_df.columns:
                    safety_df[col] = safety_df[col].apply(
                        lambda x: " | ".join(x) if isinstance(x, list) else x
                    )

            safety_df.to_excel(safety_xlsx_path, index=False)

        print(f"- 전체 JSON: {json_path}")
        print(f"- 전체 CSV: {csv_path}")
        print(f"- 전체 Excel: {xlsx_path}")
        print(f"- 안전 관련 JSON: {safety_json_path}")
        print(f"- 안전 관련 Excel: {safety_xlsx_path}")