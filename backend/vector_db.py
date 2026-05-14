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


def search_resumes(query, top_k=5):
    embedding_model = get_model()
    embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )

    matches = []

    if results and results.get("metadatas"):
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0]

        for index, metadata in enumerate(metadatas):
            distance = distances[index] if index < len(distances) else None
            match_score = 0

            if distance is not None:
                match_score = max(0, int((1 - distance) * 100))

            matches.append({
                "application_id": metadata.get("application_id"),
                "seeker_email": metadata.get("seeker_email"),
                "job_id": metadata.get("job_id"),
                "semantic_match_score": match_score
            })

    return matches