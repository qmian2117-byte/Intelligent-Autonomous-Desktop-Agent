/**
 * API service connecting React to the DesktopPilot AI FastAPI backend.
 */

const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

export async function sendChatMessage(message, sessionId = null) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return await response.json();
}

export async function sendApprovalDecision(token, approved) {
  const response = await fetch(`${API_BASE_URL}/chat/approve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      token: token,
      approved: approved,
    }),
  });

  if (!response.ok) {
    throw new Error(`Approval API error: ${response.statusText}`);
  }

  return await response.json();
}

export async function getSystemHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return await response.json();
  } catch (error) {
    return { backend: "offline", error: error.message };
  }
}

