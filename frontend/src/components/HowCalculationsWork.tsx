/**
 * Informational modal explaining how hint and hand-review calculations work.
 * Covers equity vs random, weighted equity (vs range), pot odds, and recommendation logic.
 */
import Modal from "./Modal";

interface Props {
  open: boolean;
  onClose: () => void;
}

const SECTION_HEADING = {
  fontSize: 13,
  fontWeight: 700,
  color: "var(--accent)",
  marginTop: 16,
  marginBottom: 6,
} as const;

const BODY = {
  fontSize: 12,
  color: "var(--text-secondary)",
  lineHeight: 1.55,
  marginBottom: 8,
} as const;

export default function HowCalculationsWork({ open, onClose }: Props) {
  return (
    <Modal open={open} onClose={onClose} title="How calculations work" maxWidth={520} titleId="how-calculations-title">
      <div style={{ padding: "0 4px" }}>
        <p style={BODY}>
          Hints and hand review use two equity numbers plus pot odds to recommend an action (fold, call, raise, etc.).
          The <strong>recommendation is based on weighted equity and pot odds</strong> when we can infer the opponent’s range; otherwise we use equity vs random hands.
        </p>

        <div style={SECTION_HEADING}>Equity (vs random)</div>
        <p style={BODY}>
          Your chance of winning the hand if the opponent’s cards were random. We run a Monte Carlo simulation (e.g. 1,000 runouts): deal random opponent hands from the remaining deck, complete the board, and see how often you win or tie. That win rate is your <strong>equity vs random</strong>. It’s a baseline that ignores how the opponent has been betting.
        </p>

        <div style={SECTION_HEADING}>Weighted equity (equity vs range)</div>
        <p style={BODY}>
          When the opponent has taken actions this hand (e.g. raised preflop, bet the flop), we infer a <strong>range</strong>—the set of hands they might have given those actions. Rules (no AI) narrow that range: e.g. a preflop raiser might have the top ~18% of hands; a 3-bet might be ~4%. We then run a Monte Carlo simulation where the opponent’s hand is drawn only from that range instead of randomly. Your win rate in that simulation is your <strong>weighted equity</strong> (or “equity vs range”). This is the number we use for the recommendation when a range is available.
        </p>

        <div style={SECTION_HEADING}>Pot odds</div>
        <p style={BODY}>
          The minimum equity you need to call profitably. Formula: <strong>pot odds = to_call ÷ (pot + to_call)</strong>, expressed as a percentage. For example, if the pot is 50 and you must call 10, pot odds = 10 / 60 ≈ 17%. If your equity is above that, calling is profitable in the long run.
        </p>

        <div style={SECTION_HEADING}>How the recommendation is chosen</div>
        <p style={BODY}>
          We compare the equity we use (weighted equity when available, otherwise equity vs random) to the pot odds and fixed thresholds:
        </p>
        <ul style={{ ...BODY, paddingLeft: 18, marginTop: -4 }}>
          <li><strong>When there is a bet to call:</strong> If equity &gt; pot odds + 15% → raise. If equity is within 5% of pot odds → call. If equity &lt; pot odds − 5% → fold.</li>
          <li><strong>When you can check for free:</strong> If equity &gt; 65% → bet. If 30–65% → check. If &lt; 30% → check (and consider folding to a bet).</li>
        </ul>
        <p style={BODY}>
          So the same hand can be a “raise” when we use weighted equity (e.g. 84% vs a loose range) but would look like a “fold” if we only looked at equity vs random (e.g. 9%). Showing both numbers lets you see why the recommendation makes sense and how much the opponent’s range matters.
        </p>

        <div style={{ ...SECTION_HEADING, marginTop: 20 }}>Summary</div>
        <p style={BODY}>
          <strong>Equity (vs random)</strong> = your win rate vs random opponent hands. <strong>Weighted equity</strong> = your win rate vs the opponent’s inferred range from their betting. We use weighted equity for the recommendation when we have it; otherwise we use equity vs random. <strong>Pot odds</strong> = break-even equity to call. The hint and hand review show both equity numbers when range-based calculation was used so the numbers stay consistent and transparent.
        </p>
      </div>
    </Modal>
  );
}
