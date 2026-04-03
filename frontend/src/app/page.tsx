"use client";

import { useState, useEffect } from "react";

export default function Dashboard() {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [jd, setJd] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [isJdLoading, setIsJdLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  // Modals & States
  const [emailModal, setEmailModal] = useState<{show: boolean, text: string, name: string}>({show: false, text: "", name: ""});
  const [interviewDates, setInterviewDates] = useState<Record<string, string>>({});
  const [candidateEmails, setCandidateEmails] = useState<Record<string, string>>({});
  const [feedbackState, setFeedbackState] = useState<{candidateId: string, rating: number, text: string}>({candidateId: "", rating: 5, text: ""});

  const handleRename = async (candidateId: string, currentName: string) => {
      const newName = prompt("Enter new name for candidate:", currentName);
      if (!newName || newName === currentName) return;
      try {
          const res = await fetch("http://localhost:8000/api/candidate/rename", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ candidate_id: candidateId, new_name: newName })
          });
          if (res.ok) fetchCandidates();
      } catch(e) { console.error("Rename failed", e); }
  }
  
  // Stats
  const avgScore = candidates.length > 0 
    ? (candidates.reduce((a, b) => a + b.score, 0) / candidates.length).toFixed(1) 
    : 0;
    
  // Fetch candidates
  const fetchCandidates = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/candidates");
      if(res.ok) {
        setCandidates(await res.json());
      }
    } catch(e) { console.error("Error fetching candidates", e) }
  };
  
  useEffect(() => { fetchCandidates(); }, []);

  const handleJdSubmit = async () => {
    if (!jd) return;
    setIsJdLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/extract-jd", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jd })
      });
      const data = await res.json();
      setRequiredSkills(data.required_skills.join(", "));
    } catch (e) { console.error("Error extracting JD", e) }
    setIsJdLoading(false);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    if (!requiredSkills) {
      alert("Please extract Job Description skills first!");
      return;
    }

    setIsUploading(true);
    const files = Array.from(e.target.files);
    
    try {
      const uploadPromises = files.map(async (file) => {
        const candidateName = file.name.replace(/\.[^/.]+$/, ""); // strip extension
        
        const formData = new FormData();
        formData.append("candidate_name", candidateName);
        formData.append("required_skills", requiredSkills);
        formData.append("file", file);

        const res = await fetch("http://localhost:8000/api/upload-resume", {
          method: "POST",
          body: formData
        });
        return res.ok;
      });

      await Promise.all(uploadPromises);
      fetchCandidates(); // Refresh list ONCE after all are processed
    } catch(err) { console.error("Upload failed", err) }
    
    setIsUploading(false);
    // clear input
    e.target.value = "";
  };

  const handleEvaluate = async (candidateId: string) => {
    const experience = parseInt(prompt("Years of Experience:", "2") || "0");
    const noticePeriod = prompt("Notice Period (Immediate, 15 days, 30 days, 60 days):", "30 days") || "30 days";
    const expectedSalary = parseInt(prompt("Expected Salary (LPA / INR):", "1500000") || "0");
    
    try {
      const res = await fetch("http://localhost:8000/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          candidate_id: candidateId,
          experience,
          notice_period: noticePeriod,
          expected_salary: expectedSalary
        })
      });
      if(res.ok) fetchCandidates();
    } catch(e) { console.error("Evaluate failed", e) }
  };

  const handleStatusChange = async (candidateId: string, newStatus: string) => {
    try {
      await fetch("http://localhost:8000/api/interview/status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_id: candidateId, status: newStatus })
      });
      fetchCandidates();
    } catch (e) { console.error("Error updating status", e); }
  };

  const handleScheduleInterview = async (candidateId: string, name: string) => {
    const date = interviewDates[candidateId] || "";
    const email = candidateEmails[candidateId] || "";
    if(!date) {
        alert("Please select an interview date!");
        return;
    }
    if(!email) {
        alert("Please enter a candidate email address!");
        return;
    }
    try {
      const res = await fetch("http://localhost:8000/api/interview/schedule", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_id: candidateId, job_id: 1, interview_date: date, email: email })
      });
      if (res.ok) {
          const data = await res.json();
          if(data.email_sent) {
              alert(`Success! An email has been sent in real-time to ${email}.`);
          } else {
              alert(`Email creation successful, but sending failed: ${data.warning}`);
          }
          fetchCandidates();
      }
    } catch (e) { console.error("Error scheduling", e); }
  };

  const handleSubmitFeedback = async () => {
      if(!feedbackState.candidateId) {
          alert("Select a candidate first");
          return;
      }
      try {
        const res = await fetch("http://localhost:8000/api/interview/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
              candidate_id: feedbackState.candidateId, 
              rating: feedbackState.rating, 
              feedback: feedbackState.text 
          })
        });
        if(res.ok) {
            alert("Feedback saved!");
            setFeedbackState({candidateId: "", rating: 5, text: ""});
        }
      } catch (e) { console.error("Error saving feedback", e); }
  };

  const scheduledCandidates = candidates.filter(c => c.status === 'Scheduled' || c.status === 'Shortlisted');

  return (
    <main className="p-4 md:p-8 fade-in flex flex-col gap-8 max-w-[90rem] mx-auto min-h-screen relative">
      
      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center glass-dark p-6 rounded-3xl gap-4">
        <div>
          <h1 className="text-3xl md:text-5xl font-extrabold text-gradient tracking-tight">Recruiter AI</h1>
          <p className="text-slate-400 mt-2 text-sm md:text-base font-medium">Advanced Track B Automation System</p>
        </div>
        <div className="flex gap-8">
          <div className="text-right">
            <p className="text-slate-500 text-xs uppercase tracking-widest font-bold">Total Candidates</p>
            <p className="text-3xl font-bold text-white">{candidates.length}</p>
          </div>
          <div className="text-right">
            <p className="text-slate-500 text-xs uppercase tracking-widest font-bold">Avg ATS Score</p>
            <p className="text-3xl font-bold items-center flex gap-1 justify-end">
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">{avgScore}%</span>
            </p>
          </div>
        </div>
      </header>
      
      {/* Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column (Inputs) */}
        <div className="flex flex-col gap-8 lg:col-span-1">
          <section className="glass-dark p-6 rounded-3xl flex flex-col gap-5 border-t border-white/10 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-purple-600 opacity-50 group-hover:opacity-100 transition-opacity"></div>
            <h2 className="text-xl font-bold flex items-center gap-2 text-white">
               📄 Job Description
            </h2>
            <textarea 
              className="w-full h-32 bg-slate-900/50 border border-white/10 rounded-2xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all resize-none text-slate-200 placeholder-slate-600"
              placeholder="Paste Job Description here to leverage extraction..."
              value={jd}
              onChange={e => setJd(e.target.value)}
            />
            <button 
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-3 rounded-2xl transition-all shadow-xl hover:shadow-purple-500/20 active:scale-95 flex items-center justify-center gap-2 disabled:opacity-50"
              onClick={handleJdSubmit}
              disabled={isJdLoading || !jd}
            >
              {isJdLoading ? "Extracting..." : "Analyze Needs"}
            </button>
            {requiredSkills && (
              <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl mt-1 fade-in">
                <p className="text-xs text-emerald-400 mb-1 uppercase tracking-wider font-bold">Required Skills Found:</p>
                <p className="text-sm font-medium text-emerald-100 leading-relaxed max-h-32 overflow-y-auto">{requiredSkills}</p>
              </div>
            )}
          </section>

          <section className="glass-dark p-6 rounded-3xl flex flex-col gap-4 border-t border-white/10 relative overflow-hidden group">
             <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-500 to-orange-400 opacity-50 group-hover:opacity-100 transition-opacity"></div>
            <h2 className="text-xl font-bold text-white">📂 Bulk Upload Resumes</h2>
            <p className="text-sm text-slate-400">Select multiple PDF/DOCX files. The AI will parse them all automatically and generate scores in a single pass.</p>            
            <label className={`mt-2 border-2 border-dashed ${requiredSkills && !isUploading ? 'border-pink-500/40 hover:border-pink-500 hover:bg-pink-500/5 cursor-pointer' : 'border-white/10 cursor-not-allowed opacity-50'} rounded-2xl p-8 text-center transition-all ${isUploading ? 'animate-pulse bg-white/5' : ''}`}>
              <p className="text-sm font-bold text-slate-200">
                  {isUploading ? 'Uploading & Processing...' : (requiredSkills ? 'Select Resumes to Match' : 'Extract JD Skills First')}
              </p>
              <p className="text-xs text-slate-500 mt-2 font-medium">Multiple files allowed</p>
              <input type="file" multiple className="hidden" accept=".pdf,.docx" onChange={handleFileUpload} disabled={!requiredSkills || isUploading} />
            </label>
          </section>
        </div>

        {/* Right Column (Leaderboard) */}
        <div className="lg:col-span-2 glass-dark p-6 rounded-3xl flex flex-col border-t border-white/10 relative overflow-hidden group">
           <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-400 to-blue-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2 text-white">
            🏆 Master Applicant Leaderboard
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse whitespace-nowrap">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 text-xs uppercase tracking-wider">
                  <th className="pb-4 font-bold px-4">Candidate</th>
                  <th className="pb-4 font-bold px-4 w-48">AI Match Score</th>
                  <th className="pb-4 font-bold px-4">Current Status</th>
                  <th className="pb-4 font-bold px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {candidates.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-12 text-center text-slate-500 text-sm font-medium">
                        No candidates found. Start by uploading resumes!
                    </td>
                  </tr>
                ) : (
                  candidates.map((c, i) => (
                    <tr key={c.id} className="border-b border-white/5 hover:bg-white/5 transition-colors group/row fade-in" style={{animationDelay: `${i * 0.05}s`}}>
                      <td className="py-5 px-4 font-semibold text-slate-200 text-sm">
                          <div className="flex items-center gap-2">
                              {c.name}
                              <button onClick={() => handleRename(c.id, c.name)} className="text-slate-500 hover:text-white transition-colors border border-transparent hover:border-white/10 rounded px-1" title="Rename Candidate">✏️</button>
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
                        <select 
                            value={['Hold','Scheduled','Rejected'].includes(c.status) ? c.status : 'Hold'}
                            onChange={(e) => handleStatusChange(c.id, e.target.value)}
                            className={`bg-slate-900 border border-slate-700 text-xs rounded-lg p-1.5 outline-none font-medium cursor-pointer transition-colors ${
                                c.status === "Scheduled" ? "text-emerald-400 border-emerald-500/30" :
                                c.status === "Rejected" ? "text-rose-400 border-rose-500/30" :
                                "text-amber-400 border-amber-500/30"
                            }`}
                        >
                            <option value="Hold">Hold</option>
                            <option value="Scheduled">Scheduled</option>
                            <option value="Rejected">Rejected</option>
                        </select>
                      </td>
                      <td className="py-5 px-4 text-right">
                        <button 
                            disabled={c.status === 'Rejected'}
                            onClick={() => handleEvaluate(c.id)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm ${c.status === 'Rejected' ? 'bg-white/5 text-slate-600 border border-white/5 cursor-not-allowed opacity-50' : 'bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 hover:border-white/20 active:scale-95'} mr-2`}
                        >
                            Screen
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
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-2">
          
          {/* Scheduling Dashboard */}
          <section className="glass-dark p-6 rounded-3xl flex flex-col gap-5 border-t border-white/10 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 to-teal-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">📅 Scheduled Interviews Panel</h2>
            <p className="text-sm text-slate-400 mb-2">Candidates marked as "Scheduled" or "Shortlisted" appear here.</p>
            
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
                            <div className="flex gap-2 items-center w-full mt-2">
                                <input 
                                    type="email"
                                    placeholder="Candidate Email"
                                    className="bg-black/50 border border-white/10 text-slate-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-500/50 flex-1"
                                    value={candidateEmails[c.id] || ""}
                                    onChange={(e) => setCandidateEmails({...candidateEmails, [c.id]: e.target.value})}
                                />
                                <input 
                                    type="date" 
                                    className="bg-black/50 border border-white/10 text-slate-300 rounded-lg p-2 text-sm focus:outline-none focus:border-emerald-500/50 w-[140px]"
                                    value={interviewDates[c.id] || ""}
                                    onChange={(e) => setInterviewDates({...interviewDates, [c.id]: e.target.value})}
                                />
                                <button
                                    onClick={() => handleScheduleInterview(c.id, c.name)}
                                    className="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-2 px-4 rounded-lg text-sm active:scale-95 transition-all whitespace-nowrap"
                                >
                                    Set Date & Email
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
          </section>

          {/* Feedback Dashboard */}
          <section className="glass-dark p-6 rounded-3xl flex flex-col gap-5 border-t border-white/10 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-400 to-orange-500 opacity-50 group-hover:opacity-100 transition-opacity"></div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">📝 Interview Feedback</h2>
            
            <select 
                className="bg-slate-900/80 border border-white/10 text-slate-300 rounded-xl p-3 text-sm focus:outline-none focus:border-amber-500/50"
                value={feedbackState.candidateId}
                onChange={e => setFeedbackState({...feedbackState, candidateId: e.target.value})}
            >
                <option value="">Select a Candidate...</option>
                {candidates.map(c => (
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
                className="w-full h-24 bg-slate-900/80 border border-white/10 rounded-xl p-3 text-sm focus:outline-none focus:border-amber-500/50 resize-none text-slate-300 placeholder-slate-600"
                placeholder="Qualitative feedback and interview notes..."
                value={feedbackState.text}
                onChange={e => setFeedbackState({...feedbackState, text: e.target.value})}
            ></textarea>

            <button 
                onClick={handleSubmitFeedback}
                className="w-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold py-3 rounded-xl transition-all shadow-xl hover:shadow-orange-500/20 active:scale-95"
            >
                Submit Feedback
            </button>            
          </section>
      </div>

    </main>
  );
}
