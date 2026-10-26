import { useState } from "react";
import type { Tone } from "../types/api";
import { Segmented } from "./motion/Segmented";
import { TransitionPanel } from "./motion/TransitionPanel";
import { CopyButton } from "./ui/CopyButton";

/**
 * The owner's real fear is that asking a loyal customer for a contract feels
 * like distrust. So the message comes in three registers, and the owner
 * picks the one that sounds like them.
 */
export function ToneMessage({ tones }: { tones: Tone[] }) {
  const [key, setKey] = useState<Tone["key"]>("warm");
  const tone = tones.find((t) => t.key === key) ?? tones[0];
  if (!tone) return null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <Segmented
          options={tones.map((t) => ({ value: t.key, label: t.label }))}
          value={key}
          onChange={setKey}
          layoutId="tone"
          label="Tone of the message"
        />
        <CopyButton text={tone.message} label="Copy message" done="Message copied" />
      </div>
      <TransitionPanel activeKey={tone.key}>
        <pre className="well max-h-72 overflow-y-auto whitespace-pre-wrap p-3.5 font-sans text-sm leading-relaxed text-fg">
          {tone.message}
        </pre>
      </TransitionPanel>
    </div>
  );
}
