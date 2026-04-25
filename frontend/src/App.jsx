import {
  CheckCircle,
  FileText,
  LogOut,
  RefreshCw,
  RotateCcw,
  Save,
  Send,
  Upload,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { apiRequest } from "./api";

const PRESET_TOKENS = [
  { label: "Draft merchant", token: "merchant-draft-token" },
  { label: "Review merchant", token: "merchant-review-token" },
  { label: "Reviewer", token: "reviewer-token" },
];

const DOCUMENT_TYPES = [
  { value: "pan", label: "PAN" },
  { value: "aadhaar", label: "Aadhaar" },
  { value: "bank_statement", label: "Bank statement" },
];

const INITIAL_FORM = {
  personal_name: "",
  personal_email: "",
  phone: "",
  business_name: "",
  business_type: "agency",
  expected_monthly_volume_usd: "",
};

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("playto_token") || "reviewer-token");
  const [account, setAccount] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function login(nextToken = token) {
    setLoading(true);
    setError("");
    try {
      const me = await apiRequest("/auth/me/", { token: nextToken });
      setAccount(me);
      setToken(nextToken);
      localStorage.setItem("playto_token", nextToken);
    } catch (err) {
      setAccount(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    login(token);
  }, []);

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-brand">Playto Pay</p>
            <h1 className="text-2xl font-semibold text-ink">KYC pipeline</h1>
          </div>
          {account && (
            <div className="flex items-center gap-3 rounded-md border border-line bg-slate-50 px-3 py-2 text-sm">
              <span className="font-medium">{account.username}</span>
              <StatusBadge status={account.role} />
              <button
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line bg-white text-slate-700 hover:bg-slate-100"
                title="Log out"
                onClick={() => {
                  localStorage.removeItem("playto_token");
                  setAccount(null);
                }}
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 lg:px-6">
        {!account ? (
          <LoginPanel
            token={token}
            setToken={setToken}
            login={login}
            error={error}
            loading={loading}
          />
        ) : account.role === "reviewer" ? (
          <ReviewerPortal token={token} />
        ) : (
          <MerchantPortal token={token} />
        )}
      </main>
    </div>
  );
}

function LoginPanel({ token, setToken, login, error, loading }) {
  return (
    <section className="max-w-xl">
      <div className="mb-4 flex flex-wrap gap-2">
        {PRESET_TOKENS.map((preset) => (
          <button
            key={preset.token}
            className="rounded-md border border-line bg-white px-3 py-2 text-sm font-medium hover:border-brand"
            onClick={() => {
              setToken(preset.token);
              login(preset.token);
            }}
          >
            {preset.label}
          </button>
        ))}
      </div>
      <div className="rounded-md border border-line bg-white p-4 shadow-soft">
        <label className="mb-2 block text-sm font-medium" htmlFor="token">
          API token
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="token"
            className="min-h-11 flex-1 rounded-md border border-line px-3"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
          <button
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-brand px-4 font-semibold text-white hover:bg-green-800 disabled:opacity-60"
            disabled={loading}
            onClick={() => login(token)}
          >
            <UserCheck size={18} />
            Sign in
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      </div>
    </section>
  );
}

function MerchantPortal({ token }) {
  const [submission, setSubmission] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [step, setStep] = useState("personal");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadSubmission() {
    setBusy(true);
    setError("");
    try {
      const data = await apiRequest("/merchant/submission/", { token });
      setSubmission(data);
      setForm({ ...INITIAL_FORM, ...normalizeSubmission(data) });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadSubmission();
  }, [token]);

  async function saveProgress() {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const data = await apiRequest("/merchant/submission/", {
        token,
        method: "PATCH",
        body: form,
      });
      setSubmission(data);
      setMessage("Progress saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submitKyc() {
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const data = await apiRequest("/merchant/submission/submit/", {
        token,
        method: "POST",
        body: {},
      });
      setSubmission(data);
      setMessage("Submitted for review.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function uploadDocument(documentType, file) {
    if (!file) return;
    setBusy(true);
    setMessage("");
    setError("");
    const body = new FormData();
    body.append("document_type", documentType);
    body.append("file", file);
    try {
      await apiRequest("/merchant/submission/documents/", {
        token,
        method: "POST",
        body,
        isFormData: true,
      });
      setMessage("Document uploaded.");
      await loadSubmission();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const editable = submission?.state === "draft" || submission?.state === "more_info_requested";

  return (
    <section className="grid gap-6 lg:grid-cols-[220px_1fr]">
      <aside className="space-y-2">
        {["personal", "business", "documents"].map((name) => (
          <button
            key={name}
            className={`w-full rounded-md border px-3 py-3 text-left text-sm font-semibold capitalize ${
              step === name ? "border-brand bg-green-50 text-brand" : "border-line bg-white"
            }`}
            onClick={() => setStep(name)}
          >
            {name}
          </button>
        ))}
        {submission && <StatusBadge status={submission.state} />}
      </aside>

      <div className="rounded-md border border-line bg-white p-5 shadow-soft">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Merchant submission</h2>
            <p className="text-sm text-slate-600">Submission #{submission?.id || "new"}</p>
          </div>
          <button
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-line bg-white hover:bg-slate-100"
            title="Refresh"
            onClick={loadSubmission}
          >
            <RefreshCw size={16} />
          </button>
        </div>

        {step === "personal" && (
          <div className="grid gap-4 md:grid-cols-2">
            <TextInput label="Name" value={form.personal_name} onChange={(v) => setFormValue(setForm, "personal_name", v)} disabled={!editable} />
            <TextInput label="Email" value={form.personal_email} onChange={(v) => setFormValue(setForm, "personal_email", v)} disabled={!editable} />
            <TextInput label="Phone" value={form.phone} onChange={(v) => setFormValue(setForm, "phone", v)} disabled={!editable} />
          </div>
        )}

        {step === "business" && (
          <div className="grid gap-4 md:grid-cols-2">
            <TextInput label="Business name" value={form.business_name} onChange={(v) => setFormValue(setForm, "business_name", v)} disabled={!editable} />
            <label className="block text-sm font-medium">
              Business type
              <select
                className="mt-2 min-h-11 w-full rounded-md border border-line px-3 disabled:bg-slate-100"
                value={form.business_type}
                disabled={!editable}
                onChange={(event) => setFormValue(setForm, "business_type", event.target.value)}
              >
                <option value="agency">Agency</option>
                <option value="freelancer">Freelancer</option>
                <option value="studio">Studio</option>
                <option value="other">Other</option>
              </select>
            </label>
            <TextInput
              label="Expected monthly volume USD"
              type="number"
              value={form.expected_monthly_volume_usd}
              onChange={(v) => setFormValue(setForm, "expected_monthly_volume_usd", v)}
              disabled={!editable}
            />
          </div>
        )}

        {step === "documents" && (
          <div className="grid gap-3">
            {DOCUMENT_TYPES.map((docType) => {
              const existing = submission?.documents?.find((doc) => doc.document_type === docType.value);
              return (
                <div key={docType.value} className="flex flex-col gap-3 rounded-md border border-line p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-semibold">{docType.label}</p>
                    <p className="text-sm text-slate-600">{existing ? existing.original_filename : "Not uploaded"}</p>
                  </div>
                  <label className={`inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-md border border-line px-3 text-sm font-medium ${editable ? "bg-white hover:bg-slate-100" : "bg-slate-100 text-slate-500"}`}>
                    <Upload size={16} />
                    Upload
                    <input
                      className="hidden"
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      disabled={!editable}
                      onChange={(event) => uploadDocument(docType.value, event.target.files?.[0])}
                    />
                  </label>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-md border border-line px-4 font-semibold hover:bg-slate-100 disabled:opacity-60"
            disabled={busy || !editable}
            onClick={saveProgress}
          >
            <Save size={17} />
            Save
          </button>
          <button
            className="inline-flex min-h-11 items-center gap-2 rounded-md bg-brand px-4 font-semibold text-white hover:bg-green-800 disabled:opacity-60"
            disabled={busy || !editable}
            onClick={submitKyc}
          >
            <Send size={17} />
            Submit
          </button>
          {busy && <span className="text-sm text-slate-600">Working...</span>}
          {message && <span className="text-sm font-medium text-brand">{message}</span>}
          {error && <span className="text-sm font-medium text-red-700">{error}</span>}
        </div>
      </div>
    </section>
  );
}

function ReviewerPortal({ token }) {
  const [dashboard, setDashboard] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [selected, setSelected] = useState(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadDashboard() {
    setBusy(true);
    setError("");
    try {
      const data = await apiRequest("/reviewer/dashboard/", { token });
      setDashboard(data);
      const firstId = data.queue[0]?.id;
      setSelectedId((current) => current || firstId || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function loadSubmission(id) {
    if (!id) {
      setSelected(null);
      return;
    }
    setError("");
    try {
      const data = await apiRequest(`/reviewer/submissions/${id}/`, { token });
      setSelected(data);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, [token]);

  useEffect(() => {
    loadSubmission(selectedId);
  }, [selectedId]);

  async function transition(action) {
    if (!selected) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const data = await apiRequest(`/reviewer/submissions/${selected.id}/transition/`, {
        token,
        method: "POST",
        body: { action, reason },
      });
      setSelected(data);
      setReason("");
      setMessage("State updated.");
      await loadDashboard();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const metrics = dashboard?.metrics;

  return (
    <section className="space-y-6">
      <div className="grid gap-3 md:grid-cols-3">
        <Metric label="In queue" value={metrics?.submissions_in_queue ?? "-"} />
        <Metric label="Avg queue time" value={formatDuration(metrics?.average_time_in_queue_seconds)} />
        <Metric label="7 day approval rate" value={metrics?.approval_rate_last_7_days == null ? "No decisions" : `${metrics.approval_rate_last_7_days}%`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <div className="rounded-md border border-line bg-white shadow-soft">
          <div className="flex items-center justify-between border-b border-line p-4">
            <h2 className="text-lg font-semibold">Reviewer queue</h2>
            <button
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line hover:bg-slate-100"
              title="Refresh"
              onClick={loadDashboard}
            >
              <RefreshCw size={16} />
            </button>
          </div>
          <div className="max-h-[560px] overflow-auto p-2">
            {dashboard?.queue?.length ? (
              dashboard.queue.map((item) => (
                <button
                  key={item.id}
                  className={`mb-2 w-full rounded-md border p-3 text-left hover:border-brand ${
                    selectedId === item.id ? "border-brand bg-green-50" : "border-line bg-white"
                  }`}
                  onClick={() => setSelectedId(item.id)}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold">{item.business_name || `Submission #${item.id}`}</p>
                    <StatusBadge status={item.state} />
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{item.merchant_username}</p>
                  <div className="mt-3 flex items-center gap-2 text-xs">
                    <span>{item.age_hours}h in queue</span>
                    {item.at_risk && <span className="rounded bg-amber-100 px-2 py-1 font-semibold text-amber-800">At risk</span>}
                  </div>
                </button>
              ))
            ) : (
              <p className="p-4 text-sm text-slate-600">No active submissions.</p>
            )}
          </div>
        </div>

        <div className="rounded-md border border-line bg-white p-5 shadow-soft">
          {selected ? (
            <SubmissionDetail
              submission={selected}
              reason={reason}
              setReason={setReason}
              transition={transition}
              busy={busy}
            />
          ) : (
            <p className="text-sm text-slate-600">Select a queue item.</p>
          )}
          <div className="mt-4 min-h-6">
            {message && <span className="text-sm font-medium text-brand">{message}</span>}
            {error && <span className="text-sm font-medium text-red-700">{error}</span>}
          </div>
        </div>
      </div>
    </section>
  );
}

function SubmissionDetail({ submission, reason, setReason, transition, busy }) {
  const canStart = submission.state === "submitted";
  const canDecide = submission.state === "under_review";

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{submission.business_name || `Submission #${submission.id}`}</h2>
          <p className="text-sm text-slate-600">{submission.merchant_username}</p>
        </div>
        <StatusBadge status={submission.state} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Info label="Name" value={submission.personal_name} />
        <Info label="Email" value={submission.personal_email} />
        <Info label="Phone" value={submission.phone} />
        <Info label="Business type" value={submission.business_type} />
        <Info label="Monthly volume" value={`$${submission.expected_monthly_volume_usd || 0}`} />
        <Info label="Reviewer" value={submission.reviewer_username || "Unassigned"} />
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Documents</h3>
        <div className="grid gap-2">
          {submission.documents.map((document) => (
            <a
              key={document.id}
              className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-medium hover:border-brand"
              href={document.file}
              target="_blank"
              rel="noreferrer"
            >
              <FileText size={16} />
              {document.document_type}: {document.original_filename}
            </a>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <label className="block text-sm font-medium" htmlFor="reason">
          Reviewer reason
        </label>
        <textarea
          id="reason"
          className="mt-2 min-h-28 w-full rounded-md border border-line p-3"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Decision reason or more information request"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-md border border-line px-3 font-semibold hover:bg-slate-100 disabled:opacity-50"
          disabled={!canStart || busy}
          onClick={() => transition("start_review")}
        >
          <UserCheck size={17} />
          Start review
        </button>
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-md bg-brand px-3 font-semibold text-white hover:bg-green-800 disabled:opacity-50"
          disabled={!canDecide || busy}
          onClick={() => transition("approve")}
        >
          <CheckCircle size={17} />
          Approve
        </button>
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-md bg-red-700 px-3 font-semibold text-white hover:bg-red-800 disabled:opacity-50"
          disabled={!canDecide || busy}
          onClick={() => transition("reject")}
        >
          <XCircle size={17} />
          Reject
        </button>
        <button
          className="inline-flex min-h-10 items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 font-semibold text-amber-900 hover:bg-amber-100 disabled:opacity-50"
          disabled={!canDecide || busy}
          onClick={() => transition("request_more_info")}
        >
          <RotateCcw size={17} />
          More info
        </button>
      </div>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-line bg-white p-4 shadow-soft">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    reviewer: "bg-slate-100 text-slate-700",
    merchant: "bg-green-100 text-green-800",
    draft: "bg-slate-100 text-slate-700",
    submitted: "bg-blue-100 text-blue-800",
    under_review: "bg-amber-100 text-amber-800",
    approved: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
    more_info_requested: "bg-orange-100 text-orange-800",
  };
  return (
    <span className={`inline-flex rounded px-2 py-1 text-xs font-semibold ${colors[status] || colors.draft}`}>
      {String(status).replaceAll("_", " ")}
    </span>
  );
}

function TextInput({ label, value, onChange, type = "text", disabled = false }) {
  return (
    <label className="block text-sm font-medium">
      {label}
      <input
        className="mt-2 min-h-11 w-full rounded-md border border-line px-3 disabled:bg-slate-100"
        type={type}
        value={value ?? ""}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function Info({ label, value }) {
  return (
    <div className="rounded-md border border-line p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 break-words text-sm">{value || "Not provided"}</p>
    </div>
  );
}

function setFormValue(setForm, key, value) {
  setForm((current) => ({ ...current, [key]: value }));
}

function normalizeSubmission(submission) {
  return {
    personal_name: submission.personal_name || "",
    personal_email: submission.personal_email || "",
    phone: submission.phone || "",
    business_name: submission.business_name || "",
    business_type: submission.business_type || "agency",
    expected_monthly_volume_usd: submission.expected_monthly_volume_usd || "",
  };
}

function formatDuration(seconds) {
  if (seconds == null) return "-";
  if (seconds < 60) return `${seconds}s`;
  const hours = seconds / 3600;
  if (hours < 1) return `${Math.round(seconds / 60)}m`;
  return `${hours.toFixed(1)}h`;
}

