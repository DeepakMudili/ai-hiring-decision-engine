const API_URL = "https://ai-hiring-decision-engine.onrender.com";


function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}


/* =========================
   REGISTER
========================= */

async function register() {

    const name = document.getElementById("registerName").value;
    const email = document.getElementById("registerEmail").value;
    const password = document.getElementById("registerPassword").value;
    const role = document.getElementById("registerRole").value;

    if (!name || !email || !password || !role) {
        alert("Please fill all fields");
        return;
    }

    const formData = new FormData();

    formData.append("name", name);
    formData.append("email", email);
    formData.append("password", password);
    formData.append("role", role);

    const response = await fetch(`${API_URL}/register`, {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (data.message) {
        document.getElementById("registerResult").innerHTML =
            `<p>${data.message}</p>`;

        setTimeout(() => {
            window.location.href = "index.html";
        }, 1000);

    } else {
        document.getElementById("registerResult").innerHTML =
            `<p>${data.error}</p>`;
    }
}


/* =========================
   LOGIN
========================= */

async function login() {

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    if (!email || !password) {
        alert("Please enter email and password");
        return;
    }

    const formData = new FormData();

    formData.append("email", email);
    formData.append("password", password);

    const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (data.message) {

        localStorage.setItem("userEmail", data.email);
        localStorage.setItem("userRole", data.role);
        localStorage.setItem("userName", data.name);

        if (data.role === "job_seeker") {
            window.location.href = "seeker.html";
        } else {
            window.location.href = "interviewer.html";
        }

    } else {
        document.getElementById("loginResult").innerHTML =
            `<p>${data.error}</p>`;
    }
}


/* =========================
   POST JOB
========================= */

async function postJob() {

    const title = document.getElementById("jobTitle").value;
    const description = document.getElementById("jobDescription").value;
    const vacancies = document.getElementById("jobVacancies").value;

    const postedBy = localStorage.getItem("userEmail");

    if (!title || !description || !vacancies) {
        alert("Please enter job title, description, and vacancies");
        return;
    }

    const formData = new FormData();

    formData.append("title", title);
    formData.append("description", description);
    formData.append("posted_by", postedBy);
    formData.append("vacancies", vacancies);

    const response = await fetch(`${API_URL}/post-job`, {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    document.getElementById("jobPostResult").innerHTML =
        `<p>${data.message}</p>`;

    document.getElementById("jobTitle").value = "";
    document.getElementById("jobDescription").value = "";
    document.getElementById("jobVacancies").value = "";

    loadPostedJobs();
}


/* =========================
   LOAD JOBS FOR JOB SEEKER
========================= */

async function loadJobs() {

    const response = await fetch(`${API_URL}/jobs`);

    const data = await response.json();

    let html = "";

    data.jobs.forEach(job => {

        html += `
        <div class="job-card">

            <h3>${job.title}</h3>

            <p>${job.description}</p>

            <p><strong>Vacancies:</strong> ${job.vacancies}</p>

            <input type="file" id="resume_${job.id}" accept="application/pdf">

            <button onclick="applyJob(${job.id})">
                Apply
            </button>

        </div>
        `;
    });

    document.getElementById("jobsContainer").innerHTML = html;
}


/* =========================
   APPLY JOB
========================= */

async function applyJob(jobId) {

    const fileInput = document.getElementById(`resume_${jobId}`);
    const file = fileInput.files[0];

    if (!file) {
        alert("Please upload resume PDF");
        return;
    }

    const email = localStorage.getItem("userEmail");

    const formData = new FormData();

    formData.append("seeker_email", email);
    formData.append("job_id", jobId);
    formData.append("file", file);

    alert("Application submitted. AI is analyzing your resume. Please wait.");

    const response = await fetch(`${API_URL}/apply`, {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    alert(data.message || data.error);

    loadMyStatus();
}


/* =========================
   MY APPLICATION STATUS
========================= */

async function loadMyStatus() {

    const email = localStorage.getItem("userEmail");

    const response = await fetch(`${API_URL}/my-status/${email}`);

    const data = await response.json();

    let html = "";

    data.applications.forEach(app => {

        html += `
        <div class="job-card">

            <h3>${app.job_title}</h3>

            <p>Status: <strong>${app.status}</strong></p>

        </div>
        `;
    });

    document.getElementById("statusContainer").innerHTML = html;
}


/* =========================
   LOAD POSTED JOBS
========================= */

async function loadPostedJobs() {

    const response = await fetch(`${API_URL}/jobs`);

    const data = await response.json();

    const interviewerEmail = localStorage.getItem("userEmail");

    let html = "";

    data.jobs.forEach(job => {

        if (job.posted_by === interviewerEmail) {

            html += `
            <div class="job-card">

                <h3>${job.title}</h3>

                <p>${job.description}</p>

                <p><strong>Vacancies:</strong> ${job.vacancies}</p>
                <p><strong>Selected:</strong> ${job.selected_count}</p>
                <p><strong>Remaining:</strong> ${job.remaining}</p>

                <button onclick="deleteJob(${job.id})">
                    Delete Job
                </button>

            </div>
            `;
        }
    });

    document.getElementById("postedJobsContainer").innerHTML = html;
}


/* =========================
   DELETE JOB
========================= */

async function deleteJob(jobId) {

    const confirmDelete = confirm(
        "Are you sure you want to delete this job?"
    );

    if (!confirmDelete) {
        return;
    }

    const response = await fetch(`${API_URL}/delete-job/${jobId}`, {
        method: "DELETE"
    });

    const data = await response.json();

    alert(data.message || data.error);

    loadPostedJobs();
    loadApplications();
}


/* =========================
   LOAD APPLICATIONS
========================= */
async function loadApplications() {

    const response = await fetch(`${API_URL}/applications`);

    const data = await response.json();

    const interviewerEmail = localStorage.getItem("userEmail");

    let html = "";

    data.applications.forEach(app => {

        if (
            app.posted_by === interviewerEmail &&
            app.status !== "Rejected" &&
            app.status !== "Selected"
        ) {

            html += `
            <div class="job-card">

                <h3>${app.job_title}</h3>

                <p><strong>Application ID:</strong> ${app.id}</p>
                <p><strong>Candidate:</strong> ${app.seeker_email}</p>

                <p><strong>AI Resume Score:</strong> ${app.resume_score}/50</p>
                <p><strong>Recruiter Score:</strong> ${app.interview_score}/50</p>
                <p><strong>Final Score:</strong> ${app.final_score}/100</p>
                <p><strong>Current Status:</strong> ${app.status}</p>

                <hr>

                <p><strong>Matched Skills:</strong> ${app.matched_skills || "New AI analysis required"}</p>
                <p><strong>Missing Skills:</strong> ${app.missing_skills || "New AI analysis required"}</p>
                <p><strong>AI Feedback:</strong> ${app.ai_feedback || "New AI analysis required"}</p>

                <input
                    type="number"
                    id="interview_${app.id}"
                    placeholder="Recruiter Score out of 50"
                    min="0"
                    max="50"
                >

                <button onclick="finalDecision(${app.id})">
                    Submit Final Decision
                </button>

            </div>
            `;
        }
    });

    if (html === "") {
        html = "<p>No active applications to review.</p>";
    }

    document.getElementById("applicationsContainer").innerHTML = html;
}


/* =========================
   FINAL DECISION
========================= */

async function finalDecision(applicationId) {

    const interviewScore = document.getElementById(
        `interview_${applicationId}`
    ).value;

    if (interviewScore === "") {
        alert("Please enter recruiter score");
        return;
    }

    if (interviewScore < 0 || interviewScore > 50) {
        alert("Recruiter score must be between 0 and 50");
        return;
    }

    const formData = new FormData();

    formData.append("application_id", applicationId);
    formData.append("interview_score", interviewScore);

    const response = await fetch(`${API_URL}/final-decision`, {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (data.error) {
        alert(data.error);
    } else {
        alert(
            `AI Score: ${data.ai_resume_score}/50\n` +
            `Recruiter Score: ${data.recruiter_score}/50\n` +
            `Final Score: ${data.final_score}/100\n` +
            `Status: ${data.status}`
        );
    }

    loadApplications();
    loadPostedJobs();
}

async function loadSelectedCandidates() {

    const response = await fetch(`${API_URL}/applications`);

    const data = await response.json();

    const interviewerEmail = localStorage.getItem("userEmail");

    let html = "";

    data.applications.forEach(app => {

        if (
            app.posted_by === interviewerEmail &&
            app.status === "Selected"
        ) {

            html += `
            <div class="job-card">

                <h3>${app.job_title}</h3>

                <p><strong>Candidate:</strong> ${app.seeker_email}</p>
                <p><strong>AI Resume Score:</strong> ${app.resume_score}/50</p>
                <p><strong>Recruiter Score:</strong> ${app.interview_score}/50</p>
                <p><strong>Final Score:</strong> ${app.final_score}/100</p>
                <p><strong>Status:</strong> ${app.status}</p>

            </div>
            `;
        }
    });

    if (html === "") {
        html = "<p>No selected candidates yet.</p>";
    }

    document.getElementById("selectedCandidatesContainer").innerHTML = html;
}