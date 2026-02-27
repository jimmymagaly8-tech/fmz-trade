import { useRef } from 'react';
import Editor, { type OnMount } from '@monaco-editor/react';

interface Props {
  code: string;
  onChange: (code: string) => void;
}

const DEFAULT_OPTIONS = {
  fontSize: 14,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 4,
  wordWrap: 'on' as const,
};

export default function StrategyEditor({ code, onChange }: Props) {
  const editorRef = useRef<any>(null);

  const handleMount: OnMount = (editor) => {
    editorRef.current = editor;
    editor.focus();
  };

  return (
    <div style={{ height: '100%', border: '1px solid #d9d9d9', borderRadius: 6 }}>
      <Editor
        height="100%"
        language="python"
        theme="vs-dark"
        value={code}
        onChange={(v) => onChange(v ?? '')}
        onMount={handleMount}
        options={DEFAULT_OPTIONS}
      />
    </div>
  );
}
