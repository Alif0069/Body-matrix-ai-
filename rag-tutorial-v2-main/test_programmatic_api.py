import unittest
from pathlib import Path

from populate_database import calculate_chunk_ids
from query_data import query_rag, query_rag_response


class FakeDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


class FakeDB:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def similarity_search_with_score(self, query_text, k):
        self.calls.append((query_text, k))
        return self.results


class FakeModel:
    def __init__(self, response_text):
        self.response_text = response_text
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.response_text


class ProgrammaticApiTests(unittest.TestCase):
    def test_query_rag_response_returns_structured_payload(self):
        doc = FakeDocument(
            "Relevant chunk",
            {
                "id": "data/file.pdf:0:0",
                "source": "data/file.pdf",
                "page": 0,
            },
        )
        db = FakeDB([(doc, 0.12)])
        model = FakeModel("structured answer")

        response = query_rag_response(
            "Where should I go?",
            db=db,
            model=model,
            k=3,
        )

        self.assertEqual(response.response_text, "structured answer")
        self.assertEqual(response.sources, ["data/file.pdf:0:0"])
        self.assertEqual(db.calls, [("Where should I go?", 3)])
        self.assertEqual(model.prompts, [response.prompt])
        self.assertIn("Relevant chunk", response.context_text)
        self.assertIn("Where should I go?", response.prompt)

    def test_query_rag_keeps_text_return_value(self):
        doc = FakeDocument("Chunk", {"id": "data/file.pdf:0:0"})
        db = FakeDB([(doc, 0.42)])
        model = FakeModel("text only")

        response_text = query_rag("Question?", db=db, model=model)

        self.assertEqual(response_text, "text only")

    def test_calculate_chunk_ids_normalizes_absolute_paths(self):
        project_root = Path(__file__).resolve().parent
        source_path = project_root / "data" / "monopoly.pdf"

        chunks = [
            FakeDocument("", {"source": str(source_path), "page": 2}),
            FakeDocument("", {"source": str(source_path), "page": 2}),
        ]

        calculate_chunk_ids(chunks, source_root=project_root)

        self.assertEqual(chunks[0].metadata["id"], "data/monopoly.pdf:2:0")
        self.assertEqual(chunks[1].metadata["id"], "data/monopoly.pdf:2:1")


if __name__ == "__main__":
    unittest.main()
