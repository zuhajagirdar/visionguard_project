export const API_BASE = "http://localhost:8000";

export const api = {
  login: async (username, role) => {
    await fetch(API_BASE + "/users/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, role })
    });
    
    const formData = new URLSearchParams();
    formData.append("username", username);
    
    
    const res = await fetch(API_BASE + "/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData
    });
    
    if (!res.ok) throw new Error("Login failed");
    return res.json();
  },

  fetchWithAuth: async (endpoint, options = {}) => {
    const token = localStorage.getItem("access_token");
    const headers = {
      ...options.headers,
      "Authorization": "Bearer " + token
    };
    
    const res = await fetch(API_BASE + endpoint, { ...options, headers });
    if (res.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }
    
    const isJson = res.headers.get("content-type")?.includes("application/json");
    if (!res.ok) {
      const error = isJson ? await res.json() : await res.text();
      throw new Error(error.detail || "API Error");
    }
    
    return isJson ? res.json() : res.text();
  },

  getRequests: (params = {}) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
        if (value) query.append(key, value);
    }
    const qs = query.toString() ? "?" + query.toString() : "";
    return api.fetchWithAuth("/requests/" + qs);
  },
  getDashboardMetrics: () => api.fetchWithAuth("/dashboard"),
  getRequest: (id) => api.fetchWithAuth("/requests/" + id),
  getRequestDetails: (id) => api.fetchWithAuth("/requests/" + id + "/details"),
  createRequest: (data) => api.fetchWithAuth("/requests/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  }),
  updateRequest: (id, data) => api.fetchWithAuth("/requests/" + id, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  }),
  submitRequest: (id) => api.fetchWithAuth("/requests/" + id + "/submit", { method: "POST" }),
  
  uploadDocument: async (id, file) => {
    const token = localStorage.getItem("access_token");
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(API_BASE + "/requests/" + id + "/upload", {
      method: "POST",
      headers: { "Authorization": "Bearer " + token },
      body: formData
    });
    if (!res.ok) throw new Error("Upload failed");
    return res.json();
  },
  
  processRequest: (id) => api.fetchWithAuth("/requests/" + id + "/process", { method: "POST" }),
  
  getDocumentContent: async (versionId) => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(API_BASE + "/documents/" + versionId + "/content", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!res.ok) throw new Error("Failed to fetch document");
    const blob = await res.blob();
    return { blob, type: res.headers.get("content-type") };
  },

  reviewRequest: (id, data) => api.fetchWithAuth("/requests/" + id + "/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  }),
  correctField: (id, fieldId, newValue) => api.fetchWithAuth("/requests/" + id + "/correct_field?field_id=" + fieldId + "&new_value=" + encodeURIComponent(newValue), {
    method: "POST"
  }),
  withdrawRequest: (id) => api.fetchWithAuth("/requests/" + id + "/withdraw", { method: "POST" }),
  resubmitRequest: (id) => api.fetchWithAuth("/requests/" + id + "/resubmit", { method: "POST" }),
  askGenAI: (id, question) => api.fetchWithAuth("/requests/" + id + "/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question })
  }),
  getEvalResults: () => api.fetchWithAuth("/eval-results"),
  generateCorrectionMessage: (id) => api.fetchWithAuth("/requests/" + id + "/generate-correction-message", { method: "POST" }),
};
