const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export async function apiRequest(path, { token, method = "GET", body, isFormData = false } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Token ${token}`;
  if (!isFormData) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(formatErrors(data));
  }
  return data;
}

function formatErrors(data) {
  const errors = data?.errors || data;
  if (!errors || Object.keys(errors).length === 0) return "Request failed.";
  return flatten(errors).join(" ");
}

function flatten(value) {
  if (Array.isArray(value)) return value.flatMap(flatten);
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, nested]) =>
      flatten(nested).map((message) => `${key}: ${message}`)
    );
  }
  return [String(value)];
}

