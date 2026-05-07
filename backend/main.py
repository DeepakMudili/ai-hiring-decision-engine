from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from database import supabase
from business_logic import (
    hash_password,
    verify_password,
    extract_pdf_text,
    calculate_resume_ai_analysis,
    calculate_final_score
)

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
    return {"message": "Hiring Decision Engine Backend Running with Supabase"}


@app.post("/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    try:
        if role not in ["job_seeker", "interviewer"]:
            return {"error": "Role must be job_seeker or interviewer"}

        existing = supabase.table("users").select("*").eq("email", email).execute()

        if existing.data:
            return {"error": "Email already exists"}

        hashed_password = hash_password(password)

        result = supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role
        }).execute()

        return {
            "message": "Account created successfully",
            "data": result.data
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@app.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...)
):
    result = supabase.table("users").select("*").eq("email", email).execute()

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


@app.post("/post-job")
async def post_job(
    title: str = Form(...),
    description: str = Form(...),
    posted_by: str = Form(...),
    vacancies: int = Form(...)
):
    supabase.table("jobs").insert({
        "title": title,
        "description": description,
        "posted_by": posted_by,
        "vacancies": vacancies
    }).execute()

    return {"message": "Job posted successfully"}


@app.get("/jobs")
async def get_jobs():
    jobs_result = supabase.table("jobs").select("*").execute()
    applications_result = supabase.table("applications").select("*").execute()

    jobs = jobs_result.data
    applications = applications_result.data

    all_jobs = []

    for job in jobs:
        selected_count = len([
            app for app in applications
            if app["job_id"] == job["id"] and app["status"] == "Selected"
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


@app.delete("/delete-job/{job_id}")
async def delete_job(job_id: int):
    supabase.table("applications").delete().eq("job_id", job_id).execute()
    supabase.table("jobs").delete().eq("id", job_id).execute()

    return {"message": "Job deleted successfully"}


@app.post("/apply")
async def apply_job(
    seeker_email: str = Form(...),
    job_id: int = Form(...),
    file: UploadFile = None
):
    existing = supabase.table("applications") \
        .select("*") \
        .eq("seeker_email", seeker_email) \
        .eq("job_id", job_id) \
        .execute()

    if existing.data:
        return {"error": "You have already applied for this job."}

    if file is None:
        return {"error": "Resume file is required"}

    job_result = supabase.table("jobs").select("*").eq("id", job_id).execute()

    if not job_result.data:
        return {"error": "Job not found"}

    job = job_result.data[0]

    file_bytes = await file.read()
    resume_text = extract_pdf_text(file_bytes)

    ai_analysis = calculate_resume_ai_analysis(
        resume_text,
        job["description"]
    )

    supabase.table("applications").insert({
        "seeker_email": seeker_email,
        "job_id": job_id,
        "resume_score": ai_analysis["score"],
        "interview_score": 0,
        "final_score": 0,
        "status": "Under Review",
        "matched_skills": ai_analysis["matched_skills"],
        "missing_skills": ai_analysis["missing_skills"],
        "ai_feedback": ai_analysis["feedback"]
    }).execute()

    return {"message": "Application submitted successfully"}


@app.get("/applications")
async def get_applications():
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
                "ai_feedback": app_item.get("ai_feedback")
            })

    return {"applications": data}


@app.post("/final-decision")
async def final_decision(
    application_id: int = Form(...),
    interview_score: int = Form(...)
):
    if interview_score < 0 or interview_score > 50:
        return {"error": "Recruiter score must be between 0 and 50"}

    app_result = supabase.table("applications").select("*").eq("id", application_id).execute()

    if not app_result.data:
        return {"error": "Application not found"}

    application = app_result.data[0]

    final_score, status = calculate_final_score(
        application["resume_score"],
        interview_score
    )

    if status == "Invalid Score":
        return {"error": "Recruiter score must be between 0 and 50"}

    if status == "Selected":
        job_result = supabase.table("jobs").select("*").eq("id", application["job_id"]).execute()
        job = job_result.data[0]

        selected_result = supabase.table("applications") \
            .select("*") \
            .eq("job_id", application["job_id"]) \
            .eq("status", "Selected") \
            .execute()

        if len(selected_result.data) >= job["vacancies"]:
            return {"error": "Vacancy limit reached. Cannot select more candidates."}

    supabase.table("applications").update({
        "interview_score": interview_score,
        "final_score": final_score,
        "status": status
    }).eq("id", application_id).execute()

    return {
        "message": "Final decision updated",
        "ai_resume_score": application["resume_score"],
        "recruiter_score": interview_score,
        "final_score": final_score,
        "status": status
    }


@app.get("/my-status/{email}")
async def my_status(email: str):
    apps_result = supabase.table("applications").select("*").eq("seeker_email", email).execute()
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