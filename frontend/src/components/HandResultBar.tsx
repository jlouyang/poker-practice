/**
 * Displays the result of a completed hand with winners and action buttons.
 */
import type { HandResult, AnalysisResult } from "../types";
import { formatPlayerName } from "../utils/format";

interface Props {
  handResult: HandResult;
  analysis: AnalysisResult[] | null;
  onReviewHand: () => void;
  onNextHand: () => void;
}

function HandResultBar({ handResult, analysis, onReviewHand, onNextHand }: Props) { return (
  <div className="hand-result-bar">
    <div>
      {handResult.winners &&
        Object.entries(handResult.winners).map(([pid, info]) => (
          <div key={pid} className="result-win-text">
            {formatPlayerName(pid)} wins {info.amount} with {info.hand}
          </div>
        ))}
      {handResult.player_id && (
        <div className="result-win-text">
          {formatPlayerName(handResult.player_id)} wins {handResult.amount} (opponents folded)
        </div>
      )}
    </div>
    {analysis && analysis.length > 0 && (
      <button className="btn btn-outline" style={{ color: "var(--accent)", borderColor: "var(--accent)" }} onClick={onReviewHand}>
        Review Hand
      </button>
    )}
    <button className="btn btn-primary" onClick={onNextHand}>
      Next Hand
    </button>
  </div>
); }

export default HandResultBar;
