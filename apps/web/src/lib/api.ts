const API_BASE = typeof window !== 'undefined'
  ? (window.location.port === '3000' || window.location.port === '5173'
      ? 'http://localhost:8001/api/v1'
      : '/api/v1')
  : '/api/v1';

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('ecom_auth_token');
}

export function setAuthSession(token: string, user: any) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('ecom_auth_token', token);
  localStorage.setItem('ecom_user', JSON.stringify(user));
}

export function clearAuthSession() {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('ecom_auth_token');
  localStorage.removeItem('ecom_user');
}

export function getAuthUser(): any | null {
  if (typeof window === 'undefined') return null;
  const user = localStorage.getItem('ecom_user');
  try {
    return user ? JSON.parse(user) : null;
  } catch {
    return null;
  }
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---------------- AUTH APIs ----------------
export async function signupUser(data: { email: string; password: string; name: string; role?: string }) {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Signup failed' }));
    throw new Error(err.detail || 'Signup failed');
  }
  return res.json();
}

export async function loginUser(data: { email: string; password: string }) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Invalid credentials' }));
    throw new Error(err.detail || 'Invalid credentials');
  }
  return res.json();
}

export async function forgotPassword(email: string) {
  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  return res.json();
}

// ---------------- DASHBOARD & OPS APIs ----------------
export async function fetchDashboardSummary() {
  const res = await fetch(`${API_BASE}/dashboard/summary`, {
    headers: { ...authHeaders() }
  });
  if (!res.ok) throw new Error("Failed to fetch dashboard summary");
  return res.json();
}

export async function fetchPendingActions(status?: string) {
  const url = status ? `${API_BASE}/actions?status=${status}` : `${API_BASE}/actions`;
  const res = await fetch(url, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to fetch actions");
  return res.json();
}

export async function approveAction(actionId: string, reason: string = "Approved by operator") {
  const user = getAuthUser();
  const decided_by = user?.email || "admin@autonomous.store";
  const res = await fetch(`${API_BASE}/actions/${actionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ decision: "approved", decided_by, reason })
  });
  if (res.status === 409) {
    throw new Error("Conflict: This action was already approved or decided by another operator.");
  }
  if (res.status === 410) {
    throw new Error("Expired: This action proposal has expired due to data staleness (>24 hours).");
  }
  if (!res.ok) throw new Error("Failed to approve action");
  return res.json();
}

export async function rejectAction(actionId: string, reason: string = "Rejected by operator") {
  const user = getAuthUser();
  const decided_by = user?.email || "admin@autonomous.store";
  const res = await fetch(`${API_BASE}/actions/${actionId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ decision: "rejected", decided_by, reason })
  });
  if (!res.ok) throw new Error("Failed to reject action");
  return res.json();
}

export async function fetchAgentRuns() {
  const res = await fetch(`${API_BASE}/agents/runs`, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to fetch agent runs");
  return res.json();
}

export async function fetchInventoryRisks() {
  const res = await fetch(`${API_BASE}/inventory/risks`);
  if (!res.ok) throw new Error("Failed to fetch inventory risks");
  return res.json();
}


export async function fetchAgentHealth() {
  const res = await fetch(`${API_BASE}/agents/health`, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to fetch agent health");
  return res.json();
}
export async function fetchOrderExceptions() {
  const res = await fetch(`${API_BASE}/orders/exceptions`, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to fetch order exceptions");
  return res.json();
}

export async function fetchTickets() {
  const res = await fetch(`${API_BASE}/tickets`, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to fetch support tickets");
  return res.json();
}

export async function fetchPricingRecommendations() {
  const res = await fetch(`${API_BASE}/pricing/recommendations`, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to fetch pricing recommendations");
  return res.json();
}

export async function triggerDemoScenario() {
  const res = await fetch(`${API_BASE}/simulation/run-demo`, { method: "POST", headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to trigger demo scenario");
  return res.json();
}

// ---------------- STOREFRONT & RESERVATION APIs ----------------
export async function reserveStock(sku_code: string, quantity: number = 1) {
  const user = getAuthUser();
  const res = await fetch(`${API_BASE}/inventory/${sku_code}/reserve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ quantity, user_id: user?.id })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Reservation failed" }));
    throw new Error(err.detail || "Reservation failed");
  }
  return res.json();
}

export async function releaseReservation(reservation_id: string) {
  const res = await fetch(`${API_BASE}/inventory/reservations/${reservation_id}`, {
    method: "DELETE",
    headers: { ...authHeaders() }
  });
  return res.json();
}

export async function checkoutProduct(
  sku_code: string,
  quantity: number = 1,
  customer_name: string = "Demo Shopper",
  customer_email: string = "shopper@example.com",
  shipping_address: string = "742 Evergreen Terrace, Seattle, WA 98101",
  payment_method: string = "Credit Card (•••• 4242)",
  reservation_id?: string
) {
  const idempotencyKey = `idem-checkout-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const res = await fetch(`${API_BASE}/orders/checkout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
      ...authHeaders()
    },
    body: JSON.stringify({
      sku_code,
      quantity,
      customer_name,
      customer_email,
      shipping_address,
      payment_method,
      reservation_id
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Checkout failed" }));
    throw new Error(err.detail || "Checkout failed");
  }
  return res.json();
}

export async function trackOrder(query: string) {
  const res = await fetch(`${API_BASE}/orders/track/${encodeURIComponent(query.trim())}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Order tracking lookup failed" }));
    throw new Error(err.detail || "Order tracking lookup failed");
  }
  return res.json();
}

export async function sendCustomerChat(message: string, order_id?: string, customer_email?: string, language: string = "en") {
  const res = await fetch(`${API_BASE}/tickets/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ message, order_id: order_id || undefined, customer_email: customer_email || "shopper@example.com", language })
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}

export async function restockProduct(sku_code: string, quantity: number = 150) {
  const res = await fetch(`${API_BASE}/inventory/${sku_code}/restock`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ quantity })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Restock failed" }));
    throw new Error(err.detail || "Restock failed");
  }
  return res.json();
}

export async function updateAutonomyLevel(level: number) {
  const res = await fetch(`${API_BASE}/dashboard/autonomy`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ autonomy_level: level })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update autonomy level" }));
    throw new Error(err.detail || "Failed to update autonomy level");
  }
  return res.json();
}

// ---------------- 112 EDGE CASES & GEMINI APIS ----------------
export interface EdgeCaseItem {
  code: string;
  agent: string;
  name: string;
  scenario: string;
  resolution: string;
  priority: string;
  autonomy_level: string | number;
  risk_level: string;
}

export interface EdgeCaseSimulationResult {
  status: string;
  code: string;
  name: string;
  agent: string;
  scenario: string;
  resolution: string;
  priority: string;
  autonomy_level: string;
  risk_level: string;
  summary: string;
  confidence: number;
  evidence: Array<{
    type: string;
    ref: string;
    claim: string;
    confidence?: number;
  }>;
  validation_checklist: {
    margin_floor_passed: boolean;
    map_compliant: boolean;
    p0_hold_active: boolean;
    idempotency_verified: boolean;
    autonomy_gate: string;
    priority_tier: string;
  };
  steps: Array<{
    step: number;
    title: string;
    detail: string;
    status: string;
  }>;
  actions: Array<{
    action_type: string;
    resource_type: string;
    resource_id: string;
    risk_level: string;
    requires_approval: boolean;
    autonomy_level: string;
    parameters: Record<string, any>;
  }>;
}

export async function fetchEdgeCases(): Promise<{ total: number; edge_cases: EdgeCaseItem[] }> {
  const res = await fetch(`${API_BASE}/simulation/edge-cases`, {
    headers: { ...authHeaders() }
  });
  if (!res.ok) throw new Error("Failed to fetch edge cases catalog");
  return res.json();
}

export async function runEdgeCaseSimulation(code: string): Promise<EdgeCaseSimulationResult> {
  const res = await fetch(`${API_BASE}/simulation/edge-cases/${encodeURIComponent(code)}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Failed to simulate edge case ${code}` }));
    throw new Error(err.detail || `Failed to simulate edge case ${code}`);
  }
  return res.json();
}

export async function fetchGeminiLiveStatus() {
  const res = await fetch(`${API_BASE}/simulation/gemini-status`, {
    headers: { ...authHeaders() }
  });
  if (!res.ok) throw new Error("Failed to fetch Gemini status");
  return res.json();
}

export async function executeLiveGeminiPrompt(prompt: string) {
  const res = await fetch(`${API_BASE}/simulation/gemini-test`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ prompt })
  });
  if (!res.ok) throw new Error("Failed to test live Gemini inference");
  return res.json();
}

// ─── PRODUCT MANAGEMENT APIs (Admin) ─────────────────────────────────────────

export interface AdminProduct {
  product_id: string;
  sku_id: string;
  sku_code: string;
  product_title: string;
  status: 'active' | 'archived' | 'draft';
  price_usd: number;
  cost_usd: number;
  margin_pct: number;
  currency: string;
  weight_grams: number;
  on_hand: number;
  reserved: number;
  net_available: number;
  reorder_point: number;
  daily_velocity: number;
  days_of_cover: number;
  warnings: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface CreateProductPayload {
  title: string;
  sku_code: string;
  price_usd: number;
  cost_usd: number;
  initial_stock: number;
  weight_grams: number;
  category: string;
  daily_velocity: number;
  reorder_point?: number;
  currency?: string;
  status?: string;
}

export async function fetchAdminProducts(params?: {
  status?: string;
  category?: string;
  search?: string;
}): Promise<{ total: number; products: AdminProduct[] }> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.category) query.set('category', params.category);
  if (params?.search) query.set('search', params.search);
  const qs = query.toString() ? `?${query}` : '';
  const res = await fetch(`${API_BASE}/products${qs}`, { headers: { ...authHeaders() } });
  if (!res.ok) throw new Error("Failed to fetch products");
  return res.json();
}

export async function createAdminProduct(payload: CreateProductPayload) {
  const res = await fetch(`${API_BASE}/products`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Failed to create product");
  }
  return data;
}

export async function updateAdminProduct(sku_code: string, payload: {
  title?: string;
  price_usd?: number;
  cost_usd?: number;
  weight_grams?: number;
  daily_velocity?: number;
  reorder_point?: number;
  status?: string;
}) {
  const res = await fetch(`${API_BASE}/products/${encodeURIComponent(sku_code)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to update product");
  return data;
}

export async function adjustAdminStock(sku_code: string, delta: number, reason: string = "Manual admin adjustment") {
  const res = await fetch(`${API_BASE}/products/${encodeURIComponent(sku_code)}/adjust-stock`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ delta, reason })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Stock adjustment failed");
  return data;
}

export async function archiveAdminProduct(sku_code: string) {
  const res = await fetch(`${API_BASE}/products/${encodeURIComponent(sku_code)}`, {
    method: "DELETE",
    headers: { ...authHeaders() }
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to archive product");
  return data;
}
