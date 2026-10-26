import { ClipboardPaste, FileText, Upload } from "lucide-react";
import { useState } from "react";
import { ProgressRule } from "./motion/ProgressRule";
import { Segmented } from "./motion/Segmented";
import { TransitionPanel } from "./motion/TransitionPanel";

interface UploadZoneProps {
  busy: boolean;
  onFile: (file: File) => void;
  onPaste: (text: string) => void;
}

type Mode = "file" | "paste";

const MODES = [
  { value: "file", label: "Upload the export", icon: FileText },
  { value: "paste", label: "Paste the text", icon: ClipboardPaste },
] as const;

/** The home page's one job. A thin progress rule runs along the top while the chat is read. */
export function UploadZone({ busy, onFile, onPaste }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [mode, setMode] = useState<Mode>("file");
  const [text, setText] = useState("");

  const take = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onFile(file);
  };

  return (
    <div className="panel relative px-5 pb-5 pt-3">
      {busy && <ProgressRule />}

      <Segmented options={MODES} value={mode} onChange={setMode} layoutId="upload-mode" label="How to add the chat" variant="tabs" />

      <TransitionPanel activeKey={mode}>
        {mode === "file" ? (
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              take(e.dataTransfer.files);
            }}
            className={`mt-5 flex cursor-pointer flex-col items-center gap-2.5 rounded-md border border-dashed px-6 py-9 text-center transition-colors ${
              dragging ? "border-navy-400 bg-navy-50" : "border-line-strong bg-sunken/50 hover:border-navy-300 hover:bg-navy-50/40"
            }`}
          >
            <span className="grid h-9 w-9 place-items-center rounded-md border border-line bg-surface text-navy-600">
              <Upload size={17} aria-hidden />
            </span>
            <span className="text-sm font-semibold text-fg">Drop your WhatsApp chat here, or choose the file</span>
            <span className="max-w-sm text-xs leading-relaxed text-fg-muted">
              In WhatsApp, open the chat, then More options, Export chat, Without media. You'll get a{" "}
              <code className="font-mono">.txt</code> file.
            </span>
            <input type="file" accept=".txt,text/plain" className="sr-only" disabled={busy} onChange={(e) => take(e.target.files)} />
            <span className="btn btn-primary mt-2" aria-hidden>
              {busy ? "Reading the chat…" : "Choose the .txt file"}
            </span>
          </label>
        ) : (
          <form
            className="mt-5 space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (text.trim()) onPaste(text);
            }}
          >
            <label htmlFor="paste" className="text-xs text-fg-muted">
              Paste the messages exactly as exported, with their dates and times.
            </label>
            <textarea
              id="paste"
              rows={9}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                "12/08/24, 10:16 am - Ravi Traders: Need 40 office chairs\n12/08/24, 10:40 am - Sunrise Furniture: 4500 per chair plus GST"
              }
              className="field font-mono text-xs leading-relaxed"
            />
            <button type="submit" className="btn btn-primary" disabled={busy || !text.trim()}>
              {busy ? "Reading the chat…" : "Read this chat"}
            </button>
          </form>
        )}
      </TransitionPanel>
    </div>
  );
}
