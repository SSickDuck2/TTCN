const API_BASE_URL = 'http://localhost:8000/api';

interface FetchOptions extends RequestInit {
  requireAuth?: boolean;
}

export const fetchApi = async (endpoint: string, options: FetchOptions = {}) => {
  const { requireAuth = true, headers = {}, ...restOptions } = options;

  let requestHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    ...headers,
  };

  if (requireAuth) {
    let token = null;
    if (typeof window !== 'undefined') {
      token = localStorage.getItem('token');
    }
    if (token) {
      requestHeaders = {
        ...requestHeaders,
        Authorization: `Bearer ${token}`,
      };
    } else {
      if (typeof window !== 'undefined' && window.location.pathname !== '/') {
        window.location.href = '/';
      }
    }
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: requestHeaders,
      ...restOptions,
    });

    if (response.status === 401 && requireAuth) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        if (window.location.pathname !== '/') {
          window.location.href = '/';
        }
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'API request failed');
    }

    return await response.json();
  } catch (error) {
    throw error;
  }
};

// ─── V2 API Functions ──────────────────────────────────────────────────────────

/** Trả về thông tin thời gian và trạng thái TTCN hiện tại */
export const getTimeStatus = () => fetchApi('/time/status');

/** Lấy thông tin hợp đồng công khai của cầu thủ */
export const getPlayerPublicInfo = (playerId: number) =>
  fetchApi(`/market/player-info/${playerId}/public`);

/** Lấy thông tin hợp đồng riêng tư (cần là chủ sở hữu hoặc đang đàm phán) */
export const getPlayerPrivateInfo = (playerId: number) =>
  fetchApi(`/market/player-info/${playerId}/private`);

/** Gửi Inquiry hỏi mua trực tiếp → Tạo Negotiation mới */
export const sendInquiry = (playerId: number) =>
  fetchApi('/market/inquire', {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId }),
  });

/** Quick Sell cầu thủ cho hệ thống (lấy 50% giá trị) */
export const quickSellPlayer = (playerId: number) =>
  fetchApi('/market/quick-sell', {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId }),
  });

/** Lấy trạng thái một phiên đàm phán */
export const getNegotiation = (negotiationId: number) =>
  fetchApi(`/negotiations/${negotiationId}`);

/** Trả lời Inquiry (bên bán đồng ý/từ chối) */
export const respondToInquiry = (negotiationId: number, accept: boolean, initialDemand?: number) =>
  fetchApi(`/negotiations/${negotiationId}/respond-inquiry`, {
    method: 'POST',
    body: JSON.stringify({ accept, initial_demand: initialDemand ?? 0 }),
  });

/** Bên mua gửi giá mua */
export const submitOffer = (negotiationId: number, offerAmount: number) =>
  fetchApi(`/negotiations/${negotiationId}/offer`, {
    method: 'POST',
    body: JSON.stringify({ offer_amount: offerAmount }),
  });

/** Bên bán trả giá lại */
export const respondToOffer = (negotiationId: number, demandAmount: number) =>
  fetchApi(`/negotiations/${negotiationId}/counter`, {
    method: 'POST',
    body: JSON.stringify({ demand_amount: demandAmount }),
  });

/** Hủy đàm phán */
export const cancelNegotiation = (negotiationId: number) =>
  fetchApi(`/negotiations/${negotiationId}/cancel`, { method: 'POST' });

/** Đặt câu hỏi trong phiên đàm phán */
export const askNegotiationQuestion = (negotiationId: number, questionId: number) =>
  fetchApi(`/negotiations/${negotiationId}/ask`, {
    method: 'POST',
    body: JSON.stringify({ question_id: questionId }),
  });

/** Lấy danh sách 20 câu hỏi đàm phán */
export const getNegotiationQuestions = () => fetchApi('/negotiations/questions');

// ===== ADMIN API =====
export async function adminSetState(state: string) {
  return fetchApi('/admin/time/set-state', {
    method: 'POST',
    body: JSON.stringify({ state }),
  });
}

export async function adminAdvanceTime(days: number) {
  return fetchApi('/admin/time/advance', {
    method: 'POST',
    body: JSON.stringify({ days }),
  });
}

export async function adminTriggerSimulation() {
  return fetchApi('/admin/simulation/trigger', {
    method: 'POST',
  });
}

export async function adminGetClubsInDebt() {
  return fetchApi('/admin/clubs/debt');
}

export async function adminGetSimulationStatus() {
  return fetchApi('/admin/simulation/status');
}

export async function adminToggleSimulation() {
  return fetchApi('/admin/simulation/toggle', {
    method: 'POST',
  });
}

export async function adminResetData() {
  return fetchApi('/admin/data/reset', {
    method: 'POST',
  });
}

export async function adminSystemHealth() {
  return fetchApi('/admin/system/health');
}

export async function adminGetAllNegotiations() {
  return fetchApi('/admin/negotiations');
}

export async function adminCancelNegotiation(id: number) {
  return fetchApi(`/admin/negotiations/${id}/cancel`, {
    method: 'POST',
  });
}
