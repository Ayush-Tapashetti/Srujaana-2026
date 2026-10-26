import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { useIsland } from "../motion/StatusIsland";

interface CopyButtonProps {
  text: string;
  label?: string;
  /** What the status island says was copied, e.g. "Question copied". */
  done?: string;
  className?: string;
}

export function CopyButton({ text, label = "Copy", done = "Copied", className = "" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);
  const island = useIsland();

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard can be blocked on plain http; fall back to a hidden field.
      const area = document.createElement("textarea");
      area.value = text;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    setCopied(true);
    island.notify("success", done, "Paste it into WhatsApp");
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <button type="button" onClick={copy} className={`btn btn-secondary btn-sm ${className}`}>
      {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
      {copied ? "Copied" : label}
    </button>
  );
}
