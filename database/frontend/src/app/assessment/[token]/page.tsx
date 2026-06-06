"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";

interface AssessmentDetails {
  token: string;
  candidate_name: string;
  job_title: string;
  language: string;
  question_title: string;
  question_description: string;
  template_code: string;
}

interface EvaluationResult {
  score: number;
  passed: boolean;
  report: string;
}

export default function AssessmentPortal() {
  const params = useParams();
  const token = params?.token as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [details, setDetails] = useState<AssessmentDetails | null>(null);
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);

  // Empty string = relative path via Next.js proxy — works locally and when deployed on Vercel
  const API_BASE = "";

  useEffect(() => {
    if (!token) return;
    fetchDetails();
  }, [token]);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await fetch(`${API_BASE}/api/assessment/${token}`);
      if (!res.ok) {
        throw new Error(await res.text() || "Failed to load assessment details.");
      }
      const data: AssessmentDetails = await res.json();
      setDetails(data);
      setCode(data.template_code || "");
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Invalid or expired assessment link.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!token || !details) return;
    try {
      setSubmitting(true);
      setResult(null);
      const res = await fetch(`${API_BASE}/api/assessment/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: token,
          submitted_code: code,
          code_language: details.language,
        }),
      });

      if (!res.ok) {
        throw new Error(await res.text() || "Submission failed.");
      }
      const data: EvaluationResult = await res.json();
      setResult(data);
    } catch (err: any) {
      alert(err.message || "Error submitting code.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = code.substring(0, start) + "    " + code.substring(end);
      setCode(newValue);
      
      // Reset cursor position
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 4;
      }, 0);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center font-sans">
        <div className="relative w-16 h-16 mb-4">
          <div className="absolute inset-0 rounded-full border-4 border-emerald-500/20 animate-ping"></div>
          <div className="absolute inset-0 rounded-full border-4 border-t-emerald-500 border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
        </div>
        <p className="text-slate-400 font-medium tracking-wide animate-pulse">Initializing Coding Workspace...</p>
      </div>
    );
  }

  if (error || !details) {
    return (
      <div className="min-h-screen bg-slate-950 text-white flex flex-col items-center justify-center font-sans p-6">
        <div className="max-w-md w-full bg-slate-900/50 backdrop-blur-md border border-red-500/25 p-8 rounded-2xl text-center shadow-2xl">
          <div className="w-16 h-16 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">⚠️</div>
          <h2 className="text-xl font-bold text-red-400 mb-2">Workspace Error</h2>
          <p className="text-slate-400 mb-6">{error || "Could not retrieve assessment link details. Please contact support."}</p>
          <button onClick={fetchDetails} className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 transition text-sm font-semibold rounded-lg">
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white flex flex-col font-sans">
      {/* Top Banner Header */}
      <header className="px-6 py-4 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center font-bold text-slate-950">
            A
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">RECRUITER AI ASSESSMENT</h1>
            <p className="text-xs text-slate-500">Candidate Workspace • Real-time Compiler Mode</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-6">
          <div className="text-right">
            <span className="text-xs text-slate-500 block">Candidate</span>
            <span className="text-xs font-semibold text-emerald-400">{details.candidate_name}</span>
          </div>
          <div className="text-right border-l border-slate-800 pl-6">
            <span className="text-xs text-slate-500 block">Applying For</span>
            <span className="text-xs font-semibold text-slate-300">{details.job_title}</span>
          </div>
        </div>
      </header>

      {/* Main Workspace Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 overflow-hidden">
        {/* Left Side: Question Pane */}
        <div className="p-8 overflow-y-auto border-r border-slate-900 flex flex-col space-y-6">
          <div className="space-y-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider">
              Coding Challenge
            </span>
            <h2 className="text-2xl font-bold text-slate-100">{details.question_title}</h2>
          </div>

          <div className="bg-slate-900/40 border border-slate-800/50 rounded-xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Problem Statement</h3>
            <div className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
              {details.question_description}
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Instructions</h3>
            <ul className="text-xs text-slate-400 space-y-2 list-disc pl-4">
              <li>Read the problem statement and template code carefully.</li>
              <li>Ensure the solution is written in the required language and structure.</li>
              <li>Do not rename the core function, as it matches compiler check cases.</li>
              <li>Click the Submit code button to compile and evaluate your code.</li>
            </ul>
          </div>
        </div>

        {/* Right Side: Code Editor Workspace */}
        <div className="flex flex-col bg-slate-900/20">
          {/* Editor Header Tools */}
          <div className="px-6 py-3 bg-slate-900/50 border-b border-slate-900/80 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{details.language} Editor</span>
            </div>
            <button
              onClick={() => {
                if (confirm("Reset code editor to initial template? All changes will be lost.")) {
                  setCode(details.template_code || "");
                }
              }}
              className="text-xs text-slate-500 hover:text-slate-300 transition"
            >
              Reset Template
            </button>
          </div>

          {/* Text Editor */}
          <div className="flex-1 relative min-h-[350px]">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={handleKeyDown}
              className="absolute inset-0 w-full h-full p-6 bg-slate-950 font-mono text-sm text-slate-200 focus:outline-none focus:ring-0 resize-none leading-relaxed"
              spellCheck="false"
              placeholder="// Write your code solution here..."
            />
          </div>

          {/* Footer Submit Actions */}
          <div className="p-6 bg-slate-900/40 border-t border-slate-900 flex items-center justify-between">
            <div className="text-xs text-slate-500 font-medium">
              💡 ProTip: Press <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">Tab</kbd> for 4 spaces indent.
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting || !code.trim()}
              className="relative overflow-hidden px-8 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold rounded-lg shadow-lg hover:shadow-emerald-500/20 hover:scale-[1.02] disabled:opacity-50 disabled:pointer-events-none transition duration-200"
            >
              {submitting ? (
                <span className="flex items-center space-x-2">
                  <span className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin"></span>
                  <span>Compiling...</span>
                </span>
              ) : (
                "Submit Solution"
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Grader Overlay Modal / Panel */}
      {result && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-6 animate-fade-in">
          <div className="max-w-2xl w-full bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className={`px-6 py-4 flex items-center justify-between border-b border-slate-800 ${result.passed ? "bg-emerald-500/5" : "bg-red-500/5"}`}>
              <div className="flex items-center space-x-3">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${result.passed ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                  {result.passed ? "✓" : "✗"}
                </span>
                <div>
                  <h3 className="text-base font-bold">Grading Report Compiled</h3>
                  <p className="text-xs text-slate-500">Evaluation finished successfully</p>
                </div>
              </div>
              <div className="text-right">
                <span className="text-xs text-slate-500 block">Overall Score</span>
                <span className={`text-xl font-black ${result.passed ? "text-emerald-400" : "text-red-400"}`}>{result.score}/100</span>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Grader Feedback</h4>
                <p className="text-sm text-slate-300 leading-relaxed bg-slate-950 p-4 rounded-xl border border-slate-900 whitespace-pre-wrap">
                  {result.report}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-950 border border-slate-900 flex items-center justify-between">
                <div>
                  <span className="text-xs text-slate-500 block">Assessment Status</span>
                  <span className={`text-sm font-bold ${result.passed ? "text-emerald-400" : "text-red-400"}`}>
                    {result.passed ? "PASSED (Next Stage: Interview scheduled)" : "RE-EVALUATION PLACED (Below Pass Threshold)"}
                  </span>
                </div>
                {result.passed ? (
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Qualified
                  </span>
                ) : (
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
                    Failed
                  </span>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-slate-900/50 border-t border-slate-800/80 flex items-center justify-end">
              <button
                onClick={() => setResult(null)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 transition text-sm font-semibold rounded-lg text-slate-300"
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
