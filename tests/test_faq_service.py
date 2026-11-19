from src.faq_service import AppointmentQuestion, patient_safe_suggestions


class FakeClient:
    def query(self, collection, embedding, top_k):
        return {"items": [{"metadata": {"question": "How do I prepare?", "answer": "Bring your medication list.", "urgency": "routine"}}, {"metadata": {"question": "I have chest pain", "answer": "Seek urgent care.", "urgency": "urgent"}}]}

    def rerank(self, query, candidates, top_k):
        return {"results": [{"text": "I have chest pain"}, {"text": "How do I prepare?"}]}


def test_urgent_faq_is_filtered_from_patient_suggestions():
    result = patient_safe_suggestions(AppointmentQuestion("What should I bring?", "clinic"), FakeClient(), lambda _: [0.1, 0.2, 0.3])
    assert [item.question for item in result] == ["How do I prepare?"]


def test_demo_provisions_faq_before_query(monkeypatch, capsys):
    import runpy
    from pathlib import Path
    from src import faq_service

    class EmptyAccountClient:
        def __init__(self):
            self.collections = {}

        def create_collection(self, name, dimension):
            assert name not in self.collections
            self.collections[name] = {"dimension": dimension, "vectors": []}

        def upsert(self, collection, vectors):
            stored = self.collections[collection]
            assert all(len(v["embedding"]) == stored["dimension"] for v in vectors)
            stored["vectors"] = vectors

        def query(self, collection, embedding, top_k):
            stored = self.collections[collection]
            assert len(embedding) == stored["dimension"]
            assert stored["vectors"]
            return {"items": stored["vectors"]}

        def rerank(self, query, candidates, top_k):
            return {"results": [{"text": text} for text in candidates[:top_k]]}

    monkeypatch.setattr(faq_service, "InfraiClient", EmptyAccountClient)
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "run_demo.py"), run_name="__main__")
    assert "How do I prepare for a video visit?" in capsys.readouterr().out
