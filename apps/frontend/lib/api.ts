"use client";

import { api } from "@/lib/api-client";

export const authApi = {
  login: async (email: string, password: string) => {
    const { data } = await api.post("/auth/login", { email, password });
    return data;
  },
  register: async (email: string, password: string, referralCode?: string) => {
    const payload: any = { email, password };
    if (referralCode) payload.referral_code = referralCode;
    const { data } = await api.post("/auth/register", payload);
    return data;
  },
  verifyEmailToken: async (token: string) => {
    const { data } = await api.get(`/auth/verify-email?token=${encodeURIComponent(token)}`);
    return data;
  },
  resendVerificationEmail: async (email: string) => {
    const { data } = await api.post("/auth/resend-verification-email", { email });
    return data;
  },
};

export const agentsApi = {
  list: async () => (await api.get("/agents/")).data,
  get: async (id: number) => (await api.get(`/agents/${id}`)).data,
  create: async (payload: any) => (await api.post("/agents/", payload)).data,
  update: async (id: number, payload: any) => (await api.put(`/agents/${id}`, payload)).data,
  run: async (id: number, input_data?: string) =>
    (await api.post(`/agents/${id}/run`, { input_data })).data,
  versions: async (id: number) => (await api.get(`/agents/${id}/versions`)).data,
  publish: async (id: number, payload: any) =>
    (await api.post(`/marketplace/agents/${id}/publish`, payload)).data,
  clone: async (id: number) => (await api.post(`/agents/${id}/clone`)).data,
};

export const workflowsApi = {
  list: async () => (await api.get("/workflows/")).data,
  create: async (payload: any) => (await api.post("/workflows/", payload)).data,
  run: async (id: number, input: string) =>
    (await api.post(`/workflows/${id}/run`, { input })).data,
};

export const marketplaceApi = {
  listings: async () => (await api.get("/marketplace/listings")).data,
  buy: async (listingId: number) => (await api.post(`/marketplace/listings/${listingId}/buy`)).data,
  install: async (agentId: number) => (await api.post(`/marketplace/${agentId}/install`)).data,
  createListing: async (payload: any) => (await api.post("/marketplace/listings", payload)).data,
  reviews: async (listingId: number) =>
    (await api.get(`/marketplace/listings/${listingId}/reviews`)).data,
  createReview: async (listingId: number, payload: any) =>
    (await api.post(`/marketplace/listings/${listingId}/reviews`, payload)).data,
};

export const executionsApi = {
  list: async () => (await api.get("/executions/")).data,
  byAgent: async (agentId: number) => (await api.get(`/executions/${agentId}`)).data,
};

export const workspacesApi = {
  list: async () => (await api.get("/workspaces/")).data,
  create: async (payload: any) => (await api.post("/workspaces/", payload)).data,
};

export const deploymentApi = {
  templates: async () => (await api.get("/deployment/templates")).data,
  deployTemplate: async (templateId: number) =>
    (await api.post(`/deployment/templates/${templateId}/deploy`)).data,
  submitFeedback: async (payload: { type: string; message?: string; rating?: number }) =>
    (await api.post("/deployment/feedback", payload)).data,
};

export const walletApi = {
  balance: async () => (await api.get("/wallet/balance")).data,
  recharge: async (amount: number) => (await api.post("/wallet/recharge", null, { params: { amount } })).data,
  confirmRecharge: async (chargeId: number) =>
    (await api.post(`/wallet/recharge/${chargeId}/confirm`)).data,
  failRecharge: async (chargeId: number) =>
    (await api.post(`/wallet/recharge/${chargeId}/fail`)).data,
  transactions: async () => (await api.get("/wallet/transactions")).data,
  charges: async () => (await api.get("/wallet/charges")).data,
};

export const billingApi = {
  subscription: async () => (await api.get("/billing/subscription")).data,
  usage: async () => (await api.get("/billing/usage")).data,
};

export const growthApi = {
  referrals: async () => (await api.get("/growth/referrals")).data,
  claim: async (referralId: number) => (await api.post(`/growth/referrals/claim/${referralId}`)).data,
  redeem: async (referralId: number) =>
    (await api.post(`/referral/redeem`, { referral_id: referralId })).data,
  metrics: async () => (await api.get("/growth/metrics")).data,
};

export const complianceApi = {
  scan: async (payload: any) => (await api.post("/compliance/scan", payload)).data,
};

export const shareApi = {
  get: async (runId: number) => (await api.get(`/share/${runId}`)).data,
};

export const innovationApi = {
  list: async () => (await api.get("/innovation/opportunities")).data,
  simulate: async (payload: any) => (await api.post("/innovation/simulations", payload)).data,
};

export const adminApi = {
  users: async () => (await api.get("/admin/users")).data,
  auditLogs: async () => (await api.get("/admin/audit-logs")).data,
};

export const observabilityApi = {
  metrics: async () => (await api.get("/observability/metrics")).data,
  health: async () => (await api.get("/observability/system-health")).data,
  stats: async () => (await api.get("/observability/execution-stats")).data,
};

export const apiKeysApi = {
  list: async () => (await api.get("/auth/api-keys")).data,
  create: async (name: string) => (await api.post("/auth/api-keys", { name })).data,
  revoke: async (id: number) => (await api.delete(`/auth/api-keys/${id}`)).data,
};

export const analyticsApi = {
  founderRuns: async (limit: number = 5) =>
    (await api.get(`/analytics/founder-runs?limit=${limit}`)).data,
  founderRun: async (id: number) => (await api.get(`/analytics/founder-runs/${id}`)).data,
};

export const publicApi = {
  agent: async (id: number) => (await api.get(`/agents/public/${id}`)).data,
  demoAgent: async () => (await api.get(`/agents/public/demo`)).data,
  workflow: async (id: number) => (await api.get(`/workflows/public/${id}`)).data,
  runAgent: async (id: number, input_data?: string) =>
    (await api.post(`/agents/public/${id}/run`, { input_data })).data,
  cloneWorkflow: async (id: number) => (await api.post(`/workflows/${id}/clone`)).data,
  installWorkflow: async (id: number) => (await api.post(`/workflows/${id}/install`)).data,
  systemAgent: async (slug: string) => (await api.get(`/marketplace/public/${slug}`)).data,
  installSystemAgent: async (slug: string) =>
    (await api.post(`/marketplace/public/${slug}/install`)).data,
};

export const templatesApi = {
  list: async () => (await api.get("/templates/agents")).data,
  getBySlug: async (slug: string) => (await api.get(`/templates/agents/by-slug/${slug}`)).data,
  install: async (id: number) => (await api.post(`/templates/agents/${id}/install`)).data,
  submit: async (payload: any) => (await api.post("/templates/agents/submit", payload)).data,
  share: async (id: number) => (await api.post(`/templates/agents/${id}/share`)).data,
};

// Backward-compatible exports for legacy pages
export const getAgents = agentsApi.list;
export const getAgent = agentsApi.get;
export const createAgent = async (name: string, description?: string, config?: any) =>
  agentsApi.create({ name, description, config });
export const updateAgent = agentsApi.update;
export const runAgent = async (id: number, input: string) => agentsApi.run(id, input);

export const getExecutions = async (agentId?: number) =>
  agentId ? executionsApi.byAgent(agentId) : executionsApi.list();

export const getWorkflows = workflowsApi.list;
export const createWorkflow = async (name: string, config: any) =>
  workflowsApi.create({ name, config_json: config });
export const runWorkflow = workflowsApi.run;

export const getProjectTemplates = deploymentApi.templates;
export const deployTemplate = deploymentApi.deployTemplate;
export const submitFeedback = async (type: string, message?: string, rating?: number) =>
  deploymentApi.submitFeedback({ type, message, rating });

export const getMarketplaceAgents = async (search?: string, tag?: string, category?: string) => {
  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (tag) params.append("tag", tag);
  if (category) params.append("category", category);
  const suffix = params.toString();
  return api.get(`/marketplace/listings${suffix ? `?${suffix}` : ""}`).then((res) => res.data);
};
export const buyListing = marketplaceApi.buy;
export const installAgent = marketplaceApi.install;
export const createListing = marketplaceApi.createListing;

export const getAgentReviews = (agentId: number) =>
  api.get(`/marketplace/agents/${agentId}/reviews`).then((res) => res.data);
export const createReview = (agentId: number, rating: number, comment: string) =>
  api.post(`/marketplace/agents/${agentId}/reviews`, { rating, comment }).then((res) => res.data);

export const getAgentVersions = agentsApi.versions;
export const createAgentVersion = (agentId: number, version: string, description: string) =>
  api.post(`/agents/${agentId}/versions`, { version, description }).then((res) => res.data);
export const rollbackAgentVersion = (agentId: number, versionId: number) =>
  api.post(`/agents/${agentId}/rollback/${versionId}`).then((res) => res.data);
export const publishAgent = agentsApi.publish;

export const getSchedules = () => api.get("/schedules/").then((res) => res.data);
export const createSchedule = (agentId: number, cron: string, input: string) =>
  api
    .post("/schedules/", { agent_id: agentId, cron_expression: cron, input_payload: input })
    .then((res) => res.data);
export const deleteSchedule = (scheduleId: number) =>
  api.delete(`/schedules/${scheduleId}`).then((res) => res.data);

export const getDashboardStats = () => api.get("/intelligence/dashboard").then((res) => res.data);
export const getReflections = (agentId?: number, flaggedOnly?: boolean) => {
  const params = new URLSearchParams();
  if (agentId) params.append("agent_id", agentId.toString());
  if (flaggedOnly) params.append("flagged_only", "true");
  return api.get(`/intelligence/reflections?${params.toString()}`).then((res) => res.data);
};
export const getEvolutions = () => api.get("/intelligence/evolutions").then((res) => res.data);
export const applyEvolution = (evoId: number) =>
  api.post(`/intelligence/evolutions/${evoId}/apply`).then((res) => res.data);
export const getMe = () => api.get("/auth/me").then((res) => res.data);
export const getWorkflow = (id: number) => api.get(`/workflows/${id}`).then((res) => res.data);
export const getHealthStatus = () => api.get("/health").then((res) => res.data);
