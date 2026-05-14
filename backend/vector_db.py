import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="resume_embeddings")

model = None


def get_model():
    global model

    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

    return model


def add_resume_embedding(application_id, seeker_email, job_id, resume_text):
    embedding_model = get_model()
    embedding = embedding_model.encode(resume_text).tolist()

    collection.add(
        ids=[str(application_id)],
        embeddings=[embedding],
        documents=[resume_text[:3000]],
        metadatas=[{
            "application_id": application_id,
            "seeker_email": seeker_email,
            "job_id": job_id
        }]
    )

def search_resumes(query, applications):
    query_words = query.lower().split()

    matches = []

    for app in applications:

        searchable_text = f"""
        {app.get("matched_skills", "")}
        {app.get("missing_skills", "")}
        {app.get("ai_feedback", "")}
        {app.get("candidate_summary", "")}
        """.lower()

        score = 0

        for word in query_words:
            if word in searchable_text:
                score += 1

        if score > 0:
            matches.append({
                "application_id": app["id"],
                "semantic_match_score": min(score * 20, 100)
            })

    matches.sort(
        key=lambda x: x["semantic_match_score"],
        reverse=True
    )

    return matches[:5]