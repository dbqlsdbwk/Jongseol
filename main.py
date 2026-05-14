from pathlib import Path
from parser_agent import CivilSpecParsingAgent


def main():
    input_pdf = Path("input") / "토목공사+표준일반시방서+2016.pdf"
    output_dir = Path("output")

    agent = CivilSpecParsingAgent()
    clauses = agent.run(
        pdf_path=str(input_pdf),
        output_dir=str(output_dir)
    )

    print("\n샘플 출력 5개")
    print("=" * 80)

    for clause in clauses[:5]:
        print(f"[{clause['block_id']}] "
              f"{clause.get('spec_code')} {clause.get('spec_title')} / "
              f"{clause.get('clause_id')} {clause.get('clause_title')}")
        print(f"page: {clause.get('page_start')}~{clause.get('page_end')}")
        print(f"safety: {clause.get('is_safety_related')}, "
              f"keywords: {clause.get('matched_keywords')}")
        print(f"content: {clause.get('content')[:150]}")
        print("-" * 80)


if __name__ == "__main__":
    main()