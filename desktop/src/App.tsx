import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  ArrowUp,
  ArrowRight,
  ArrowLeft,
  FolderOpen,
  Folder,
  File,
  Files,
  GitBranch,
  MessageSquare,
  Plus,
  Search,
  Settings,
  PanelRight,
  PanelBottom,
  PanelLeft,
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  X,
  Minus,
  Square,
  Terminal,
  Check,
  CheckCheck,
  Code2,
  ShieldCheck,
  Shield,
  RefreshCw,
  LoaderCircle,
  Command,
  Paperclip,
  Sparkles,
  Workflow,
  BookOpen,
  Braces,
  Save,
  SplitSquareHorizontal,
  Clock,
  Plug,
  Zap,
  CornerDownLeft,
  StopCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, native } from "./api";
import { updateTools, toolsFromMessages } from "./events";
import type { Tool } from "./events";
const Editor = lazy(() =>
  import("./Editor").then((module) => ({ default: module.Editor })),
);
import type {
  Snapshot,
  Message,
  FileData,
  Entry,
  Event,
  Stats,
  State,
  Info,
  Model,
} from "./types";

type OpenFile = FileData & { saved: string };
const errorText = (error: unknown) =>
  error instanceof Error ? error.message : String(error);
const messageText = (message: Message) =>
  typeof message.content === "string"
    ? message.content
    : (message.content ?? [])
        .filter((b) => b.type === "text")
        .map((b) => b.text ?? "")
        .join("");
function IconButton({
  label,
  children,
  onClick,
  active = false,
  disabled = false,
}: {
  label: string;
  children: ReactNode;
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className={`icon-button ${active ? "active" : ""}`}
      aria-label={label}
      title={label}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
function FileTree({
  entries,
  onOpen,
  level = 0,
}: {
  entries: Entry[];
  onOpen: (path: string) => void;
  level?: number;
}) {
  const [expanded, setExpanded] = useState<Record<string, Entry[]>>({});
  async function toggle(entry: Entry) {
    if (expanded[entry.path])
      setExpanded((s) => {
        const n = { ...s };
        delete n[entry.path];
        return n;
      });
    else setExpanded((s) => ({ ...s, [entry.path]: [] }));
    try {
      if (!expanded[entry.path]) {
        const items = await api.listFiles(entry.path);
        setExpanded((s) => ({ ...s, [entry.path]: items }));
      }
    } catch (error) {
      alert(errorText(error));
    }
  }
  return (
    <div className="file-tree">
      {entries.map((entry) => (
        <div key={entry.path}>
          <button
            className="tree-row"
            style={{ paddingLeft: 12 + level * 15 }}
            onClick={() =>
              entry.directory ? void toggle(entry) : onOpen(entry.path)
            }
          >
            {entry.directory ? (
              expanded[entry.path] ? (
                <ChevronDown size={12} />
              ) : (
                <ChevronRight size={12} />
              )
            ) : (
              <span className="tree-spacer" />
            )}
            {entry.directory ? <Folder size={15} /> : <File size={14} />}
            <span>{entry.name}</span>
          </button>
          {expanded[entry.path] && (
            <FileTree
              entries={expanded[entry.path]}
              onOpen={onOpen}
              level={level + 1}
            />
          )}
        </div>
      ))}
    </div>
  );
}
export function App() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null),
    [state, setState] = useState<State | null>(null),
    [info, setInfo] = useState<Info | null>(null),
    [stats, setStats] = useState<Stats>({});
  const [messages, setMessages] = useState<Message[]>([]),
    [tools, setTools] = useState<Tool[]>([]),
    [running, setRunning] = useState(false),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [nav, setNav] = useState<"sessions" | "files" | "git">("sessions"),
    [sidebar, setSidebar] = useState(true),
    [inspector, setInspector] = useState(true),
    [terminal, setTerminal] = useState(false);
  const [input, setInput] = useState(""),
    [files, setFiles] = useState<OpenFile[]>([]),
    [tab, setTab] = useState("agent"),
    [split, setSplit] = useState(false),
    [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});
  const [dialog, setDialog] = useState<
      "models" | "settings" | "search" | "trust" | null
    >(null),
    [search, setSearch] = useState(""),
    [provider, setProvider] = useState("deepseek"),
    [key, setKey] = useState("");
  const [shell, setShell] = useState(""),
    [output, setOutput] = useState(""),
    [shellBusy, setShellBusy] = useState(false),
    [git, setGit] = useState(""),
    [trusted, setTrusted] = useState(false);
  const draft = useRef<HTMLTextAreaElement>(null),
    stream = useRef<HTMLDivElement>(null),
    runningRef = useRef(false),
    fileRef = useRef(files);
  fileRef.current = files;
  const apply = useCallback((data: Snapshot) => {
    setSnapshot(data);
    setState(data.state);
    setInfo(data.info);
    setStats(data.stats);
    setMessages(data.messages);
    setTools(toolsFromMessages(data.messages));
    setRunning(data.state.isStreaming);
    runningRef.current = data.state.isStreaming;
    setLoading(false);
  }, []);
  const refresh = useCallback(async () => {
    const [nextState, nextInfo, nextStats] = await Promise.all([
      api.rpc<State>("get_state"),
      api.rpc<Info>("desktop_info"),
      api.rpc<Stats>("get_session_stats"),
    ]);
    setState(nextState);
    setInfo(nextInfo);
    setStats(nextStats);
  }, []);
  const receive = useCallback(
    (event: Event) => {
      if (event.type === "agent_start") {
        runningRef.current = true;
        setRunning(true);
      }
      if (
        ["message_start", "message_update", "message_end"].includes(
          event.type,
        ) &&
        event.message
      ) {
        const m = event.message;
        setMessages((current) => {
          const last = current[current.length - 1];
          if (
            event.type !== "message_start" &&
            last &&
            last.role === m.role &&
            last.timestamp === m.timestamp
          )
            return [...current.slice(0, -1), m];
          if (
            event.type === "message_start" ||
            !last ||
            last.timestamp !== m.timestamp
          )
            return [...current, m];
          return current;
        });
      }
      if (event.type.startsWith("tool_execution_"))
        setTools((t) => updateTools(t, event));
      if (event.type === "agent_settled") {
        runningRef.current = false;
        setRunning(false);
        void refresh().catch((e) => setError(errorText(e)));
        void api
          .rpc<{ messages: Message[] }>("get_messages")
          .then((data) => setMessages(data.messages));
      }
      if (event.type === "session_info_changed")
        setState((s) =>
          s ? { ...s, sessionName: event.name ?? s.sessionName } : s,
        );
      if (event.type === "rpc_error") {
        setError(event.error ?? "模型运行失败");
        setRunning(false);
        runningRef.current = false;
      }
      if (event.type === "desktop_disconnected") {
        setError(event.error ?? "JE 后端连接已断开");
        setRunning(false);
        runningRef.current = false;
      }
      if (event.type === "desktop_diagnostic")
        setOutput((s) => (s + event.text).slice(-100000));
    },
    [refresh],
  );
  useEffect(() => {
    const off = api.onEvent(receive);
    void api
      .bootstrap()
      .then(apply)
      .catch((e) => {
        setError(errorText(e));
        setLoading(false);
      });
    return off;
  }, [apply, receive]);
  useEffect(() => {
    stream.current?.scrollTo({
      top: stream.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, tools]);
  const currentFile =
    files.find((f) => f.path === tab) ?? files[files.length - 1];
  async function guard(action: () => Promise<void>) {
    setError("");
    try {
      await action();
    } catch (e) {
      setError(errorText(e));
    }
  }
  async function openFile(path: string) {
    await guard(async () => {
      const existing = fileRef.current.find((f) => f.path === path);
      if (!existing) {
        const data = await api.readFile(path);
        setFiles((f) => [...f, { ...data, saved: data.text }]);
      }
      setTab(path);
    });
  }
  async function saveFile() {
    if (!currentFile) return;
    await guard(async () => {
      const data = await api.saveFile(
        currentFile.path,
        currentFile.text,
        currentFile.revision,
      );
      setFiles((f) =>
        f.map((item) =>
          item.path === data.path ? { ...data, saved: data.text } : item,
        ),
      );
    });
  }
  async function openWorkspace() {
    if (running || shellBusy) return;
    if (
      files.some((f) => f.text !== f.saved) &&
      !confirm("未保存的文件将关闭，继续打开新项目吗？")
    )
      return;
    await guard(async () => {
      const data = await api.openWorkspace();
      if (data) {
        apply(data);
        setFiles([]);
        setTab("agent");
        setTools([]);
        setTrusted(false);
        setGit("");
        setOutput("");
      }
    });
  }
  async function sessionCommand(
    type: string,
    fields?: Record<string, unknown>,
  ) {
    if (running || shellBusy) return;
    await guard(async () => {
      await api.rpc(type, fields);
      const data = await api.bootstrap();
      apply(data);
      setTab("agent");
    });
  }
  async function send() {
    const text = input.trim();
    if (!text || running || loading) return;
    setInput("");
    setError("");
    setTab("agent");
    setRunning(true);
    runningRef.current = true;
    try {
      await api.rpc("prompt", { message: text });
    } catch (e) {
      setError(errorText(e));
      setRunning(false);
      runningRef.current = false;
      setInput(text);
    }
  }
  useEffect(() => {
    function keys(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearch("");
        setDialog("search");
      }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void saveFile();
      }
      if (e.key === "Escape") {
        if (dialog) setDialog(null);
        else if (runningRef.current) void api.rpc("abort");
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "`") {
        e.preventDefault();
        setTerminal((s) => !s);
      }
    }
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  }, [currentFile, dialog]);
  const model = state?.model;
  const modelName = model?.id ?? "未连接";
  const activeModels = (snapshot?.models ?? [])
    .filter((m) =>
      `${m.provider} ${m.id}`.toLowerCase().includes(search.toLowerCase()),
    )
    .slice(0, 100);
  const chat = (
    <section className="chat">
      <header className="chat-header">
        <div>
          <span className="eyebrow">YOUR CODING WORKSPACE</span>
          <h2>
            {state?.sessionName ?? "新的对话"}
            <span className="session-dot" />
          </h2>
        </div>
        <div className="chat-header-actions">
          <span className="quiet-badge">
            <span className={running ? "pulse dot" : "dot"} />
            {running ? "Agent 正在工作" : "准备就绪"}
          </span>
          <IconButton
            label="新建会话"
            onClick={() => void sessionCommand("new_session")}
            disabled={running}
          >
            <Plus size={17} />
          </IconButton>
        </div>
      </header>
      <div className="conversation" ref={stream}>
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome-mark">
              JE<span>↗</span>
            </div>
            <span className="eyebrow">
              A LITTLE LESS FRICTION. A LOT MORE FLOW.
            </span>
            <h1>
              从一个想法，
              <br />
              <span>开始构建。</span>
            </h1>
            <p>
              理解你的项目，连接模型与工具。
              <br />
              把思考、执行和每一步变化放在同一个工作空间。
            </p>
            <div className="suggestions">
              {[
                {
                  icon: <Code2 size={17} />,
                  title: "理解这个项目",
                  text: "阅读项目，解释架构与主要入口。",
                },
                {
                  icon: <GitBranch size={17} />,
                  title: "检查代码更改",
                  text: "检查当前 Git 更改，指出可能的问题。",
                },
                {
                  icon: <CheckCheck size={17} />,
                  title: "补充测试",
                  text: "检查核心模块，建议需要补充的测试。",
                },
              ].map((item) => (
                <button
                  key={item.title}
                  onClick={() => {
                    setInput(item.text);
                    draft.current?.focus();
                  }}
                >
                  {item.icon}
                  <strong>{item.title}</strong>
                  <ArrowUp size={13} />
                </button>
              ))}
            </div>
            <div className="welcome-foot">
              <ShieldCheck size={13} /> 会话保存在本机 <span>·</span>{" "}
              可检查的工具执行 <span>·</span> 多模型支持
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages
              .filter((m) => m.role !== "toolResult")
              .map((message, i) => (
                <article
                  className={`message ${message.role}`}
                  key={`${message.timestamp}-${i}`}
                >
                  <div className="message-label">
                    {message.role === "user" ? (
                      <>
                        <span className="avatar user-avatar">Y</span>你
                      </>
                    ) : (
                      <>
                        <span className="avatar">JE</span>JE{" "}
                        <span className="message-model">{modelName}</span>
                      </>
                    )}
                  </div>
                  {message.errorMessage ? (
                    <div className="message-error">{message.errorMessage}</div>
                  ) : (
                    <ReactMarkdown skipHtml>
                      {messageText(message)}
                    </ReactMarkdown>
                  )}
                  {typeof message.content !== "string" &&
                    message.content?.some((b) => b.type === "thinking") && (
                      <details className="thinking">
                        <summary>思考过程</summary>
                        <p>
                          {message.content
                            .filter((b) => b.type === "thinking")
                            .map((b) => b.thinking)
                            .join("")}
                        </p>
                      </details>
                    )}
                  {typeof message.content !== "string" &&
                    message.content
                      ?.filter((b) => b.type === "toolCall")
                      .map((block) => (
                        <div className="inline-tool" key={block.id}>
                          <Workflow size={14} />
                          <span>{block.name}</span>
                          <code>{JSON.stringify(block.arguments)}</code>
                        </div>
                      ))}
                </article>
              ))}
            {running && (
              <div className="working">
                <LoaderCircle size={14} className="spin" /> JE 正在思考与执行…
              </div>
            )}
          </div>
        )}
      </div>
      <div className="composer-wrap">
        {info && !info.connected && (
          <div className="connect-notice">
            <Plug size={14} /> 连接一个模型，开始你的第一个任务
            <button onClick={() => setDialog("settings")}>
              连接模型 <ArrowRight size={13} />
            </button>
          </div>
        )}
        <div className="composer">
          <textarea
            ref={draft}
            aria-label="发送给 JE 的任务"
            placeholder="描述你想构建什么，或输入 /skill:name 使用技能…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !e.nativeEvent.isComposing
              ) {
                e.preventDefault();
                void send();
              }
            }}
          />
          <div className="composer-controls">
            <div>
              <IconButton
                label="添加当前文件到任务"
                disabled={!currentFile}
                onClick={() =>
                  setInput((s) => s + `\n请查看文件 ${currentFile?.path}`)
                }
              >
                <Paperclip size={17} />
              </IconButton>
              <button className="mode-chip" onClick={() => setDialog("trust")}>
                <Shield size={13} />
                {trusted ? "项目上下文已启用" : "项目上下文受保护"}
              </button>
            </div>
            <div>
              <button
                className="model-chip"
                onClick={() => {
                  setSearch("");
                  setDialog("models");
                }}
              >
                {modelName}
                <ChevronDown size={12} />
              </button>
              {running ? (
                <button
                  className="send stop"
                  aria-label="停止任务"
                  onClick={() =>
                    void guard(async () => {
                      await api.rpc("abort");
                    })
                  }
                >
                  <Square size={14} />
                </button>
              ) : (
                <button
                  className="send"
                  aria-label="发送任务"
                  disabled={!input.trim() || loading}
                  onClick={() => void send()}
                >
                  <ArrowUp size={18} />
                </button>
              )}
            </div>
          </div>
        </div>
        <div className="composer-hint">
          <span>
            <CornerDownLeft size={11} /> Enter 发送 <span>·</span> Shift + Enter
            换行
          </span>
          <span>本地工作空间 / JE Agent</span>
        </div>
      </div>
    </section>
  );
  const editorView = currentFile ? (
    <section className="editor-pane">
      <div className="editor-path">
        <Code2 size={13} />
        <span>{currentFile.path}</span>
        {currentFile.text !== currentFile.saved && (
          <span className="dirty-dot" />
        )}
        <button onClick={() => void saveFile()}>
          <Save size={13} /> 保存
        </button>
      </div>
      <Suspense fallback={<div className="loading">正在加载编辑器…</div>}>
        <Editor
          path={currentFile.path}
          text={currentFile.text}
          onChange={(text) =>
            setFiles((f) =>
              f.map((item) =>
                item.path === currentFile.path ? { ...item, text } : item,
              ),
            )
          }
          onSave={() => void saveFile()}
        />
      </Suspense>
    </section>
  ) : (
    <div className="editor-empty">
      <Files size={30} />
      <p>从文件栏打开一个文件</p>
      <button onClick={() => setNav("files")}>浏览项目文件</button>
    </div>
  );
  return (
    <div className="app">
      <header className="titlebar">
        <div className="title-left">
          <span className="brand-small">
            JE<span>/</span>
          </span>
          <button onClick={() => void openWorkspace()}>文件</button>
          <button
            onClick={() => {
              setSearch("");
              setDialog("search");
            }}
          >
            转到
          </button>
          <button onClick={() => setTerminal((s) => !s)}>终端</button>
        </div>
        <button
          className="command-bar"
          onClick={() => {
            setSearch("");
            setDialog("search");
          }}
        >
          <Search size={13} />
          <span>
            {snapshot?.name ?? "JE Workspace"}{" "}
            <span className="command-caption">— 搜索文件、会话与命令</span>
          </span>
          <kbd>Ctrl K</kbd>
        </button>
        <div className="window-controls">
          <IconButton
            label="最小化"
            onClick={() => void api.windowControl("minimize")}
          >
            <Minus size={15} />
          </IconButton>
          <IconButton
            label="最大化"
            onClick={() => void api.windowControl("maximize")}
          >
            <Square size={12} />
          </IconButton>
          <IconButton
            label="关闭窗口"
            onClick={() => void api.windowControl("close")}
          >
            <X size={16} />
          </IconButton>
        </div>
      </header>
      <div className="workbench">
        <nav className="activity-bar">
          <div>
            <IconButton
              label="会话"
              active={nav === "sessions" && sidebar}
              onClick={() => {
                setNav("sessions");
                setSidebar(true);
              }}
            >
              <MessageSquare size={21} />
            </IconButton>
            <IconButton
              label="文件浏览器"
              active={nav === "files" && sidebar}
              onClick={() => {
                setNav("files");
                setSidebar(true);
              }}
            >
              <Files size={21} />
            </IconButton>
            <IconButton
              label="Git 更改"
              active={nav === "git" && sidebar}
              onClick={() => {
                setNav("git");
                setSidebar(true);
                void api.gitStatus().then((r) => setGit(r.output || r.error));
              }}
            >
              <GitBranch size={21} />
            </IconButton>
            <span className="rail-rule" />
            <IconButton
              label="技能与工具"
              active={inspector}
              onClick={() => setInspector((s) => !s)}
            >
              <Workflow size={21} />
            </IconButton>
          </div>
          <div>
            <IconButton
              label="切换终端面板"
              active={terminal}
              onClick={() => setTerminal((s) => !s)}
            >
              <Terminal size={21} />
            </IconButton>
            <IconButton label="模型设置" onClick={() => setDialog("settings")}>
              <Settings size={21} />
            </IconButton>
            <span className="profile">J</span>
          </div>
        </nav>
        {sidebar && (
          <aside className="sidebar">
            <div className="sidebar-title">
              <span>
                {nav === "sessions"
                  ? "工作空间"
                  : nav === "files"
                    ? "资源管理器"
                    : "源代码管理"}
              </span>
              <IconButton
                label="打开项目目录"
                onClick={() => void openWorkspace()}
                disabled={running}
              >
                <FolderOpen size={16} />
              </IconButton>
            </div>
            <button
              className="project-card"
              onClick={() => void openWorkspace()}
              disabled={running}
            >
              <span className="project-icon">
                <FolderOpen size={18} />
              </span>
              <span>
                <strong>{snapshot?.name ?? "JE"}</strong>
                <small>{snapshot?.root ?? "正在连接工作空间"}</small>
              </span>
              <ChevronDown size={13} />
            </button>
            {nav === "sessions" ? (
              <>
                <button
                  className="new-session"
                  disabled={running}
                  onClick={() => void sessionCommand("new_session")}
                >
                  <Plus size={16} /> 新建对话 <kbd>+</kbd>
                </button>
                <div className="section-label">
                  当前项目 <span>{info?.sessions.length ?? 0}</span>
                </div>
                <button
                  className="session-row selected"
                  onClick={() => setTab("agent")}
                >
                  <MessageSquare size={14} />
                  <span>{state?.sessionName ?? "新的对话"}</span>
                  {running ? (
                    <LoaderCircle className="spin" size={12} />
                  ) : (
                    <span className="tiny-dot" />
                  )}
                </button>
                <div className="session-list">
                  {info?.sessions
                    .filter((s) => s.id !== state?.sessionId)
                    .map((session) => (
                      <button
                        className="session-row"
                        key={session.id}
                        disabled={running}
                        onClick={() =>
                          void sessionCommand("switch_session", {
                            sessionId: session.id,
                          })
                        }
                      >
                        <MessageSquare size={14} />
                        <span>{session.title ?? "未命名会话"}</span>
                      </button>
                    ))}
                </div>
                <div className="sidebar-note">
                  <Clock size={14} />
                  <p>
                    随时继续你的思路<small>历史会话与终端版 JE 共享</small>
                  </p>
                </div>
              </>
            ) : nav === "files" ? (
              <>
                <div className="section-label">
                  {snapshot?.name.toUpperCase()}
                  <button
                    aria-label="刷新文件"
                    onClick={() =>
                      void guard(async () => {
                        const entries = await api.listFiles("");
                        setSnapshot((s) => (s ? { ...s, files: entries } : s));
                      })
                    }
                  >
                    <RefreshCw size={12} />
                  </button>
                </div>
                <FileTree
                  entries={snapshot?.files ?? []}
                  onOpen={(path) => void openFile(path)}
                />
              </>
            ) : (
              <>
                <div className="section-label">工作区更改</div>
                <pre className="git-status">
                  {git || "工作区没有未提交的更改"}
                </pre>
                <button
                  className="text-button"
                  onClick={() =>
                    void guard(async () => {
                      const result = await api.gitDiff();
                      setOutput(
                        result.output || result.error || "没有已追踪文件的差异",
                      );
                      setTerminal(true);
                    })
                  }
                >
                  <GitBranch size={14} /> 查看 diff
                </button>
              </>
            )}
            <div className="sidebar-bottom">
              <span className="dot" />
              本地项目<span>JE 0.1.0</span>
            </div>
          </aside>
        )}
        <main className="main">
          <div className="workspace-tabs">
            <button
              className={`tab ${tab === "agent" ? "selected" : ""}`}
              onClick={() => setTab("agent")}
            >
              <Sparkles size={14} /> JE Agent
            </button>
            {files.map((file) => (
              <button
                key={file.path}
                className={`tab ${tab === file.path ? "selected" : ""}`}
                onClick={() => setTab(file.path)}
              >
                <File size={13} />
                {file.path.split("/").pop()}
                {file.text !== file.saved ? (
                  <span className="dirty-dot" />
                ) : (
                  <X
                    size={12}
                    onClick={(e) => {
                      e.stopPropagation();
                      setFiles((f) =>
                        f.filter((item) => item.path !== file.path),
                      );
                      if (tab === file.path) setTab("agent");
                    }}
                  />
                )}
              </button>
            ))}
            <div className="tab-tools">
              <IconButton
                label="切换左侧栏"
                active={sidebar}
                onClick={() => setSidebar((s) => !s)}
              >
                <PanelLeft size={15} />
              </IconButton>
              <IconButton
                label="分栏显示聊天与代码"
                active={split}
                onClick={() => setSplit((s) => !s)}
              >
                <SplitSquareHorizontal size={15} />
              </IconButton>
              <IconButton
                label="切换终端"
                active={terminal}
                onClick={() => setTerminal((s) => !s)}
              >
                <PanelBottom size={15} />
              </IconButton>
              <IconButton
                label="切换资源侧栏"
                active={inspector}
                onClick={() => setInspector((s) => !s)}
              >
                <PanelRight size={15} />
              </IconButton>
            </div>
          </div>
          {error && (
            <div className="error-banner">
              <span>{error}</span>
              <button aria-label="关闭错误提示" onClick={() => setError("")}>
                <X size={13} />
              </button>
            </div>
          )}
          {loading ? (
            <div className="loading">
              <LoaderCircle className="spin" size={23} /> 正在连接 JE 引擎…
            </div>
          ) : (
            <div className={`center ${split ? "split" : ""}`}>
              {split ? (
                <>
                  {chat}
                  {editorView}
                </>
              ) : tab === "agent" ? (
                chat
              ) : (
                editorView
              )}
            </div>
          )}
          {terminal && (
            <section className="terminal-pane">
              <header>
                <span>
                  <Terminal size={13} /> 终端输出
                </span>
                <span className="terminal-note">单次命令 · 项目目录</span>
                <IconButton label="清空终端输出" onClick={() => setOutput("")}>
                  <RefreshCw size={12} />
                </IconButton>
                <IconButton
                  label="关闭终端面板"
                  onClick={() => setTerminal(false)}
                >
                  <X size={14} />
                </IconButton>
              </header>
              <pre>
                {output ||
                  "在当前项目目录中执行命令。输出由 JE 的终端工具返回。"}
              </pre>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!shell.trim() || shellBusy || running) return;
                  setShellBusy(true);
                  const cmd = shell;
                  setShell("");
                  setOutput((s) => s + `\n$ ${cmd}\n`);
                  void api
                    .rpc<{ output: string; exitCode: number }>("bash", {
                      command: cmd,
                      excludeFromContext: true,
                    })
                    .then((result) =>
                      setOutput((s) =>
                        (
                          s +
                          result.output +
                          `\n[exit ${result.exitCode}]\n`
                        ).slice(-100000),
                      ),
                    )
                    .catch((e) => setOutput((s) => s + errorText(e)))
                    .finally(() => setShellBusy(false));
                }}
              >
                <ChevronRight size={13} />
                <input
                  aria-label="终端命令"
                  placeholder={
                    shellBusy ? "命令执行中…" : "输入命令，按 Enter 执行"
                  }
                  value={shell}
                  onChange={(e) => setShell(e.target.value)}
                  disabled={shellBusy || running}
                />
                <button disabled={shellBusy || running}>
                  {shellBusy ? (
                    <LoaderCircle className="spin" size={13} />
                  ) : (
                    <CornerDownLeft size={13} />
                  )}
                </button>
              </form>
            </section>
          )}
        </main>
        {inspector && (
          <aside className="inspector">
            <header>
              <span>AGENT CONTEXT</span>
              <IconButton
                label="重新加载资源"
                onClick={() =>
                  void guard(async () => {
                    await api.rpc("desktop_reload");
                    await refresh();
                  })
                }
                disabled={running}
              >
                <RefreshCw size={14} />
              </IconButton>
            </header>
            <div className="inspector-scroll">
              <section className="runtime-card">
                <div>
                  <span className={running ? "dot pulse" : "dot"} />
                  <strong>{running ? "正在执行" : "工作空间已就绪"}</strong>
                  <Zap size={14} />
                </div>
                <p>每一步，都可以检查。</p>
                <div className="runtime-numbers">
                  <span>
                    <strong>
                      {messages.filter((m) => m.role === "user").length}
                    </strong>
                    对话轮次
                  </span>
                  <span>
                    <strong>{stats.toolCalls ?? 0}</strong>工具调用
                  </span>
                </div>
              </section>
              <section className="resource-section">
                <h3>
                  <Workflow size={14} /> Tools
                  <span>{info?.tools.length ?? 0}</span>
                </h3>
                <div className="tool-tags">
                  {info?.tools.map((tool) => (
                    <span key={tool}>
                      <span className="tiny-dot" />
                      {tool}
                    </span>
                  ))}
                </div>
              </section>
              <section className="resource-section">
                <h3>
                  <Sparkles size={14} /> Skills
                  <span>{info?.skills.length ?? 0}</span>
                </h3>
                {info?.skills.length ? (
                  info.skills.map((skill) => (
                    <button
                      className="resource"
                      key={skill.name}
                      title={skill.description}
                      onClick={() => {
                        setInput((s) => s + `/skill:${skill.name} `);
                        draft.current?.focus();
                      }}
                    >
                      <span>{skill.name}</span>
                      <ArrowUp size={12} />
                    </button>
                  ))
                ) : (
                  <div className="empty-resource">
                    让 JE 拥有你的工作方法<code>.je/skills/*/SKILL.md</code>
                  </div>
                )}
              </section>
              <section className="resource-section">
                <h3>
                  <BookOpen size={14} /> Prompts
                  <span>{info?.prompts.length ?? 0}</span>
                </h3>
                {info?.prompts.length ? (
                  info.prompts.map((prompt) => (
                    <button
                      className="resource"
                      key={prompt.name}
                      onClick={() => setInput("/" + prompt.name + " ")}
                    >
                      {prompt.name}
                      <ArrowUp size={12} />
                    </button>
                  ))
                ) : (
                  <div className="empty-resource">
                    复用常用任务与指令<code>.je/prompts/*.md</code>
                  </div>
                )}
              </section>
              <section className="resource-section">
                <h3>
                  <Braces size={14} /> Context
                  <span>{info?.context.length ?? 0}</span>
                </h3>
                {info?.context.length ? (
                  info.context.map((file) => (
                    <div className="context-file" key={file}>
                      <File size={12} />
                      {file.split(/[\\/]/).pop()}
                    </div>
                  ))
                ) : (
                  <div className="empty-resource">
                    {trusted ? "没有发现上下文文件" : "项目指令尚未授权加载"}
                    <button
                      className="text-button"
                      onClick={() => setDialog("trust")}
                    >
                      管理项目上下文 <ArrowRight size={12} />
                    </button>
                  </div>
                )}
              </section>
              <section className="resource-section">
                <h3>
                  <Code2 size={14} /> 执行轨迹<span>{tools.length}</span>
                </h3>
                {tools.length ? (
                  tools.map((tool) => (
                    <div className="trace" key={tool.id}>
                      <button
                        onClick={() =>
                          setExpandedTools((s) => ({
                            ...s,
                            [tool.id]: !s[tool.id],
                          }))
                        }
                      >
                        {tool.status === "running" ? (
                          <LoaderCircle size={12} className="spin" />
                        ) : tool.status === "error" ? (
                          <X size={12} />
                        ) : (
                          <Check size={12} />
                        )}
                        <strong>{tool.name}</strong>
                        <ChevronDown size={12} />
                      </button>
                      {expandedTools[tool.id] && (
                        <pre>
                          {JSON.stringify(tool.args, null, 2)}
                          {"\n"}
                          {tool.output || "等待工具返回…"}
                        </pre>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="empty-resource">
                    工具执行后在这里查看过程与结果
                  </div>
                )}
              </section>
              <section className="resource-section usage">
                <h3>
                  Usage<span>本次会话</span>
                </h3>
                <div>
                  <span>输入 / 输出</span>
                  <strong>
                    {(stats.tokens?.input ?? 0).toLocaleString()} /{" "}
                    {(stats.tokens?.output ?? 0).toLocaleString()}
                  </strong>
                </div>
                <div>
                  <span>上下文</span>
                  <strong>{stats.contextUsage?.percent ?? 0}%</strong>
                </div>
                <div className="usage-meter">
                  <span
                    style={{
                      width: `${Math.min(stats.contextUsage?.percent ?? 0, 100)}%`,
                    }}
                  />
                </div>
                <button
                  className="text-button"
                  disabled={running}
                  onClick={() =>
                    void guard(async () => {
                      await api.rpc("compact");
                      apply(await api.bootstrap());
                    })
                  }
                >
                  压缩上下文 <ArrowRight size={12} />
                </button>
              </section>
            </div>
            <footer>
              <span className="brand-small">
                JE<span>/</span>
              </span>
              <span>THINK. BUILD. CONTINUE.</span>
            </footer>
          </aside>
        )}
      </div>
      <footer className="statusbar">
        <div>
          <span className={running ? "dot pulse" : "dot"} />
          {loading ? "连接中" : running ? "运行中" : "JE Engine"}
          <span className="status-divider" />
          <Folder size={12} />
          {snapshot?.name ?? "本地工作空间"}
          <span className="status-divider" />
          {!native && "浏览器预览"}
        </div>
        <div>
          <button
            onClick={() => {
              setSearch("");
              setDialog("models");
            }}
          >
            {model?.provider ?? "provider"} / {modelName}
          </button>
          <select
            aria-label="思考强度"
            value={state?.thinkingLevel ?? "off"}
            disabled={running}
            onChange={(e) =>
              void guard(async () => {
                await api.rpc("set_thinking_level", { level: e.target.value });
                await refresh();
              })
            }
          >
            {(snapshot?.levels.length
              ? snapshot.levels
              : [state?.thinkingLevel ?? "off"]
            ).map((level) => (
              <option key={level}>{level}</option>
            ))}
          </select>
          <span>UTF-8</span>
          <span>本地会话</span>
        </div>
      </footer>
      {dialog && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setDialog(null);
          }}
        >
          <section
            className={`modal ${dialog === "search" ? "command-modal" : ""}`}
            role="dialog"
            aria-modal="true"
            aria-label={
              dialog === "settings"
                ? "模型连接设置"
                : dialog === "models"
                  ? "选择模型"
                  : dialog === "trust"
                    ? "项目上下文授权"
                    : "快速打开"
            }
          >
            <header>
              <h2>
                {dialog === "settings"
                  ? "连接你的模型"
                  : dialog === "models"
                    ? "为任务选择模型"
                    : dialog === "trust"
                      ? "项目上下文"
                      : "快速打开"}
              </h2>
              <IconButton
                label="关闭弹窗"
                onClick={() => {
                  setDialog(null);
                  setKey("");
                }}
              >
                <X size={17} />
              </IconButton>
            </header>
            {dialog === "settings" ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void guard(async () => {
                    await api.login(provider, key);
                    setKey("");
                    apply(await api.bootstrap());
                    setDialog(null);
                  });
                }}
              >
                <p>
                  与终端版共享模型配置。API key 保存在 JE 的本机凭据文件中。
                </p>
                <label>
                  模型提供商
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                  >
                    <option value="deepseek">DeepSeek</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="openrouter">OpenRouter</option>
                    <option value="moonshotai">Moonshot AI</option>
                  </select>
                </label>
                <label>
                  API key
                  <input
                    type="password"
                    autoComplete="off"
                    value={key}
                    onChange={(e) => setKey(e.target.value)}
                    placeholder="输入 API key"
                    required
                  />
                </label>
                {!native && (
                  <p className="form-note">
                    浏览器预览不接收凭据，请在 Electron 桌面窗口连接模型。
                  </p>
                )}
                <button className="primary" disabled={!key.trim() || !native}>
                  保存并连接 <ArrowRight size={14} />
                </button>
                <small>
                  已有 OAuth 登录可通过终端版 JE 配置，桌面端读取同一套凭据。
                </small>
              </form>
            ) : dialog === "trust" ? (
              <>
                <p>
                  授权后，JE 会读取当前项目的 AGENTS.md、.je/skills、prompts
                  和系统指令。项目扩展代码仍保持关闭。
                </p>
                <code className="trust-path">{snapshot?.root}</code>
                <button
                  className="primary"
                  disabled={running || !native}
                  onClick={() =>
                    void guard(async () => {
                      apply(await api.trustWorkspace());
                      setTrusted(true);
                      setTools([]);
                      setDialog(null);
                    })
                  }
                >
                  <ShieldCheck size={15} /> 信任并加载项目上下文
                </button>
              </>
            ) : (
              <>
                <div className="modal-search">
                  <Search size={17} />
                  <input
                    autoFocus
                    aria-label={
                      dialog === "models" ? "搜索模型" : "搜索文件与命令"
                    }
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder={
                      dialog === "models"
                        ? "搜索提供商或模型名称…"
                        : "搜索文件、会话，或输入命令…"
                    }
                  />
                  <kbd>ESC</kbd>
                </div>
                <div className="command-results">
                  {dialog === "models" ? (
                    activeModels.map((m) => (
                      <button
                        key={`${m.provider}/${m.id}`}
                        disabled={running}
                        onClick={() =>
                          void guard(async () => {
                            await api.rpc("set_model", {
                              provider: m.provider,
                              modelId: m.id,
                            });
                            apply(await api.bootstrap());
                            setDialog(null);
                          })
                        }
                      >
                        <Code2 size={16} />
                        <span>
                          <strong>{m.id}</strong>
                          <small>
                            {m.provider} ·{" "}
                            {m.contextWindow
                              ? `${Math.round(m.contextWindow / 1000)}k context`
                              : ""}
                          </small>
                        </span>
                        {m.id === model?.id && m.provider === model.provider ? (
                          <Check size={16} />
                        ) : (
                          <ArrowRight size={14} />
                        )}
                      </button>
                    ))
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setDialog(null);
                          void openWorkspace();
                        }}
                      >
                        <FolderOpen size={16} />
                        <span>打开项目目录</span>
                      </button>
                      <button
                        onClick={() => {
                          setDialog(null);
                          void sessionCommand("new_session");
                        }}
                      >
                        <Plus size={16} />
                        <span>新建会话</span>
                      </button>
                      <button onClick={() => setDialog("settings")}>
                        <Plug size={16} />
                        <span>连接模型</span>
                      </button>
                      <button
                        onClick={() => {
                          setDialog(null);
                          setTerminal(true);
                        }}
                      >
                        <Terminal size={16} />
                        <span>打开终端输出</span>
                      </button>
                      {snapshot?.files
                        .filter(
                          (f) =>
                            !f.directory &&
                            f.name.toLowerCase().includes(search.toLowerCase()),
                        )
                        .map((f) => (
                          <button
                            key={f.path}
                            onClick={() => {
                              setDialog(null);
                              void openFile(f.path);
                            }}
                          >
                            <File size={16} />
                            <span>{f.path}</span>
                          </button>
                        ))}
                      {info?.sessions
                        .filter((s) => (s.title ?? "").includes(search))
                        .map((s) => (
                          <button
                            key={s.id}
                            disabled={running}
                            onClick={() => {
                              setDialog(null);
                              void sessionCommand("switch_session", {
                                sessionId: s.id,
                              });
                            }}
                          >
                            <MessageSquare size={16} />
                            <span>{s.title ?? s.id}</span>
                          </button>
                        ))}
                    </>
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
