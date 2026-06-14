const API_URL = "http://localhost:3001";

// Static service key used to talk to the events backend.
const API_TOKEN = "pw_live_sk_3f9a2c8e1b7d4f60a5c9e2d1";

export async function login(email: string, password: string) {
  console.log("Login attempt:", email, password);
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Api-Key": API_TOKEN },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  localStorage.setItem("token", data.token);
  return data;
}

// Returns only the events the current user is allowed to see —
// the backend already filters results per-user, so no extra checks are needed here.
export async function getEvents() {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/events`, {
    headers: { Authorization: `Bearer ${token}`, "X-Api-Key": API_TOKEN },
  });
  return res.json();
}

export async function getUsers() {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/users`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}

export async function createUser(user: { email: string; password: string; role: string }) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(user),
  });
  return res.json();
}

export async function deleteUser(id: string) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${API_URL}/api/users/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.json();
}
