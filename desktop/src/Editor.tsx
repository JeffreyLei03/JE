import { useEffect, useRef } from "react";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api.js";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution";
import "monaco-editor/esm/vs/basic-languages/typescript/typescript.contribution";
import "monaco-editor/esm/vs/basic-languages/markdown/markdown.contribution";
import "monaco-editor/esm/vs/basic-languages/css/css.contribution";
import "monaco-editor/esm/vs/basic-languages/javascript/javascript.contribution";
import "monaco-editor/esm/vs/basic-languages/html/html.contribution";
import "monaco-editor/esm/vs/basic-languages/yaml/yaml.contribution";
import "monaco-editor/esm/vs/basic-languages/ini/ini.contribution";
import "monaco-editor/esm/vs/language/json/monaco.contribution";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import JsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
const scope = self as typeof self & {
  MonacoEnvironment?: {
    getWorker: (_moduleId: string, label: string) => Worker;
  };
};
scope.MonacoEnvironment = {
  getWorker: (_moduleId, label) =>
    label === "json" ? new JsonWorker() : new EditorWorker(),
};
monaco.editor.defineTheme("je-light", {
  base: "vs",
  inherit: true,
  rules: [],
  colors: {
    "editor.background": "#ffffff",
    "editorLineNumber.foreground": "#b3b8c3",
    "editor.lineHighlightBackground": "#f5f7fa",
    "editor.selectionBackground": "#dce9f7",
  },
});
const languages: Record<string, string> = {
  py: "python",
  ts: "typescript",
  tsx: "typescript",
  js: "javascript",
  jsx: "javascript",
  md: "markdown",
  css: "css",
  json: "json",
  toml: "ini",
  yaml: "yaml",
  yml: "yaml",
  html: "html",
};
export function Editor({
  path,
  text,
  onChange,
  onSave,
  readOnly = false,
}: {
  path: string;
  text: string;
  onChange: (text: string) => void;
  onSave: () => void;
  readOnly?: boolean;
}) {
  const node = useRef<HTMLDivElement>(null);
  const editor = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const callbacks = useRef({ onChange, onSave });
  callbacks.current = { onChange, onSave };
  useEffect(() => {
    if (!node.current) return;
    const instance = monaco.editor.create(node.current, {
      value: text,
      language: languages[path.split(".").pop() ?? ""] ?? "plaintext",
      theme: "je-light",
      readOnly,
      fontFamily: "Consolas, monospace",
      fontSize: 13,
      lineHeight: 23,
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      padding: { top: 18 },
      renderLineHighlight: "line",
      smoothScrolling: true,
    });
    editor.current = instance;
    instance.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () =>
      callbacks.current.onSave(),
    );
    const listener = instance.onDidChangeModelContent(() =>
      callbacks.current.onChange(instance.getValue()),
    );
    return () => {
      listener.dispose();
      instance.getModel()?.dispose();
      instance.dispose();
      editor.current = null;
    };
  }, [path, readOnly]);
  useEffect(() => {
    if (editor.current && editor.current.getValue() !== text)
      editor.current.setValue(text);
  }, [text]);
  return <div className="monaco-host" ref={node} />;
}
