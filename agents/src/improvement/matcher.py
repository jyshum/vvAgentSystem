import numpy as np

MATCH_THRESHOLD = 0.5
WEAK_THRESHOLD = 0.3

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def build_page_text(page: dict) -> str:
    parts = [page.get("title", ""), page.get("h1", ""), page.get("first_paragraph", "")]
    return " ".join(p for p in parts if p).strip()


def classify_match(score: float) -> str:
    if score > MATCH_THRESHOLD:
        return "matched"
    elif score >= WEAK_THRESHOLD:
        return "weak"
    else:
        return "content_gap"


def match_queries_to_pages(pages: list[dict], queries: list[dict]) -> list[dict]:
    if not queries:
        return []

    if not pages:
        return [
            {
                "query": q["query"],
                "query_id": q["query_id"],
                "match_type": "content_gap",
                "matched_page_url": None,
                "similarity_score": 0.0,
                "bucket": q.get("bucket", ""),
            }
            for q in queries
        ]

    model = _get_model()

    page_texts = [build_page_text(p) for p in pages]
    query_texts = [q["query"] for q in queries]

    page_embeddings = model.encode(page_texts, convert_to_numpy=True, normalize_embeddings=True)
    query_embeddings = model.encode(query_texts, convert_to_numpy=True, normalize_embeddings=True)

    similarity_matrix = np.dot(query_embeddings, page_embeddings.T)

    results = []
    for i, q in enumerate(queries):
        best_page_idx = int(np.argmax(similarity_matrix[i]))
        best_score = float(similarity_matrix[i][best_page_idx])
        match_type = classify_match(best_score)

        results.append({
            "query": q["query"],
            "query_id": q["query_id"],
            "match_type": match_type,
            "matched_page_url": pages[best_page_idx]["url"] if match_type != "content_gap" else None,
            "similarity_score": round(best_score, 4),
            "bucket": q.get("bucket", ""),
        })

    return results
