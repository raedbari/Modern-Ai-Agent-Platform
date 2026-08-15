import { Bot } from "lucide-react";

type AthkaLogoProps = {
  compact?: boolean;
};

export function AthkaLogo({
  compact = false,
}: AthkaLogoProps) {
  return (
    <div
      className="athka-logo"
      aria-label="Athkachatbots"
    >
      <span className="athka-logo__mark">
        <Bot aria-hidden="true" />
      </span>

      {!compact && (
        <span className="athka-logo__text">
          <strong>Athka</strong>
          <span>chatbots</span>
        </span>
      )}
    </div>
  );
}
