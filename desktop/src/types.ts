export interface Block {
  type: string;
  text?: string;
  thinking?: string;
  name?: string;
  id?: string;
  arguments?: Record<string, unknown>;
}
export interface Message {
  role: string;
  content?: Block[] | string;
  timestamp?: number;
  toolName?: string;
  toolCallId?: string;
  isError?: boolean;
  errorMessage?: string;
}
export interface Model {
  id: string;
  name?: string;
  provider: string;
  contextWindow?: number;
  reasoning?: boolean;
}
export interface Resource {
  name: string;
  path: string;
  description?: string;
}
export interface Entry {
  name: string;
  path: string;
  directory: boolean;
}
export interface FileData {
  path: string;
  text: string;
  revision: string;
}
export interface Session {
  id: string;
  title: string | null;
  updatedAt: number;
}
export interface Stats {
  tokens?: { input: number; output: number; total: number };
  toolCalls?: number;
  cost?: number;
  contextUsage?: { tokens: number; contextWindow: number; percent: number };
}
export interface State {
  model: Model;
  thinkingLevel: string;
  isStreaming: boolean;
  sessionId: string;
  sessionName: string | null;
}
export interface Info {
  cwd: string;
  connected: boolean;
  tools: string[];
  skills: Resource[];
  prompts: Resource[];
  context: string[];
  sessions: Session[];
}
export interface Snapshot {
  root: string;
  name: string;
  state: State;
  info: Info;
  messages: Message[];
  models: Model[];
  stats: Stats;
  levels: string[];
  files: Entry[];
}
export interface Event {
  type: string;
  message?: Message;
  toolCallId?: string;
  toolName?: string;
  args?: Record<string, unknown>;
  partialResult?: { content: Block[] };
  result?: { content: Block[] };
  isError?: boolean;
  error?: string;
  text?: string;
  name?: string;
}
export interface DesktopApi {
  bootstrap(): Promise<Snapshot>;
  openWorkspace(): Promise<Snapshot | null>;
  listFiles(path: string): Promise<Entry[]>;
  readFile(path: string): Promise<FileData>;
  saveFile(path: string, text: string, revision: string): Promise<FileData>;
  gitStatus(): Promise<{ output: string; error: string }>;
  gitDiff(): Promise<{ output: string; error: string }>;
  rpc<T = unknown>(type: string, fields?: Record<string, unknown>): Promise<T>;
  login(provider: string, key: string): Promise<void>;
  trustWorkspace(): Promise<Snapshot>;
  windowControl(action: string): Promise<void>;
  onEvent(callback: (event: Event) => void): () => void;
}
declare global {
  interface Window {
    je?: DesktopApi;
  }
}
