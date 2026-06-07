"use client";

import { useState, useEffect } from "react";

// Empty string = relative path. Next.js rewrites /api/* → FastAPI backend.
// Works identically in local dev (port 3000 → 8000) and on Vercel (→ Render backend).
const API_BASE = "";

export default function Dashboard() {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [jd, setJd] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [isJdLoading, setIsJdLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  // Authentication & Roles
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Register State
  const [isRegistering, setIsRegistering] = useState(false);
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerRole, setRegisterRole] = useState("Recruiter");
  const [registerName, setRegisterName] = useState("");
  const [showOtpScreen, setShowOtpScreen] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [verifyingEmail, setVerifyingEmail] = useState("");
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);

  // Job opening States
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");
  const [newJobTitle, setNewJobTitle] = useState("");
  const [newJobDescription, setNewJobDescription] = useState("");
  const [hiringManagerName, setHiringManagerName] = useState("");
  const [hiringManagerEmail, setHiringManagerEmail] = useState("");
  const [isJobCreating, setIsJobCreating] = useState(false);
  const [isCreatingNewJob, setIsCreatingNewJob] = useState(false);

  // Modals & States
  const [interviewDates, setInterviewDates] = useState<Record<string, string>>({});
  const [candidateEmails, setCandidateEmails] = useState<Record<string, string>>({});
  const [feedbackState, setFeedbackState] = useState<{candidateId: string, rating: number, text: string}>({candidateId: "", rating: 5, text: ""});
  
  // Navigation Tabs (Hiring Operations, Visualizer, Compliance Analytics)
  const [activeTab, setActiveTab] = useState<"operations" | "visualizer" | "compliance">("operations");

  // Selected candidate drawer for detailed AI analysis
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [candidateJourney, setCandidateJourney] = useState<any[]>([]);
  const [allAgentLogs, setAllAgentLogs] = useState<any[]>([]);

  // Load auth state from LocalStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    const savedRole = localStorage.getItem("role");
    const savedEmail = localStorage.getItem("email");
    if (savedToken && savedRole) {
      setToken(savedToken);
      setRole(savedRole);
      setEmail(savedEmail);
      fetchCandidatesWithToken(savedToken);
      fetchJobsWithToken(savedToken);
      fetchSystemLogsWithToken(savedToken);
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);
    try {
      const res = await fetch(`${API_BASE}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: loginEmail, password: loginPassword })
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("role", data.role);
        localStorage.setItem("email", data.email);
        setToken(data.access_token);
        setRole(data.role);
        setEmail(data.email);
        fetchCandidatesWithToken(data.access_token);
        fetchJobsWithToken(data.access_token);
        fetchSystemLogsWithToken(data.access_token);
      } else {
        alert("Login failed! Please check your credentials.");
      }
    } catch(err) {
      console.error("Login request error", err);
      alert("Cannot connect to the backend server. Make sure it's running!");
    }
    setIsLoggingIn(false);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!registerEmail.toLowerCase().endsWith("@gmail.com")) {
      alert("Only @gmail.com email addresses are allowed!");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          email: registerEmail, 
          password: registerPassword, 
          role: registerRole,
          name: registerName 
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.requires_verification) {
          setVerifyingEmail(data.email);
          setShowOtpScreen(true);
          alert("A 6-digit verification code has been sent to your Gmail. Please check your inbox!");
        } else {
          alert("Registration successful! You can now log in.");
          setLoginEmail(registerEmail);
          setLoginPassword(registerPassword);
          setIsRegistering(false);
          setRegisterEmail("");
          setRegisterPassword("");
          setRegisterName("");
        }
      } else {
        const data = await res.json();
        alert(`Registration failed: ${data.detail || "Check input details."}`);
      }
    } catch(err) {
      console.error("Register request error", err);
      alert("Cannot connect to the backend server. Make sure the email is valid and SMTP is running.");
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otpCode.length !== 6) {
      alert("Verification code must be exactly 6 digits.");
      return;
    }
    setIsVerifyingOtp(true);
    try {
      const res = await fetch(`${API_BASE}/api/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: verifyingEmail, code: otpCode })
      });
      if (res.ok) {
        alert("Email verification successful! You can now log in.");
        setLoginEmail(verifyingEmail);
        setLoginPassword(registerPassword);
        setShowOtpScreen(false);
        setIsRegistering(false);
        setRegisterEmail("");
        setRegisterPassword("");
        setRegisterName("");
        setOtpCode("");
        setVerifyingEmail("");
      } else {
        const data = await res.json();
        alert(`Verification failed: ${data.detail || "Invalid code."}`);
      }
    } catch (err) {
      console.error("OTP verification error", err);
      alert("Cannot connect to the backend server.");
    }
    setIsVerifyingOtp(false);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("email");
    setToken(null);
    setRole(null);
    setEmail(null);
    setCandidates([]);
    setJobs([]);
    setSelectedJobId("");
    setSelectedCandidateId(null);
  };

  // Fetch candidates
  const fetchCandidates = async () => {
    if (!token) return;
    fetchCandidatesWithToken(token);
  };

  const fetchCandidatesWithToken = async (authToken: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/candidates`, {
        headers: { 
          "Authorization": `Bearer ${authToken}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setCandidates(data);
      } else {
        if (res.status === 401 || res.status === 403) {
          handleLogout();
        }
      }
    } catch(e) { 
      console.error("Error fetching candidates", e);
      handleLogout();
    }
  };

  const fetchJobsWithToken = async (authToken: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/jobs`, {
        headers: { 
          "Authorization": `Bearer ${authToken}`
        }
      });
      if (res.ok) {
        setJobs(await res.json());
      } else {
        if (res.status === 401 || res.status === 403) {
          handleLogout();
        }
      }
    } catch(e) { 
      console.error("Error fetching jobs", e);
      handleLogout();
    }
  };

  const fetchSystemLogsWithToken = async (authToken: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/agent-logs`, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (res.ok) {
        setAllAgentLogs(await res.json());
      }
    } catch (e) {
      console.error("Error fetching agent logs", e);
    }
  };

  const fetchCandidateJourney = async (candidateId: string) => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/journey/${candidateId}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        setCandidateJourney(await res.json());
      }
    } catch (e) {
      console.error("Error fetching journey logs", e);
    }
  };

  const selectCandidate = (candidateId: string) => {
    setSelectedCandidateId(candidateId);
    fetchCandidateJourney(candidateId);
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newJobTitle || !requiredSkills || !hiringManagerName || !hiringManagerEmail) {
      alert("Please fill in all Job details, including required skills (analyze JD first)!");
      return;
    }
    if (!hiringManagerEmail.toLowerCase().endsWith("@gmail.com")) {
      alert("Hiring Manager email must be a @gmail.com address!");
      return;
    }
    setIsJobCreating(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          title: newJobTitle,
          description: newJobDescription,
          required_skills: requiredSkills,
          hiring_manager_name: hiringManagerName,
          hiring_manager_email: hiringManagerEmail
        })
      });
      if (res.ok) {
        alert("Job Opening Created & JD intelligence parsed successfully!");
        const data = await res.json();
        setNewJobTitle("");
        setNewJobDescription("");
        setHiringManagerName("");
        setHiringManagerEmail("");
        setJd("");
        setRequiredSkills("");
        setIsCreatingNewJob(false);
        if (data.job_id) {
          setSelectedJobId(data.job_id);
        }
        if (token) {
          fetchJobsWithToken(token);
          fetchSystemLogsWithToken(token);
        }
      } else {
        const data = await res.json();
        alert(`Failed to create Job: ${data.detail}`);
      }
    } catch (e) {
      console.error("Error creating job", e);
    }
    setIsJobCreating(false);
  };

  const handleRename = async (candidateId: string, currentName: string) => {
    const newName = prompt("Enter new name for candidate:", currentName);
    if (!newName || newName === currentName) return;
    try {
      const res = await fetch(`${API_BASE}/api/candidate/rename`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ candidate_id: candidateId, new_name: newName })
      });
      if (res.ok) fetchCandidates();
    } catch(e) { console.error("Rename failed", e); }
  };

  const handleJdSubmit = async () => {
    if (!jd) return;
    setIsJdLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/extract-jd`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ job_description: jd })
      });
      if (res.ok) {
        const data = await res.json();
        setRequiredSkills(data.required_skills.join(", "));
      } else {
        alert("JD extraction failed. Are you logged in with the Recruiter role?");
      }
    } catch (e) { console.error("Error extracting JD", e); }
    setIsJdLoading(false);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    if (!selectedJobId) {
      alert("Please select a Job Opening first!");
      return;
    }

    const selectedJob = jobs.find(j => j.id === selectedJobId);
    if (!selectedJob) return;

    setIsUploading(true);
    const files = Array.from(e.target.files);
    
    try {
      const uploadPromises = files.map(async (file) => {
        const candidateName = file.name.replace(/\.[^/.]+$/, ""); // strip extension
        
        const formData = new FormData();
        formData.append("candidate_name", candidateName);
        formData.append("required_skills", selectedJob.required_skills);
        formData.append("job_id", selectedJobId);
        formData.append("file", file);

        const res = await fetch(`${API_BASE}/api/upload-resume`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          },
          body: formData
        });
        return res.ok;
      });

      await Promise.all(uploadPromises);
      fetchCandidates(); 
      if (token) fetchSystemLogsWithToken(token);
    } catch(err) { console.error("Upload failed", err); }
    
    setIsUploading(false);
    e.target.value = "";
  };

  const handleEvaluate = async (candidateId: string) => {
    const experience = parseInt(prompt("Years of Experience:", "2") || "0");
    const noticePeriod = prompt("Notice Period (Immediate, 15 days, 30 days, 60 days):", "30 days") || "30 days";
    const expectedSalary = parseInt(prompt("Expected Salary (LPA / INR):", "1500000") || "0");
    
    try {
      const res = await fetch(`${API_BASE}/api/evaluate`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ 
          candidate_id: candidateId,
          experience,
          notice_period: noticePeriod,
          expected_salary: expectedSalary
        })
      });
      if (res.ok) fetchCandidates();
    } catch(e) { console.error("Evaluate failed", e); }
  };

  const handleStatusChange = async (candidateId: string, newStatus: string) => {
    try {
      await fetch(`${API_BASE}/api/interview/status`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ candidate_id: candidateId, status: newStatus })
      });
      fetchCandidates();
      if (selectedCandidateId === candidateId) fetchCandidateJourney(candidateId);
    } catch (e) { console.error("Error updating status", e); }
  };

  const handleScheduleInterview = async (candidateId: string) => {
    const date = interviewDates[candidateId] || "";
    const emailStr = candidateEmails[candidateId] || "";
    if(!date) {
        alert("Please select an interview date!");
        return;
    }
    if(!emailStr) {
        alert("Please enter a candidate email address!");
        return;
    }
    // Validate any real email — candidates may use Gmail, Outlook, Yahoo, etc.
    if (!/^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(emailStr)) {
        alert("Please enter a valid candidate email address.");
        return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/interview/schedule`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ candidate_id: candidateId, job_id: selectedJobId || "default_job", interview_date: date, email: emailStr })
      });
      if (res.ok) {
          const data = await res.json();
          alert(`Success! Google Meet Invite Scheduled: ${data.meet_url}\nEmail Status: ${data.email_sent ? 'Sent' : 'Mock Mode Active'}`);
          fetchCandidates();
          if (selectedCandidateId === candidateId) fetchCandidateJourney(candidateId);
      }
    } catch (e) { console.error("Error scheduling", e); }
  };

  const handleSubmitFeedback = async () => {
      const targetId = feedbackState.candidateId;
      if(!targetId) {
          alert("Select a candidate first");
          return;
      }
      try {
        const res = await fetch(`${API_BASE}/api/interview/feedback`, {
          method: "POST",
          headers: { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ 
              candidate_id: targetId, 
              rating: feedbackState.rating, 
              feedback: feedbackState.text 
          })
        });
        if(res.ok) {
            alert("Feedback saved & AI decision agent compiled report!");
            setFeedbackState({candidateId: "", rating: 5, text: ""});
            fetchCandidates();
            if (token) fetchSystemLogsWithToken(token);
            if (selectedCandidateId === targetId) selectCandidate(targetId);
        } else {
            alert("Failed to save feedback. Check if you have the HiringManager role!");
        }
      } catch (e) { console.error("Error saving feedback", e); }
  };

  // Stats
  const filteredCandidates = selectedJobId ? candidates.filter(c => c.job_id === selectedJobId) : candidates;

  const avgScore = filteredCandidates.length > 0 
    ? (filteredCandidates.reduce((a, b) => a + b.score, 0) / filteredCandidates.length).toFixed(1) 
    : 0;

  const scheduledCandidates = filteredCandidates.filter(c => c.status === 'Scheduled' || c.status === 'Shortlisted' || c.status === 'Interviewed');

  // Gated Access Flag helpers
  const canModifyJob = role === "Recruiter" || role === "Admin";
  const canUploadResumes = role === "Recruiter" || role === "Admin";
  const canScreenCandidate = role === "Recruiter" || role === "HiringManager" || role === "Admin";
  const canScreenResume = role === "Recruiter" || role === "Admin";
  const canSchedule = role === "Recruiter" || role === "Admin";
  const canSubmitFeedback = role === "HiringManager" || role === "Recruiter" || role === "Admin";

  // Detailed candidate selected fields
  const activeCandidate = candidates.find(c => c.id === selectedCandidateId);

  // Skill Metrics counts
  const pythonCount = filteredCandidates.filter(c => c.skills?.toLowerCase().includes("python")).length;
  const javaCount = filteredCandidates.filter(c => c.skills?.toLowerCase().includes("java") || c.skills?.toLowerCase().includes("spring")).length;
  const reactCount = filteredCandidates.filter(c => c.skills?.toLowerCase().includes("react") || c.skills?.toLowerCase().includes("javascript") || c.skills?.toLowerCase().includes("node")).length;
  const sqlCount = filteredCandidates.filter(c => c.skills?.toLowerCase().includes("sql") || c.skills?.toLowerCase().includes("postgres")).length;

  const totalEvaluated = filteredCandidates.length;
  const assCount = filteredCandidates.filter(c => c.assessment_score > 0).length;
  const passedAss = filteredCandidates.filter(c => c.assessment_score >= 70).length;
  const passRate = assCount > 0 ? Math.round((passedAss / assCount) * 100) : 0;
  const selectedCount = filteredCandidates.filter(c => c.status === "Selected" || c.status === "Hired").length;
  const hireRate = totalEvaluated > 0 ? Math.round((selectedCount / totalEvaluated) * 100) : 0;

  // Login view if not authenticated
  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950 p-4">
        {showOtpScreen ? (
          <form onSubmit={handleVerifyOtp} className="glass-dark p-8 rounded-3xl max-w-md w-full border-t border-white/10 flex flex-col gap-5 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-teal-600"></div>
            <div className="text-center">
              <h1 className="text-3xl font-extrabold text-white tracking-tight">Verify Gmail</h1>
              <p className="text-slate-400 text-sm mt-1">We sent a verification code to <span className="text-blue-300 font-bold">{verifyingEmail}</span></p>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">6-Digit Verification Code</label>
                <input 
                  type="text" 
                  maxLength={6}
                  required
                  placeholder="123456"
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-center text-lg font-bold tracking-widest text-slate-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  value={otpCode}
                  onChange={e => setOtpCode(e.target.value.replace(/\D/g, ""))}
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={isVerifyingOtp}
              className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-3.5 rounded-2xl transition-all shadow-xl active:scale-95 disabled:opacity-50 mt-2"
            >
              {isVerifyingOtp ? "Verifying..." : "Verify Code"}
            </button>

            <button 
              type="button" 
              onClick={() => {
                setShowOtpScreen(false);
                setOtpCode("");
              }} 
              className="text-center text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mt-2"
            >
              ← Back to Registration
            </button>
          </form>
        ) : isRegistering ? (
          <form onSubmit={handleRegister} className="glass-dark p-8 rounded-3xl max-w-md w-full border-t border-white/10 flex flex-col gap-5 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-600"></div>
            <div className="text-center">
              <h1 className="text-3xl font-extrabold text-white tracking-tight">Create Account</h1>
              <p className="text-slate-400 text-sm mt-1">Register for Recruiter AI Agent Platform</p>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Full Name</label>
                <input 
                  type="text" 
                  required
                  placeholder="John Doe"
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={registerName}
                  onChange={e => setRegisterName(e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Email Address</label>
                <input 
                  type="email" 
                  required
                  placeholder="user@domain.com"
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={registerEmail}
                  onChange={e => setRegisterEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Password</label>
                <input 
                  type="password" 
                  required
                  placeholder="••••••••"
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={registerPassword}
                  onChange={e => setRegisterPassword(e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Select System Role</label>
                <select 
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={registerRole}
                  onChange={(e) => setRegisterRole(e.target.value)}
                >
                  <option value="Recruiter">Recruiter (Post jobs, parse resumes, schedule interviews)</option>
                  <option value="HiringManager">Hiring Manager (Conduct interviews, write feedback)</option>
                  <option value="Admin">Admin (Full System Access)</option>
                </select>
              </div>
            </div>

            <button 
              type="submit"
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-3.5 rounded-2xl transition-all shadow-xl active:scale-95 mt-2"
            >
              Sign Up
            </button>

            <p className="text-center text-xs text-slate-400 mt-2">
              Already have an account?{" "}
              <button type="button" onClick={() => setIsRegistering(false)} className="text-blue-400 font-bold hover:underline">
                Log In
              </button>
            </p>
          </form>
        ) : (
          <form onSubmit={handleLogin} className="glass-dark p-8 rounded-3xl max-w-md w-full border-t border-white/10 flex flex-col gap-5 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-600"></div>
            <div className="text-center">
              <h1 className="text-3xl font-extrabold text-white tracking-tight">Recruiter AI Gate</h1>
              <p className="text-slate-400 text-sm mt-1">Enter your secure credentials to enter workspace</p>
            </div>

            <div className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Email Address</label>
                <input 
                  type="email" 
                  required
                  placeholder="email@example.com"
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={loginEmail}
                  onChange={e => setLoginEmail(e.target.value)}
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Password</label>
                <input 
                  type="password" 
                  required
                  placeholder="••••••••"
                  className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={loginPassword}
                  onChange={e => setLoginPassword(e.target.value)}
                />
              </div>
            </div>

            <button 
              type="submit"
              disabled={isLoggingIn}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-3.5 rounded-2xl transition-all shadow-xl active:scale-95 disabled:opacity-50 mt-2"
            >
              {isLoggingIn ? "Logging in..." : "Enter Workspace"}
            </button>

            <p className="text-center text-xs text-slate-400 mt-2">
              New to the system?{" "}
              <button type="button" onClick={() => setIsRegistering(true)} className="text-blue-400 font-bold hover:underline">
                Create Account
              </button>
            </p>
          </form>
        )}
      </div>
    );
  }

  return (
    <main className="p-4 md:p-8 flex flex-col gap-8 max-w-[90rem] mx-auto min-h-screen relative bg-slate-950">
      
      {/* Header Banner */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center glass-dark p-6 rounded-3xl gap-4 border-t border-white/10">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl md:text-5xl font-extrabold text-gradient tracking-tight">Recruiter AI</h1>
            <span className="bg-purple-500/20 text-purple-400 text-xs px-2.5 py-1 rounded-full font-bold uppercase border border-purple-500/30">{role} Mode</span>
          </div>
          <p className="text-slate-400 mt-2 text-sm md:text-base font-medium">Advanced Track B Automation System | Logged in: <span className="text-slate-200 font-semibold">{email}</span></p>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex gap-8">
            <div className="text-right">
              <p className="text-slate-500 text-[10px] uppercase tracking-widest font-bold">Total Candidates</p>
              <p className="text-3xl font-bold text-white">{candidates.length}</p>
            </div>
            <div className="text-right">
              <p className="text-slate-500 text-[10px] uppercase tracking-widest font-bold">Avg Match Score</p>
              <p className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">{avgScore}%</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="bg-white/5 hover:bg-rose-500/10 hover:text-rose-400 border border-white/10 rounded-2xl px-4 py-2 text-sm font-semibold transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Navigation tabs */}
      <div className="flex flex-wrap gap-4 border-b border-white/10 pb-2">
        <button 
          onClick={() => setActiveTab("operations")} 
          className={`pb-2 px-4 font-bold text-sm transition-all border-b-2 ${activeTab === "operations" ? 'text-blue-400 border-blue-400' : 'text-slate-400 border-transparent hover:text-white'}`}
        >
          📋 Hiring Operations
        </button>
        <button 
          onClick={() => {
            setActiveTab("visualizer");
            if (token) fetchSystemLogsWithToken(token);
          }} 
          className={`pb-2 px-4 font-bold text-sm transition-all border-b-2 ${activeTab === "visualizer" ? 'text-blue-400 border-blue-400' : 'text-slate-400 border-transparent hover:text-white'}`}
        >
          ⚙️ LangGraph Workflow & Logs
        </button>
        <button 
          onClick={() => setActiveTab("compliance")} 
          className={`pb-2 px-4 font-bold text-sm transition-all border-b-2 ${activeTab === "compliance" ? 'text-blue-400 border-blue-400' : 'text-slate-400 border-transparent hover:text-white'}`}
        >
          📊 Compliance & Diversity Analytics
        </button>
      </div>

      {activeTab === "operations" && (
        <>
          {/* Operations Layout Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Left Column (Job selectors, uploads, feedback) */}
            <div className="flex flex-col gap-8 lg:col-span-1">
              
              {/* Job Selector / Creator Panel */}
              {role === "HiringManager" ? (
                <section className="glass-dark p-6 rounded-3xl flex flex-col gap-4 border-t border-white/10 relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    💼 My Assigned Jobs
                  </h2>
                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wide block mb-1.5">Filter by Job Opening</label>
                    <select 
                      className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                      value={selectedJobId}
                      onChange={e => setSelectedJobId(e.target.value)}
                    >
                      <option value="">-- All My Jobs --</option>
                      {jobs.map(j => (
                        <option key={j.id} value={j.id}>{j.title}</option>
                      ))}
                    </select>
                  </div>
                </section>
              ) : (
                <section className="glass-dark p-6 rounded-3xl flex flex-col gap-4 border-t border-white/10 relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-indigo-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
                  <div className="flex justify-between items-center">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">💼 Job Opening</h2>
                    {!isCreatingNewJob && (
                      <button 
                        onClick={() => setIsCreatingNewJob(true)}
                        className="text-xs bg-blue-600 hover:bg-blue-500 text-white font-bold py-1.5 px-3 rounded-xl transition-all"
                      >
                        + New Job
                      </button>
                    )}
                  </div>

                  {isCreatingNewJob ? (
                    <form onSubmit={handleCreateJob} className="flex flex-col gap-4">
                      <div>
                        <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Job Title</label>
                        <input 
                          type="text" 
                          required
                          placeholder="e.g., Senior React Engineer"
                          className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={newJobTitle}
                          onChange={e => setNewJobTitle(e.target.value)}
                        />
                      </div>

                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block">Job Description</label>
                          <button 
                            type="button"
                            onClick={handleJdSubmit}
                            disabled={isJdLoading || !jd}
                            className="text-[10px] text-blue-400 hover:underline font-bold"
                          >
                            {isJdLoading ? "Extracting..." : "Extract Skills from Text"}
                          </button>
                        </div>
                        <textarea 
                          placeholder="Paste description details..."
                          className="w-full h-24 bg-slate-900 border border-white/10 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-200 resize-none"
                          value={jd}
                          onChange={e => setJd(e.target.value)}
                        />
                      </div>

                      <div>
                        <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Required Skills (Comma-separated)</label>
                        <input 
                          type="text" 
                          required
                          placeholder="React, TypeScript, TailwindCSS"
                          className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={requiredSkills}
                          onChange={e => setRequiredSkills(e.target.value)}
                        />
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Manager Name</label>
                          <input 
                            type="text" 
                            required
                            placeholder="Jane Manager"
                            className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={hiringManagerName}
                            onChange={e => setHiringManagerName(e.target.value)}
                          />
                        </div>
                        <div>
                          <label className="text-xs font-bold text-slate-300 uppercase tracking-wide block mb-1">Manager Email</label>
                          <input 
                            type="email" 
                            required
                            placeholder="manager@company.com"
                            className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={hiringManagerEmail}
                            onChange={e => setHiringManagerEmail(e.target.value)}
                          />
                        </div>
                      </div>

                      <div className="flex gap-2.5 mt-2">
                        <button 
                          type="submit"
                          disabled={isJobCreating}
                          className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-2.5 rounded-xl transition-all shadow-md text-sm active:scale-95 disabled:opacity-50"
                        >
                          {isJobCreating ? "Creating..." : "Create Opening"}
                        </button>
                        <button 
                          type="button"
                          onClick={() => {
                            setIsCreatingNewJob(false);
                            setNewJobTitle("");
                            setHiringManagerName("");
                            setHiringManagerEmail("");
                            setRequiredSkills("");
                          }}
                          className="bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl px-4 py-2.5 text-slate-300 font-semibold text-sm transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="flex flex-col gap-3">
                      <div>
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wide block mb-1.5">Select Active Job Opening</label>
                        <select 
                          className="w-full bg-slate-900 border border-white/10 rounded-xl p-3 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                          value={selectedJobId}
                          onChange={e => setSelectedJobId(e.target.value)}
                        >
                          <option value="">-- All Job Openings --</option>
                          {jobs.map(j => (
                            <option key={j.id} value={j.id}>{j.title}</option>
                          ))}
                        </select>
                      </div>

                      {selectedJobId && (() => {
                        const job = jobs.find(j => j.id === selectedJobId);
                        if (!job) return null;
                        return (
                          <div className="p-4 bg-slate-900/60 rounded-2xl border border-white/5 flex flex-col gap-2 mt-1 fade-in text-xs">
                            <div>
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block">Required Skills</span>
                              <p className="text-slate-300 font-medium">{job.required_skills}</p>
                            </div>
                            <div className="mt-1">
                              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block">Hiring Manager Email</span>
                              <p className="text-slate-300 font-medium break-all">{job.hiring_manager_email}</p>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </section>
              )}

              {/* Upload Panel */}
              {role !== "HiringManager" && (
                <section className="glass-dark p-6 rounded-3xl flex flex-col gap-4 border-t border-white/10 relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-500 to-orange-400 opacity-50 group-hover:opacity-100 transition-opacity"></div>
                  <h2 className="text-xl font-bold text-white">📂 Bulk Upload Resumes</h2>
                  <p className="text-sm text-slate-400">Select multiple PDF/DOCX files. The stateful LangGraph pipeline will parse, extract, score, and invite eligible candidates automatically.</p>            
                  <label className={`mt-2 border-2 border-dashed ${selectedJobId && !isUploading && canUploadResumes ? 'border-pink-500/40 hover:border-pink-500 hover:bg-pink-500/5 cursor-pointer' : 'border-white/10 cursor-not-allowed opacity-50'} rounded-2xl p-8 text-center transition-all ${isUploading ? 'animate-pulse bg-white/5' : ''}`}>
                    <p className="text-sm font-bold text-slate-200">
                        {isUploading ? 'Processing Pipeline Nodes...' : (selectedJobId ? `Upload Resumes for ${jobs.find(j => j.id === selectedJobId)?.title}` : 'Select a Job Opening first')}
                    </p>
                    <p className="text-xs text-slate-500 mt-2 font-medium">Multiple PDF/DOCX files allowed</p>
                    <input type="file" multiple className="hidden" accept=".pdf,.docx" onChange={handleFileUpload} disabled={!selectedJobId || isUploading || !canUploadResumes} />
                  </label>
                </section>
              )}

              {/* Hiring Manager Review Helper & Feedback Panel */}
              {role === "HiringManager" && (
                <section className="glass-dark p-6 rounded-3xl flex flex-col gap-5 border-t border-white/10 relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-400 to-orange-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">📝 Interview Feedback</h2>
                  <p className="text-sm text-slate-400">Evaluate candidates assigned to you after conducting interviews.</p>
                  
                  <select 
                    className="w-full bg-slate-900/80 border border-white/10 text-slate-300 rounded-xl p-3 text-sm focus:outline-none"
                    value={feedbackState.candidateId}
                    onChange={e => setFeedbackState({...feedbackState, candidateId: e.target.value})}
                  >
                    <option value="">Select a Candidate...</option>
                    {filteredCandidates.map(c => (
                      <option key={c.id} value={c.id}>{c.name} - Score: {Math.round(c.score)}%</option>
                    ))}
                  </select>

                  <div className="flex items-center gap-4">
                    <span className="text-sm font-bold text-slate-400">Rating (1-10):</span>
                    <input 
                      type="range" min="1" max="10" 
                      className="flex-1 accent-amber-500"
                      value={feedbackState.rating}
                      onChange={e => setFeedbackState({...feedbackState, rating: parseInt(e.target.value)})}
                    />
                    <span className="w-8 text-center font-bold text-amber-400 bg-amber-500/10 py-1 rounded-md">{feedbackState.rating}</span>
                  </div>

                  <textarea 
                    className="w-full h-24 bg-slate-900/80 border border-white/10 rounded-xl p-3 text-sm focus:outline-none resize-none text-slate-300 placeholder-slate-600"
                    placeholder="Qualitative feedback and notes. This triggers Agent 7's final hire recommendation."
                    value={feedbackState.text}
                    onChange={e => setFeedbackState({...feedbackState, text: e.target.value})}
                  ></textarea>

                  <button 
                    onClick={handleSubmitFeedback}
                    className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold py-3 rounded-xl transition-all shadow-xl hover:shadow-orange-500/20 active:scale-95"
                  >
                    Submit Feedback & Decisions
                  </button>            
                </section>
              )}
            </div>

            {/* Right Column (Applicants Leaderboard) */}
            <div className="lg:col-span-2 glass-dark p-6 rounded-3xl flex flex-col border-t border-white/10 relative overflow-hidden group">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-400 to-blue-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  🏆 Master Applicant Leaderboard
                </h2>
                <span className="text-xs text-slate-400 font-semibold">💡 Click on any candidate to inspect details & timeline</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 text-xs uppercase tracking-wider">
                      <th className="pb-4 font-bold px-4">Candidate</th>
                      <th className="pb-4 font-bold px-4 w-48">AI Match Score</th>
                      <th className="pb-4 font-bold px-4">Coding Score</th>
                      <th className="pb-4 font-bold px-4">Current Status</th>
                      <th className="pb-4 font-bold px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCandidates.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-12 text-center text-slate-500 text-sm font-medium">
                            No candidates found. Start by selecting a job and uploading resumes!
                        </td>
                      </tr>
                    ) : (
                      filteredCandidates.map((c, i) => (
                        <tr 
                          key={c.id} 
                          onClick={() => selectCandidate(c.id)}
                          className={`border-b border-white/5 hover:bg-white/5 transition-colors group/row fade-in cursor-pointer ${selectedCandidateId === c.id ? 'bg-white/5' : ''}`} 
                          style={{animationDelay: `${i * 0.05}s`}}
                        >
                          <td className="py-5 px-4 font-semibold text-slate-200 text-sm">
                              <div className="flex flex-col gap-0.5">
                                  <div className="flex items-center gap-2">
                                      <span className="hover:text-blue-400 transition-colors">{c.name}</span>
                                      {(role === "Recruiter" || role === "Admin") && (
                                        <button 
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleRename(c.id, c.name);
                                          }} 
                                          className="text-slate-500 hover:text-white transition-colors border border-transparent hover:border-white/10 rounded px-1 text-xs" 
                                          title="Rename Candidate"
                                        >✏️</button>
                                      )}
                                  </div>
                                  <span className="text-[11px] text-blue-400 font-medium">{jobs.find(j => j.id === c.job_id)?.title || "General Application"}</span>
                              </div>
                          </td>
                          <td className="py-5 px-4 w-48">
                            <div className="flex items-center gap-3">
                              <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div className="h-full bg-gradient-to-r from-cyan-400 to-blue-500 rounded-full relative" style={{ width: `${c.score}%` }}>
                                    <div className="absolute top-0 right-0 w-4 h-full bg-white/30 blur-[2px]"></div>
                                </div>
                              </div>
                              <span className="text-sm font-bold text-slate-300 w-10 text-right">{Math.round(c.score)}%</span>
                            </div>
                          </td>
                          <td className="py-5 px-4">
                            {c.assessment_score > 0 ? (
                              <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${c.assessment_score >= 70 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                                {c.assessment_score}/100
                              </span>
                            ) : (
                              <span className="text-xs text-slate-500 italic">Not Submitted</span>
                            )}
                          </td>
                          <td className="py-5 px-4" onClick={(e) => e.stopPropagation()}>
                            {/* Read-only status badge — AI controls transitions automatically */}
                            {(() => {
                              const statusConfig: Record<string, { label: string; cls: string }> = {
                                Applied:    { label: "Applied",    cls: "bg-slate-700/60 text-slate-300 border-slate-600" },
                                Assessed:   { label: "📩 Test Sent", cls: "bg-blue-500/10 text-blue-400 border-blue-500/30" },
                                Hold:       { label: "⏸ On Hold",   cls: "bg-amber-500/10 text-amber-400 border-amber-500/30" },
                                Scheduled:  { label: "📅 Scheduled", cls: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" },
                                Interviewed:{ label: "🎙 Interviewed",cls: "bg-teal-500/10 text-teal-400 border-teal-500/30" },
                                Shortlisted:{ label: "⭐ Shortlisted",cls: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" },
                                Selected:   { label: "✅ Selected",  cls: "bg-green-500/10 text-green-400 border-green-500/30" },
                                Hired:      { label: "🎉 Hired",     cls: "bg-purple-500/10 text-purple-400 border-purple-500/30" },
                                Rejected:   { label: "❌ Rejected",  cls: "bg-rose-500/10 text-rose-400 border-rose-500/30" },
                              };
                              const cfg = statusConfig[c.status] || statusConfig["Applied"];
                              return (
                                <div className="flex flex-col gap-1.5">
                                  <span className={`inline-block px-2.5 py-1 rounded-full text-[11px] font-bold border ${cfg.cls}`}>
                                    {cfg.label}
                                  </span>
                                  {/* Recruiter override panel — only visible for Hold candidates */}
                                  {c.status === "Hold" && canScreenCandidate && (
                                    <div className="flex gap-1 mt-0.5">
                                      <button
                                        title="Send coding test invitation"
                                        onClick={() => handleStatusChange(c.id, "Assessed")}
                                        className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/20 font-semibold transition-all"
                                      >
                                        Send Test
                                      </button>
                                      <button
                                        title="Reject candidate"
                                        onClick={() => handleStatusChange(c.id, "Rejected")}
                                        className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 font-semibold transition-all"
                                      >
                                        Reject
                                      </button>
                                    </div>
                                  )}
                                </div>
                              );
                            })()}
                          </td>
                          <td className="py-5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                            <button 
                                disabled={c.status === 'Rejected' || !canScreenResume}
                                onClick={() => handleEvaluate(c.id)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm ${c.status === 'Rejected' || !canScreenResume ? 'bg-white/5 text-slate-600 border border-white/5 cursor-not-allowed opacity-50' : 'bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 hover:border-white/20 active:scale-95'} mr-2`}
                            >
                                Screening Form
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          
          {/* Bottom Dashboards */}
          {(role === "Recruiter" || role === "Admin") && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-2">
                
                {/* Scheduling Dashboard */}
                <section className="glass-dark p-6 rounded-3xl flex flex-col gap-5 border-t border-white/10 relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 to-teal-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">📅 Scheduled Interviews Panel</h2>
                  <p className="text-sm text-slate-400 mb-2">Invite qualified candidates by setting Meet dates. (Recruiter Only)</p>
                  
                  {scheduledCandidates.length === 0 ? (
                      <div className="p-8 text-center border-2 border-dashed border-white/5 rounded-2xl">
                          <p className="text-slate-500 text-sm">No candidates shortlisted or scheduled yet.</p>
                      </div>
                  ) : (
                      <div className="flex flex-col gap-4 max-h-[300px] overflow-y-auto pr-2">
                          {scheduledCandidates.map(c => (
                              <div key={c.id} className="bg-slate-900/60 p-4 rounded-xl border border-white/5 flex flex-col gap-3">
                                  <div className="flex justify-between items-center">
                                      <span className="font-bold text-slate-200">{c.name}</span>
                                      <span className="bg-emerald-500/10 text-emerald-400 text-[10px] font-black uppercase px-2 py-1 rounded-md">{c.status}</span>
                                  </div>
                                  <div className="flex flex-wrap gap-3 items-center w-full mt-2">
                                      <input 
                                          disabled={!canSchedule}
                                          type="email"
                                          placeholder="Candidate Gmail"
                                          className="bg-black/50 border border-white/10 text-slate-300 rounded-lg p-2.5 text-sm focus:outline-none focus:border-emerald-500/50 flex-1 min-w-[200px]"
                                          value={candidateEmails[c.id] || c.email || ""}
                                          onChange={(e) => setCandidateEmails({...candidateEmails, [c.id]: e.target.value})}
                                      />
                                      <input 
                                          disabled={!canSchedule}
                                          type="date" 
                                          className="bg-black/50 border border-white/10 text-slate-300 rounded-lg p-2.5 text-sm focus:outline-none focus:border-emerald-500/50 w-[150px]"
                                          value={interviewDates[c.id] || ""}
                                          onChange={(e) => setInterviewDates({...interviewDates, [c.id]: e.target.value})}
                                      />
                                      <button
                                          disabled={!canSchedule}
                                          onClick={() => handleScheduleInterview(c.id)}
                                          className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-2.5 px-4 rounded-lg text-sm active:scale-95 transition-all whitespace-nowrap"
                                      >
                                          Schedule & Meet Link
                                      </button>
                                  </div>
                              </div>
                          ))}
                      </div>
                  )}
                </section>

                {/* Recruiter feedback helper overview */}
                <section className="glass-dark p-6 rounded-3xl flex flex-col gap-5 border-t border-white/10 relative overflow-hidden group">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-400 to-orange-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">📝 Recruiter Quick Notes</h2>
                  <p className="text-sm text-slate-400">Add feedback / screening evaluations to candidates directly.</p>
                  
                  <select 
                      disabled={!canSubmitFeedback}
                      className="bg-slate-900/80 border border-white/10 text-slate-300 rounded-xl p-3 text-sm focus:outline-none"
                      value={feedbackState.candidateId}
                      onChange={e => setFeedbackState({...feedbackState, candidateId: e.target.value})}
                  >
                      <option value="">Select a Candidate...</option>
                      {filteredCandidates.map(c => (
                          <option key={c.id} value={c.id}>{c.name} - Score: {Math.round(c.score)}%</option>
                      ))}
                  </select>

                  <div className="flex items-center gap-4">
                      <span className="text-sm font-bold text-slate-400">Rating (1-10):</span>
                      <input 
                          disabled={!canSubmitFeedback}
                          type="range" min="1" max="10" 
                          className="flex-1 accent-amber-500"
                          value={feedbackState.rating}
                          onChange={e => setFeedbackState({...feedbackState, rating: parseInt(e.target.value)})}
                      />
                      <span className="w-8 text-center font-bold text-amber-400 bg-amber-500/10 py-1 rounded-md">{feedbackState.rating}</span>
                  </div>

                  <textarea 
                      disabled={!canSubmitFeedback}
                      className="w-full h-24 bg-slate-900/80 border border-white/10 rounded-xl p-3 text-sm focus:outline-none resize-none text-slate-300 placeholder-slate-600"
                      placeholder="Qualitative feedback and notes..."
                      value={feedbackState.text}
                      onChange={e => setFeedbackState({...feedbackState, text: e.target.value})}
                  ></textarea>

                  <button 
                      disabled={!canSubmitFeedback}
                      onClick={handleSubmitFeedback}
                      className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold py-3 rounded-xl transition-all shadow-xl hover:shadow-orange-500/20 active:scale-95"
                  >
                      Submit Feedback
                  </button>            
                </section>
            </div>
          )}
        </>
      )}

      {activeTab === "visualizer" && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 fade-in">
          {/* Left panel: Candidate selector */}
          <div className="lg:col-span-1 glass-dark p-6 rounded-3xl border-t border-white/10 flex flex-col gap-4">
            <h3 className="text-lg font-bold text-white mb-2">Candidate Selection</h3>
            <p className="text-xs text-slate-400">Select a candidate to visualize their active LangGraph node and execution history.</p>
            <div className="flex flex-col gap-2 max-h-[450px] overflow-y-auto pr-2">
              {filteredCandidates.map(c => (
                <button
                  key={c.id}
                  onClick={() => selectCandidate(c.id)}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all text-xs flex flex-col gap-1 ${selectedCandidateId === c.id ? 'bg-blue-600/10 border-blue-500 text-blue-400' : 'bg-slate-900/50 border-white/5 hover:bg-slate-900 text-slate-300'}`}
                >
                  <span className="font-bold text-slate-200">{c.name}</span>
                  <div className="flex justify-between w-full mt-1">
                    <span>ATS Score: {Math.round(c.score)}%</span>
                    <span className="font-bold">{c.status}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Right panel: LangGraph workflow chart + logs */}
          <div className="lg:col-span-3 flex flex-col gap-8">
            <section className="glass-dark p-6 rounded-3xl border-t border-white/10 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500 to-teal-500"></div>
              <h3 className="text-xl font-bold text-white mb-4">LangGraph Multi-Agent Workflow Visualizer</h3>
              
              {selectedCandidateId && activeCandidate ? (() => {
                const status = activeCandidate.status;
                const score = activeCandidate.score;
                const hasAss = activeCandidate.assessment_score > 0;
                
                // Color states for nodes:
                // completed (green), active (blue), waiting (grey)
                const getNodeState = (nodeName: string) => {
                  if (nodeName === "JD Intelligence") return "completed";
                  if (nodeName === "Resume Screening") return "completed";
                  
                  if (nodeName === "Assessment Recommendation") {
                    return status !== "Applied" ? "completed" : "active";
                  }
                  
                  if (nodeName === "Assessment Delivery") {
                    if (activeCandidate.assessment_token) return "completed";
                    if (status === "Applied" || status === "Hold" || status === "Rejected") return "waiting";
                    if (status === "Assessed" && !hasAss) return "active";
                    return "completed";
                  }
                  
                  if (nodeName === "Assessment Evaluation") {
                    if (hasAss || ["Scheduled", "Interviewed", "Recommended", "Selected", "Hired"].includes(status)) return "completed";
                    if (status === "Assessed") return "active";
                    return "waiting";
                  }
                  
                  if (nodeName === "Interview Preparation") {
                    const hasQuestions = activeCandidate.interview_questions && activeCandidate.interview_questions.length > 0;
                    if (hasQuestions || ["Interviewed", "Recommended", "Selected", "Hired"].includes(status)) return "completed";
                    if (status === "Scheduled") return "active";
                    return "waiting";
                  }
                  
                  if (nodeName === "Interview Decision") {
                    if (activeCandidate.ai_recommendation || activeCandidate.rating) return "completed";
                    if (status === "Interviewed" || status === "Recommended") return "active";
                    return "waiting";
                  }
                  return "waiting";
                };

                const nodes = [
                  { name: "JD Intelligence", id: "jd", desc: "Agent 1: Parses Job Descriptions", icon: "📄" },
                  { name: "Resume Screening", id: "resume", desc: "Agent 2: Scores & Extracts Resume Info", icon: "🔍" },
                  { name: "Assessment Recommendation", id: "recom", desc: "Agent 3: Decides Routing Logic", icon: "🔀" },
                  { name: "Assessment Delivery", id: "delivery", desc: "Agent 4: Generates Invite & Emails Link", icon: "✉️" },
                  { name: "Assessment Evaluation", id: "evaluation", desc: "Agent 5: Grades Code via Judge0CE", icon: "💻" },
                  { name: "Interview Preparation", id: "prep", desc: "Agent 6: Generates Personalized Qs", icon: "📚" },
                  { name: "Interview Decision", id: "decision", desc: "Agent 7: Generates final Recommendations", icon: "🏁" }
                ];

                return (
                  <div className="flex flex-col gap-8 my-6">
                    {/* Visual graph layout */}
                    <div className="flex flex-col md:flex-row flex-wrap items-center justify-between gap-6 p-6 bg-slate-950/60 rounded-2xl border border-white/5">
                      {nodes.map((node, index) => {
                        const state = getNodeState(node.name);
                        let bgClass = "bg-slate-900 border-white/10 text-slate-500";
                        let glowClass = "";
                        
                        if (state === "completed") {
                          bgClass = "bg-emerald-500/10 border-emerald-500 text-emerald-400";
                          glowClass = "shadow-[0_0_15px_rgba(16,185,129,0.15)]";
                        } else if (state === "active") {
                          bgClass = "bg-blue-500/10 border-blue-500 text-blue-400 ring-2 ring-blue-500/30";
                          glowClass = "shadow-[0_0_20px_rgba(59,130,246,0.3)] animate-pulse";
                        }

                        return (
                          <div key={node.id} className="flex flex-col md:flex-row items-center gap-4">
                            {/* Node element */}
                            <div className={`w-28 p-3 rounded-2xl border text-center flex flex-col items-center justify-center gap-1.5 transition-all duration-300 relative group cursor-help ${bgClass} ${glowClass}`}>
                              <span className="text-xl">{node.icon}</span>
                              <span className="text-[10px] font-bold tracking-tight leading-tight">{node.name}</span>
                              
                              {/* Hover tooltips showing node description */}
                              <div className="absolute bottom-full mb-2 hidden group-hover:block w-48 bg-slate-900 border border-white/10 p-2.5 rounded-lg text-[10px] text-left text-slate-300 shadow-xl z-20">
                                <span className="font-bold text-white block mb-0.5">{node.name}</span>
                                {node.desc}
                                <span className="block mt-1 font-semibold text-emerald-400 capitalize">Status: {state}</span>
                              </div>
                            </div>

                            {/* Arrow divider */}
                            {index < nodes.length - 1 && (
                              <div className="text-slate-600 font-bold hidden md:block select-none text-lg">➜</div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    <div className="flex gap-4 items-center justify-center text-xs">
                      <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-emerald-500/20 border border-emerald-500 block"></span><span className="text-slate-400">Node Completed</span></div>
                      <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-blue-500/20 border border-blue-500 block"></span><span className="text-slate-400">Active Stage / Paused</span></div>
                      <div className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-slate-900 border border-white/10 block"></span><span className="text-slate-400">Not Reached</span></div>
                    </div>
                  </div>
                );
              })() : (
                <div className="py-12 text-center text-slate-500 text-sm">
                  Select a candidate from the left panel to inspect the active state graph.
                </div>
              )}
            </section>

            {/* Cron / Log records list */}
            <section className="glass-dark p-6 rounded-3xl border-t border-white/10">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-white">Chronological System Agent Logs</h3>
                <button 
                  onClick={() => {
                    if (token) fetchSystemLogsWithToken(token);
                  }} 
                  className="text-xs text-blue-400 hover:underline font-bold"
                >
                  🔄 Refresh Logs
                </button>
              </div>
              <div className="flex flex-col gap-3 overflow-y-auto max-h-[350px] pr-2">
                {allAgentLogs.length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-6">No system logs logged yet.</p>
                ) : (
                  allAgentLogs.map(log => {
                    // Try formatting input/output safely
                    let inputObj = log.input_data;
                    let outputObj = log.output_data;
                    try {
                      if (typeof log.input_data === "string" && log.input_data.startsWith("{")) inputObj = JSON.parse(log.input_data);
                      if (typeof log.output_data === "string" && log.output_data.startsWith("{")) outputObj = JSON.parse(log.output_data);
                    } catch(e){}

                    return (
                      <div key={log.id} className="bg-slate-900/60 p-4 rounded-xl border border-white/5 flex flex-col gap-2 text-xs">
                        <div className="flex justify-between items-center border-b border-white/5 pb-2">
                          <span className="font-bold text-slate-200">{log.agent_name}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${log.status === "Success" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
                              {log.status}
                            </span>
                          </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-1 font-mono text-[10px]">
                          <div>
                            <span className="text-slate-500 font-bold block mb-1">INPUT PARAMS</span>
                            <pre className="p-2 bg-slate-950/80 rounded border border-white/5 max-h-[100px] overflow-y-auto whitespace-pre-wrap">{JSON.stringify(inputObj, null, 2)}</pre>
                          </div>
                          <div>
                            <span className="text-slate-500 font-bold block mb-1">AGENT OUTPUT</span>
                            <pre className="p-2 bg-slate-950/80 rounded border border-white/5 max-h-[100px] overflow-y-auto whitespace-pre-wrap">{JSON.stringify(outputObj, null, 2)}</pre>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === "compliance" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 fade-in">
          
          {/* Recruitment Funnel */}
          <section className="glass-dark p-6 rounded-3xl flex flex-col border-t border-white/10">
            <h3 className="text-lg font-bold text-white mb-4">📊 Recruitment Funnel</h3>
            <div className="flex flex-col gap-4">
              {[
                { label: "Applied", count: candidates.filter(c => c.status === "Applied" || c.status === "Hold").length, color: "bg-blue-500" },
                { label: "Screened / Assessed", count: candidates.filter(c => c.status === "Assessed").length, color: "bg-cyan-500" },
                { label: "Interviewed (Feedback Ready)", count: candidates.filter(c => c.status === "Interviewed" || c.status === "Scheduled").length, color: "bg-emerald-500" },
                { label: "Hired / Selected", count: candidates.filter(c => c.status === "Hired" || c.status === "Selected").length, color: "bg-purple-500" },
                { label: "Rejected", count: candidates.filter(c => c.status === "Rejected").length, color: "bg-red-500" }
              ].map((step, idx) => {
                const percentage = candidates.length > 0 ? (step.count / candidates.length) * 100 : 0;
                return (
                  <div key={idx} className="flex flex-col gap-1.5">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-300">{step.label}</span>
                      <span className="text-white">{step.count} ({Math.round(percentage)}%)</span>
                    </div>
                    <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-white/5">
                      <div className={`h-full ${step.color} transition-all`} style={{ width: `${percentage}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Skill Metrics */}
          <section className="glass-dark p-6 rounded-3xl flex flex-col border-t border-white/10">
            <h3 className="text-lg font-bold text-white mb-4">📈 Active Talent Skill Analytics</h3>
            <div className="flex flex-col gap-4">
              {[
                { name: "Python / AI Engineers", count: pythonCount, total: candidates.length },
                { name: "Java / Spring Developers", count: javaCount, total: candidates.length },
                { name: "React / JavaScript Frontend", count: reactCount, total: candidates.length },
                { name: "PostgreSQL / SQL Experts", count: sqlCount, total: candidates.length }
              ].map((item, idx) => {
                const prc = item.total > 0 ? Math.round((item.count / item.total) * 100) : 0;
                return (
                  <div key={idx} className="p-4 bg-slate-900/60 rounded-2xl border border-white/5">
                    <div className="flex justify-between items-center text-xs font-semibold mb-1">
                      <span className="text-slate-300">{item.name}</span>
                      <span className="text-blue-400 font-bold">{item.count} profiles ({prc}%)</span>
                    </div>
                    <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-white/5">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${prc}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Education & Selection Metrics */}
          <section className="glass-dark p-6 rounded-3xl flex flex-col border-t border-white/10">
            <h3 className="text-lg font-bold text-white mb-4">🎓 Education & Screening Quality</h3>
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-900/60 rounded-2xl border border-white/5 text-center">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block mb-1">Tier-1 Profiles</span>
                  <span className="text-2xl font-extrabold text-emerald-400">
                    {candidates.filter(c => 
                      c.skills?.toLowerCase().includes("iit") || 
                      c.skills?.toLowerCase().includes("nit") || 
                      c.skills?.toLowerCase().includes("bits")
                    ).length}
                  </span>
                  <p className="text-[9px] text-slate-500 mt-2">IIT/NIT/BITS extracted</p>
                </div>
                <div className="p-4 bg-slate-900/60 rounded-2xl border border-white/5 text-center">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block mb-1">Tech Degrees</span>
                  <span className="text-2xl font-extrabold text-cyan-400">
                    {candidates.filter(c => 
                      c.skills?.toLowerCase().includes("b.tech") || 
                      c.skills?.toLowerCase().includes("m.tech") ||
                      c.skills?.toLowerCase().includes("engineering")
                    ).length}
                  </span>
                  <p className="text-[9px] text-slate-500 mt-2">B.Tech/M.Tech matches</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-900/60 rounded-2xl border border-white/5 text-center">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block mb-1">Test Pass Rate</span>
                  <span className="text-2xl font-extrabold text-purple-400">{passRate}%</span>
                  <p className="text-[9px] text-slate-500 mt-2">Score ≥ 70% compiler</p>
                </div>
                <div className="p-4 bg-slate-900/60 rounded-2xl border border-white/5 text-center">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block mb-1">Selection Rate</span>
                  <span className="text-2xl font-extrabold text-blue-400">{hireRate}%</span>
                  <p className="text-[9px] text-slate-500 mt-2">Hire / Strong Hire decision</p>
                </div>
              </div>
            </div>
          </section>

        </div>
      )}

      {/* Selected Candidate Detail Side Drawer */}
      {selectedCandidateId && activeCandidate && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex justify-end animate-fade-in" onClick={() => setSelectedCandidateId(null)}>
          <div 
            className="w-full max-w-2xl bg-slate-900 border-l border-white/10 h-full p-8 flex flex-col gap-6 overflow-y-auto shadow-2xl relative" 
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button 
              onClick={() => setSelectedCandidateId(null)}
              className="absolute top-6 right-6 text-slate-400 hover:text-white text-lg font-bold border border-white/10 bg-white/5 hover:bg-white/10 rounded-full w-8 h-8 flex items-center justify-center"
            >
              ✕
            </button>

            {/* Profile Header */}
            <div className="border-b border-white/5 pb-4 mt-2">
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase border ${
                activeCandidate.status === 'Scheduled' || activeCandidate.status === 'Interviewed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                activeCandidate.status === 'Rejected' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                activeCandidate.status === 'Selected' || activeCandidate.status === 'Hired' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                'bg-amber-500/10 text-amber-400 border-amber-500/20'
              }`}>{activeCandidate.status}</span>
              <h2 className="text-2xl font-bold text-white mt-2">{activeCandidate.name}</h2>
              <p className="text-xs text-blue-400 font-semibold">{jobs.find(j => j.id === activeCandidate.job_id)?.title || "General Application"}</p>
              {activeCandidate.email && <p className="text-xs text-slate-500 mt-1">Email: {activeCandidate.email}</p>}
              {activeCandidate.assessment_token && (
                <div className="mt-3 p-3.5 bg-blue-500/5 hover:bg-blue-500/10 border border-blue-500/20 rounded-2xl flex flex-col gap-2 transition-all">
                  <div className="flex justify-between items-center text-xs font-bold text-blue-400">
                    <span className="flex items-center gap-1.5">🔗 Coding Assessment Link</span>
                    <button 
                      onClick={() => {
                        navigator.clipboard.writeText(`${window.location.origin}/assessment/${activeCandidate.assessment_token}`);
                        alert("Assessment URL copied to clipboard!");
                      }}
                      className="px-2.5 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-white rounded-xl text-[10px] font-bold transition-all active:scale-95"
                    >
                      Copy URL
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-300 font-mono break-all leading-normal">
                    {window.location.origin}/assessment/{activeCandidate.assessment_token}
                  </p>
                </div>
              )}
            </div>

            {/* AI Recommendation Decision Card */}
            {activeCandidate.ai_recommendation && (
              <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-2xl flex flex-col gap-1.5">
                <div className="flex justify-between items-center text-xs font-bold">
                  <span className="text-purple-400">AI AGENT 7: FINAL DECISION RECOMMENDATION</span>
                  <span className="bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded uppercase">{activeCandidate.ai_recommendation}</span>
                </div>
                <p className="text-slate-300 text-xs mt-1 leading-relaxed italic">
                  "{candidates.find(c => c.id === selectedCandidateId)?.feedback?.split("\n").find((l: string) => l.includes("[AI reasoning]"))?.replace("[AI reasoning]", "") || "Final recommendation compiled from overall screening metrics."}"
                </p>
              </div>
            )}

            {/* ATS Score & Match Explanation */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-slate-400 uppercase tracking-widest">
                <span>ATS Match Explanation</span>
                <span className="text-emerald-400">Match score: {Math.round(activeCandidate.score)}%</span>
              </div>
              <div className="bg-slate-950 p-4 rounded-xl border border-white/5 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                {activeCandidate.ats_explanation || "No explanation report logged yet."}
              </div>
            </div>

            {/* AI Summary / Strengths / Weaknesses */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-950/60 p-4 rounded-xl border border-white/5 flex flex-col gap-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block">AI Candidate Summary</span>
                <p className="text-xs text-slate-300 leading-relaxed">{activeCandidate.candidate_summary || "Summary will populate upon screening."}</p>
              </div>
              <div className="bg-slate-950/60 p-4 rounded-xl border border-white/5 flex flex-col gap-3">
                <div>
                  <span className="text-[10px] text-emerald-500 uppercase tracking-wider font-bold block">Key Strengths</span>
                  <p className="text-xs text-slate-300 mt-1 font-medium">{activeCandidate.strengths || "None flagged."}</p>
                </div>
                <div className="border-t border-white/5 pt-2">
                  <span className="text-[10px] text-amber-500 uppercase tracking-wider font-bold block">Potential Weaknesses / Gaps</span>
                  <p className="text-xs text-slate-300 mt-1 font-medium">{activeCandidate.weaknesses || "None flagged."}</p>
                </div>
              </div>
            </div>

            {/* Coding Assessment Grader Panel */}
            {activeCandidate.assessment_score > 0 && (
              <div className="p-4 bg-slate-950 rounded-xl border border-white/5 flex flex-col gap-3">
                <div className="flex justify-between items-center text-xs font-bold text-slate-400 uppercase tracking-widest border-b border-white/5 pb-2">
                  <span>Agent 5: Coding Assessment Results</span>
                  <span className={activeCandidate.assessment_score >= 70 ? "text-emerald-400" : "text-rose-400"}>Score: {activeCandidate.assessment_score}/100</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-500 font-semibold block">Execution Status</span>
                    <span className={`font-bold ${activeCandidate.assessment_score >= 70 ? "text-emerald-400" : "text-rose-400"}`}>
                      {activeCandidate.assessment_score >= 70 ? "PASSED (Qualified)" : "HOLD / REVIEW REQUIRED"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-semibold block">Language Workspace</span>
                    <span className="font-bold text-slate-300 uppercase">Coding Portal (Judge0 Sandbox)</span>
                  </div>
                </div>
              </div>
            )}

            {/* Generated Interview Questions for the Hiring Manager */}
            {activeCandidate.interview_questions && activeCandidate.interview_questions.length > 0 && (
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs font-bold text-slate-400 uppercase tracking-widest">
                  <span>Agent 6: Generated Interview Questions</span>
                  <span className="text-blue-400">5 personalized questions</span>
                </div>
                <div className="flex flex-col gap-2.5">
                  {activeCandidate.interview_questions.map((q: string, qIdx: number) => (
                    <div key={qIdx} className="p-3 bg-slate-950 rounded-xl border border-white/5 text-xs text-slate-300 flex items-start justify-between gap-3 group/question">
                      <span className="leading-relaxed">{qIdx + 1}. {q}</span>
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(q);
                          alert("Question copied to clipboard!");
                        }}
                        className="text-[10px] bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white px-2 py-1 rounded transition-colors whitespace-nowrap opacity-0 group-hover/question:opacity-100"
                      >
                        Copy
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Journey Audit trail logs */}
            <div className="space-y-3 border-t border-white/5 pt-4">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Candidate Journey Stage Audit Trail</h4>
              <div className="flex flex-col gap-3 relative pl-4 border-l border-white/10 mt-2">
                {candidateJourney.length === 0 ? (
                  <p className="text-xs text-slate-500 font-medium italic">No lifecycle transitions recorded yet.</p>
                ) : (
                  candidateJourney.map((j, idx) => (
                    <div key={j.id} className="relative text-xs group">
                      {/* marker dot */}
                      <span className="absolute -left-[20.5px] top-1.5 w-2 h-2 rounded-full bg-blue-500 border border-slate-900 group-hover:scale-125 transition-transform"></span>
                      <div className="flex justify-between font-bold mb-0.5">
                        <span className="text-slate-200">{j.stage}</span>
                        <span className="text-slate-500 font-medium">{new Date(j.timestamp).toLocaleString()}</span>
                      </div>
                      {j.notes && <p className="text-slate-400 leading-relaxed text-[11px] font-medium">{j.notes}</p>}
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        </div>
      )}

    </main>
  );
}
