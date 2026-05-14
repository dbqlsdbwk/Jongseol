import json
from pathlib import Path


def search_spec(keyword, json_path="output/parsed_spec_all.json", safety_only=True):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []

    for item in data:
        if safety_only and not item.get("is_safety_related"):
            continue

        search_text = item.get("search_text", "")

        if keyword in search_text:
            results.append(item)

    results = sorted(
        results,
        key=lambda x: (
            x.get("safety_priority", 9),
            x.get("spec_code") or "",
            x.get("page_start") or 9999
        )
    )

    return results


if __name__ == "__main__":
    keyword = "굴착"
    results = search_spec(keyword)

    print(f"검색어: {keyword}")
    print(f"검색 결과: {len(results)}개")
    print("=" * 80)

    for r in results[:20]:
        print(f"[우선순위 {r.get('safety_priority')}] "
              f"{r.get('spec_code')} {r.get('spec_title')} / "
              f"{r.get('clause_id')} {r.get('clause_title')}")
        print(f"page: {r.get('page_start')}~{r.get('page_end')}")
        print(f"keywords: {r.get('matched_keywords')}")
        print(r.get("content")[:300])
        print("-" * 80)