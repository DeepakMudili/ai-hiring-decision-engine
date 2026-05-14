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

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailPattern.test(email)) {
        alert("Please enter a valid email address");
        return;
    }

    const passwordPattern =
        /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).{8,}$/;

    if (!passwordPattern.test(password)) {
        alert(
            "Password must be at least 8 characters and include uppercase letter, lowercase letter, number, and special character."
        );
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
            `<p class="success">${data.message}</p>`;

        setTimeout(() => {
            window.location.href = "index.html";
        }, 1000);

    } else {
        document.getElementById("registerResult").innerHTML =
            `<p class="error">${data.error}</p>`;
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
            `<p class="error">${data.error}</p>`;
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
        `<p class="success">${data.message || data.error}</p>`;

    document.getElementById("jobTitle").value = "";
    document.getElementById("jobDescription").value = "";
    document.getElementById("jobVacancies").value = "";

    loadPostedJobs();
    loadAnalytics();
}


/* =========================
   LOAD JOBS FOR SEEKER
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

    if (html === "") {
        html = "<p>No jobs available.</p>";
    }

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
   MY STATUS
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

    if (html === "") {
        html = "<p>No applications found.</p>";
    }

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

                <button class="danger-btn" onclick="deleteJob(${job.id})">
                    Delete Job
                </button>

            </div>
            `;
        }
    });

    if (html === "") {
        html = "<p>No posted jobs found.</p>";
    }

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
    loadAnalytics();
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
            html += applicationCard(app, true, true);
        }
    });

    if (html === "") {
        html = "<p>No active applications to review.</p>";
    }

    document.getElementById("applicationsContainer").innerHTML = html;
}


/* =========================
   APPLICATION CARD
========================= */

function applicationCard(app, showDecision, showGenerateQuestions) {

    return `
    <div class="job-card">

        <h3>${app.job_title}</h3>

        <p><strong>Application ID:</strong> ${app.id}</p>

        <p><strong>Candidate:</strong> ${app.seeker_email}</p>

        ${app.resume_url ? `
            <p>
                <a class="resume-link" href="${app.resume_url}" target="_blank">
                    View Resume
                </a>
            </p>
        ` : `
            <p><strong>Resume:</strong> Not available</p>
        `}

        <p><strong>AI Resume Score:</strong> ${app.resume_score}/50</p>

        <p><strong>Recruiter Score:</strong> ${app.interview_score}/50</p>

        <p><strong>Final Score:</strong> ${app.final_score}/100</p>

        <p><strong>Status:</strong> ${app.status}</p>

        <hr>

        <p><strong>Candidate Summary:</strong>
        ${app.candidate_summary || "Not available"}
        </p>

        <p><strong>Matched Skills:</strong>
        ${app.matched_skills || "Not available"}
        </p>

        <p><strong>Missing Skills:</strong>
        ${app.missing_skills || "Not available"}
        </p>

        <p><strong>AI Feedback:</strong>
        ${app.ai_feedback || "Not available"}
        </p>

        ${showGenerateQuestions ? `
            <button onclick="generateQuestions(${app.id})">
                Generate Interview Questions
            </button>

            <div id="questions_${app.id}" class="questions-box"></div>
        ` : ""}

        ${showDecision ? decisionSection(app) : ""}

    </div>
    `;
}


function decisionSection(app) {

    if (
        app.final_score !== null &&
        app.final_score !== undefined &&
        app.final_score !== 0
    ) {
        return `
        <p><strong>Final Decision Already Submitted</strong></p>
        `;
    }

    return `
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
    `;
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
    loadAnalytics();
}


/* =========================
   SELECTED CANDIDATES
========================= */

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
            html += applicationCard(app, false, false);
        }
    });

    if (html === "") {
        html = "<p>No selected candidates yet.</p>";
    }

    document.getElementById("selectedCandidatesContainer").innerHTML = html;
}


function toggleSelectedCandidates() {

    const section = document.getElementById("selectedCandidatesSection");

    if (section.style.display === "none") {
        section.style.display = "block";
        loadSelectedCandidates();
    } else {
        section.style.display = "none";
    }
}


/* =========================
   SEMANTIC SEARCH
========================= */
async function semanticSearch() {

    const query = document.getElementById("semanticSearchInput").value;
    const button = document.getElementById("semanticSearchBtn");

    if (!query) {
        alert("Please enter search text");
        return;
    }

    button.innerText = "Searching...";
    button.disabled = true;

    try {
        const response = await fetch(
            `${API_URL}/semantic-search?query=${encodeURIComponent(query)}`
        );

        const data = await response.json();

        let html = "";

        if (data.matches && data.matches.length > 0) {
            data.matches.forEach(match => {
                html += `
                <div class="job-card">
                    <h3>${match.job_title}</h3>
                    <p><strong>Candidate:</strong> ${match.candidate}</p>
                    <p><strong>AI Score:</strong> ${match.ai_score}/50</p>
                    <p><strong>Semantic Match:</strong> ${match.semantic_match_score}%</p>
                    <p><strong>Status:</strong> ${match.status}</p>
                    <p><strong>Matched Skills:</strong> ${match.matched_skills || "Not available"}</p>
                    <p><strong>Missing Skills:</strong> ${match.missing_skills || "Not available"}</p>

                    ${match.resume_url ? `
                        <p>
                            <a class="resume-link" href="${match.resume_url}" target="_blank">
                                View Resume
                            </a>
                        </p>
                    ` : ""}
                </div>
                `;
            });
        } else {
            html = "<p>No semantic matches found.</p>";
        }

        document.getElementById("semanticSearchContainer").innerHTML = html;

    } catch (error) {
        alert("Semantic search failed. Please try again.");
    }

    button.innerText = "Search Candidates";
    button.disabled = false;
}


/* =========================
   GENERATE QUESTIONS
========================= */
async function generateQuestions(applicationId) {

    const button = event.target;
    const originalText = button.innerText;

    button.innerText = "Generating...";
    button.disabled = true;

    const formData = new FormData();
    formData.append("application_id", applicationId);

    try {
        const response = await fetch(`${API_URL}/generate-questions`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        const box = document.getElementById(`questions_${applicationId}`);
        box.style.display = "block";

        if (data.questions) {
            box.innerHTML = `
                <h4>AI Interview Questions</h4>
                <pre>${data.questions}</pre>
            `;
        } else {
            box.innerHTML = `<p>${data.error}</p>`;
        }

    } catch (error) {
        alert("Question generation failed. Please try again.");
    }

    button.innerText = originalText;
    button.disabled = false;
}
/* =========================
   ANALYTICS
========================= */

async function loadAnalytics() {

    const response = await fetch(`${API_URL}/analytics`);
    const data = await response.json();

    if (data.error) {
        document.getElementById("analyticsContainer").innerHTML =
            `<p>${data.error}</p>`;
        return;
    }

    document.getElementById("analyticsContainer").innerHTML = `
    <div class="analytics-grid">

        <div class="analytics-card">
            <h3>${data.total_jobs}</h3>
            <p>Total Jobs</p>
        </div>

        <div class="analytics-card">
            <h3>${data.total_applications}</h3>
            <p>Total Applications</p>
        </div>

        <div class="analytics-card">
            <h3>${data.selected}</h3>
            <p>Selected</p>
        </div>

        <div class="analytics-card">
            <h3>${data.rejected}</h3>
            <p>Rejected</p>
        </div>

        <div class="analytics-card">
            <h3>${data.on_hold}</h3>
            <p>On Hold</p>
        </div>

        <div class="analytics-card">
            <h3>${data.under_review}</h3>
            <p>Under Review</p>
        </div>

        <div class="analytics-card">
            <h3>${data.average_ai_score}</h3>
            <p>Avg AI Score</p>
        </div>

    </div>
    `;
}


/* =========================
   RECRUITER COPILOT
========================= */
async function askRecruiterCopilot() {

    const question = document.getElementById("copilotQuestion").value;
    const recruiterEmail = localStorage.getItem("userEmail");
    const button = document.getElementById("copilotBtn");

    if (!question) {
        alert("Please enter a question");
        return;
    }

    button.innerText = "Thinking...";
    button.disabled = true;

    const formData = new FormData();
    formData.append("question", question);
    formData.append("recruiter_email", recruiterEmail);

    try {
        const response = await fetch(`${API_URL}/recruiter-copilot`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        const box = document.getElementById("copilotAnswer");
        box.style.display = "block";

        if (data.answer) {
            box.innerHTML = `
                <h4>Copilot Answer</h4>
                <pre>${data.answer}</pre>
            `;
        } else {
            box.innerHTML = `<p>${data.error}</p>`;
        }

    } catch (error) {
        alert("Recruiter copilot failed. Please try again.");
    }

    button.innerText = "Ask Copilot";
    button.disabled = false;
}