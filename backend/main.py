import uuid

from fastapi import FastAPI, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware

from database import supabase
from business_logic import (
    hash_password,
    verify_password,
    extract_pdf_text,
    calculate_resume_ai_analysis,
    calculate_final_score,
    generate_interview_questions,
    recruiter_copilot_answer
)

from vector_db import add_resume_embedding, search_resumes


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "AI Hiring Intelligence Platform Backend Running"
    }


@app.post("/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    try:
        if role not in ["job_seeker", "interviewer"]:
            return {
                "error": "Role must be job_seeker, interviewer, or admin"
            }

        existing = supabase.table("users").select("*").eq(
            "email",
            email
        ).execute()

        if existing.data:
            return {"error": "Email already exists"}

        hashed_password = hash_password(password)

        supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role
        }).execute()

        return {"message": "Account created successfully"}

    except Exception as e:
        return {"error": str(e)}


@app.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        result = supabase.table("users").select("*").eq(
            "email",
            email
        ).execute()

        if not result.data:
            return {"error": "Invalid email"}

        user = result.data[0]

        if not verify_password(password, user["password"]):
            return {"error": "Invalid password"}

        return {
            "message": "Login successful",
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }

    except Exception as e:
        return {"error": str(e)}


@app.post("/post-job")
async def post_job(
    title: str = Form(...),
    description: str = Form(...),
    posted_by: str = Form(...),
    vacancies: int = Form(...)
):
    try:
        supabase.table("jobs").insert({
            "title": title,
            "description": description,
            "posted_by": posted_by,
            "vacancies": vacancies
        }).execute()

        return {"message": "Job posted successfully"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/jobs")
async def get_jobs():
    try:
        jobs_result = supabase.table("jobs").select("*").execute()
        applications_result = supabase.table("applications").select("*").execute()

        jobs = jobs_result.data
        applications = applications_result.data

        all_jobs = []

        for job in jobs:
            selected_count = len([
                app for app in applications
                if app["job_id"] == job["id"]
                and app["status"] == "Selected"
            ])

            remaining = job["vacancies"] - selected_count

            all_jobs.append({
                "id": job["id"],
                "title": job["title"],
                "description": job["description"],
                "posted_by": job["posted_by"],
                "vacancies": job["vacancies"],
                "selected_count": selected_count,
                "remaining": remaining
            })

        return {"jobs": all_jobs}

    except Exception as e:
        return {"error": str(e)}


@app.delete("/delete-job/{job_id}")
async def delete_job(job_id: int):
    try:
        supabase.table("applications").delete().eq(
            "job_id",
            job_id
        ).execute()

        supabase.table("jobs").delete().eq(
            "id",
            job_id
        ).execute()

        return {"message": "Job deleted successfully"}

    except Exception as e:
        return {"error": str(e)}


@app.post("/apply")
async def apply_job(
    seeker_email: str = Form(...),
    job_id: int = Form(...),
    file: UploadFile = File(...)
):
    try:
        existing = supabase.table("applications").select("*").eq(
            "seeker_email",
            seeker_email
        ).eq(
            "job_id",
            job_id
        ).execute()

        if existing.data:
            return {
                "error": "You have already applied for this job."
            }

        job_result = supabase.table("jobs").select("*").eq(
            "id",
            job_id
        ).execute()

        if not job_result.data:
            return {"error": "Job not found"}

        job = job_result.data[0]

        file_bytes = await file.read()
        resume_text = extract_pdf_text(file_bytes)

        resume_file_name = (
            f"{uuid.uuid4()}_{file.filename}"
        )

        supabase.storage.from_("resumes").upload(
            resume_file_name,
            file_bytes,
            {
                "content-type": "application/pdf"
            }
        )

        resume_url = supabase.storage.from_("resumes").get_public_url(
            resume_file_name
        )

        ai_analysis = calculate_resume_ai_analysis(
            resume_text,
            job["description"]
        )

        insert_result = supabase.table("applications").insert({
            "seeker_email": seeker_email,
            "job_id": job_id,
            "resume_score": ai_analysis["score"],
            "interview_score": 0,
            "final_score": 0,
            "status": "Under Review",
            "matched_skills": ai_analysis["matched_skills"],
            "missing_skills": ai_analysis["missing_skills"],
            "ai_feedback": ai_analysis["feedback"],
            "candidate_summary": ai_analysis["candidate_summary"],
            "resume_url": resume_url
        }).execute()

        application_id = insert_result.data[0]["id"]

        add_resume_embedding(
            application_id,
            seeker_email,
            job_id,
            resume_text
        )

        return {
            "message": "Application submitted successfully"
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/applications")
async def get_applications():
    try:
        apps_result = supabase.table("applications").select("*").execute()
        jobs_result = supabase.table("jobs").select("*").execute()

        jobs = jobs_result.data
        applications = apps_result.data

        data = []

        for app_item in applications:
            job = next(
                (j for j in jobs if j["id"] == app_item["job_id"]),
                None
            )

            if job:
                data.append({
                    "id": app_item["id"],
                    "seeker_email": app_item["seeker_email"],
                    "job_id": app_item["job_id"],
                    "resume_score": app_item["resume_score"],
                    "interview_score": app_item["interview_score"],
                    "final_score": app_item["final_score"],
                    "status": app_item["status"],
                    "job_title": job["title"],
                    "posted_by": job["posted_by"],
                    "matched_skills": app_item.get("matched_skills"),
                    "missing_skills": app_item.get("missing_skills"),
                    "ai_feedback": app_item.get("ai_feedback"),
                    "candidate_summary": app_item.get("candidate_summary"),
                    "resume_url": app_item.get("resume_url")
                })

        ranked_data = sorted(
            data,
            key=lambda x: x.get("resume_score") or 0,
            reverse=True
        )

        return {"applications": ranked_data}

    except Exception as e:
        return {"error": str(e)}


@app.post("/final-decision")
async def final_decision(
    application_id: int = Form(...),
    interview_score: int = Form(...)
):
    try:
        if interview_score < 0 or interview_score > 50:
            return {
                "error": "Recruiter score must be between 0 and 50"
            }

        app_result = supabase.table("applications").select("*").eq(
            "id",
            application_id
        ).execute()

        if not app_result.data:
            return {"error": "Application not found"}

        application = app_result.data[0]

        final_score, status = calculate_final_score(
            application["resume_score"],
            interview_score
        )

        if status == "Invalid Score":
            return {
                "error": "Invalid score"
            }

        if status == "Selected":
            job_result = supabase.table("jobs").select("*").eq(
                "id",
                application["job_id"]
            ).execute()

            job = job_result.data[0]

            selected_result = supabase.table("applications").select("*").eq(
                "job_id",
                application["job_id"]
            ).eq(
                "status",
                "Selected"
            ).execute()

            if len(selected_result.data) >= job["vacancies"]:
                return {
                    "error": "Vacancy limit reached"
                }

        supabase.table("applications").update({
            "interview_score": interview_score,
            "final_score": final_score,
            "status": status
        }).eq(
            "id",
            application_id
        ).execute()

        return {
            "message": "Final decision updated",
            "ai_resume_score": application["resume_score"],
            "recruiter_score": interview_score,
            "final_score": final_score,
            "status": status
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/my-status/{email}")
async def my_status(email: str):
    try:
        apps_result = supabase.table("applications").select("*").eq(
            "seeker_email",
            email
        ).execute()

        jobs_result = supabase.table("jobs").select("*").execute()

        result = []

        for app_item in apps_result.data:
            job = next(
                (j for j in jobs_result.data if j["id"] == app_item["job_id"]),
                None
            )

            if job:
                result.append({
                    "job_title": job["title"],
                    "status": app_item["status"]
                })

        return {"applications": result}

    except Exception as e:
        return {"error": str(e)}

@app.get("/semantic-search")
async def semantic_search(query: str):
    try:
        matches = search_resumes(query, applications)

        applications_result = supabase.table("applications").select("*").execute()
        jobs_result = supabase.table("jobs").select("*").execute()

        applications = applications_result.data or []
        jobs = jobs_result.data or []

        enriched_matches = []

        for match in matches:
            application = next(
                (app for app in applications if app["id"] == match["application_id"]),
                None
            )

            if application:
                job = next(
                    (j for j in jobs if j["id"] == application["job_id"]),
                    None
                )

                enriched_matches.append({
                    "application_id": application["id"],
                    "candidate": application["seeker_email"],
                    "job_title": job["title"] if job else "Unknown",
                    "ai_score": application.get("resume_score", 0),
                    "status": application.get("status", "Unknown"),
                    "semantic_match_score": match.get("semantic_match_score", 0),
                    "resume_url": application.get("resume_url"),
                    "matched_skills": application.get("matched_skills"),
                    "missing_skills": application.get("missing_skills")
                })

        return {
            "query": query,
            "matches": enriched_matches
        }

    except Exception as e:
        print("Semantic Search Error:", str(e))
        return {
            "query": query,
            "matches": [],
            "error": f"Semantic search backend error: {str(e)}"
        }

@app.post("/generate-questions")
async def generate_questions(
    application_id: int = Form(...)
):
    try:
        app_result = supabase.table("applications").select("*").eq(
            "id",
            application_id
        ).execute()

        if not app_result.data:
            return {"error": "Application not found"}

        application = app_result.data[0]

        job_result = supabase.table("jobs").select("*").eq(
            "id",
            application["job_id"]
        ).execute()

        if not job_result.data:
            return {"error": "Job not found"}

        job_description = job_result.data[0]["description"]

        resume_context = f"""
Candidate Email: {application["seeker_email"]}
Matched Skills: {application.get("matched_skills")}
Missing Skills: {application.get("missing_skills")}
AI Feedback: {application.get("ai_feedback")}
Candidate Summary: {application.get("candidate_summary")}
"""

        questions = generate_interview_questions(
            resume_context,
            job_description
        )

        return {
            "application_id": application_id,
            "questions": questions
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/analytics")
async def analytics():
    try:
        jobs_result = supabase.table("jobs").select("*").execute()
        apps_result = supabase.table("applications").select("*").execute()

        applications = apps_result.data

        total_jobs = len(jobs_result.data)
        total_applications = len(applications)

        selected = len([
            app for app in applications
            if app["status"] == "Selected"
        ])

        rejected = len([
            app for app in applications
            if app["status"] == "Rejected"
        ])

        on_hold = len([
            app for app in applications
            if app["status"] == "On Hold"
        ])

        under_review = len([
            app for app in applications
            if app["status"] == "Under Review"
        ])

        avg_ai_score = 0

        if total_applications > 0:
            avg_ai_score = sum([
                app.get("resume_score") or 0
                for app in applications
            ]) / total_applications

        return {
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "selected": selected,
            "rejected": rejected,
            "on_hold": on_hold,
            "under_review": under_review,
            "average_ai_score": round(avg_ai_score, 2)
        }

    except Exception as e:
        return {"error": str(e)}
    
@app.post("/recruiter-copilot")
async def recruiter_copilot(
    question: str = Form(...),
    recruiter_email: str = Form(...)
):
    try:
        apps_result = supabase.table("applications").select("*").execute()
        jobs_result = supabase.table("jobs").select("*").execute()

        jobs = jobs_result.data or []
        applications = apps_result.data or []

        recruiter_data = []

        for app_item in applications:
            job = next(
                (j for j in jobs if j["id"] == app_item["job_id"]),
                None
            )

            if job and job["posted_by"] == recruiter_email:
                recruiter_data.append({
                    "candidate": app_item.get("seeker_email"),
                    "job_title": job.get("title"),
                    "ai_score": app_item.get("resume_score"),
                    "final_score": app_item.get("final_score"),
                    "status": app_item.get("status"),
                    "matched_skills": app_item.get("matched_skills"),
                    "missing_skills": app_item.get("missing_skills"),
                    "ai_feedback": app_item.get("ai_feedback"),
                    "candidate_summary": app_item.get("candidate_summary")
                })

        if not recruiter_data:
            return {
                "answer": "No candidate data found for your recruiter account yet. Post a job and ask candidates to apply first."
            }

        answer = recruiter_copilot_answer(question, recruiter_data)

        return {
            "answer": answer
        }

    except Exception as e:
        print("Recruiter Copilot Error:", str(e))
        return {
            "error": f"Recruiter copilot backend error: {str(e)}"
        }