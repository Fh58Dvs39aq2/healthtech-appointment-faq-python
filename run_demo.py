import os

from src.faq_service import AppointmentQuestion, InfraiClient, patient_safe_suggestions


def embed(text: str) -> list[float]:
    # Replace with an embedding from the OpenAI-compatible /v1/embeddings endpoint.
    return [float((sum(map(ord, text)) % 100) / 100), 0.1, 0.2]


if __name__ == "__main__":
    client = InfraiClient()
    client.create_collection("appointment-faq", dimension=3)
    faq = {
        "question": "How do I prepare for a video visit?",
        "answer": "Have your medication list ready and check your camera and microphone before the visit.",
        "urgency": "routine",
    }
    client.upsert("appointment-faq", [{
        "id": "video-visit-preparation",
        "embedding": embed(faq["question"]),
        "metadata": faq,
    }])
    question = AppointmentQuestion(os.environ.get("FAQ_QUESTION", "How do I prepare for a video visit?"), "video")
    for suggestion in patient_safe_suggestions(question, client, embed):
        print(f"{suggestion.question}: {suggestion.answer}")
