// ============================================================
// AHS TypeScript Core — Central Types
// ============================================================

/** Agent identities in the hybrid system */
export type AgentId = "hermes" | "openclaw";

/** Task complexity level */
export type Complexity = "simple" | "medium" | "complex" | "research";

/** Task classification result */
export interface TaskClassification {
  agent: AgentId;
  complexity: Complexity;
  confidence: number;     // 0.0 - 1.0
  reason: string;
  requiredSkills: string[];
}

/** A single step in an execution plan */
export interface PlanStep {
  id: string;
  action: string;
  agent: AgentId;
  description: string;
  input?: unknown;
  dependencies: string[];  // step IDs that must complete first
  timeout: number;          // seconds
}

/** Complete execution plan */
export interface ExecutionPlan {
  task: string;
  classification: TaskClassification;
  steps: PlanStep[];
  parallel: boolean;        // can steps run in parallel?
  maxConcurrency: number;   // max parallel agents
  context: Record<string, unknown>;
}

/** Bridge message — unified JSON-RPC 2.0 */
export interface BridgeMessage {
  jsonrpc: "2.0";
  id: string;
  method: string;
  params: Record<string, unknown>;
}

/** Bridge response */
export interface BridgeResponse {
  jsonrpc: "2.0";
  id: string;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/** MCP tool definition */
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

/** Supported transports */
export type TransportType = "stdio" | "websocket" | "http";

/** MCP server configuration */
export interface MCPServerConfig {
  name: string;
  transport: TransportType;
  endpoint?: string;
  command?: string;
  args?: string[];
  tools: string[];           // enabled tool names (empty = all)
}

/** Orchestrator event log entry */
export interface LogEntry {
  timestamp: number;
  agent: AgentId;
  action: string;
  status: "started" | "completed" | "failed";
  duration: number;
  result?: string;
  error?: string;
}

/** Final orchestration result */
export interface OrchestrationResult {
  task: string;
  success: boolean;
  response: string;
  steps: number;
  elapsedMs: number;
  log: LogEntry[];
  error?: string;
}

/** Agent capabilities — what each agent can do */
export const AGENT_CAPABILITIES: Record<AgentId, string[]> = {
  hermes: [
    "deep_reasoning",
    "research",
    "code_review",
    "planning",
    "analysis",
    "multi_skill",
  ],
  openclaw: [
    "fast_execution",
    "file_operations",
    "shell_commands",
    "git_operations",
    "tools_invocation",
    "delegation",
  ],
};
