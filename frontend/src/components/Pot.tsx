/**
 * Center pot display — shows the total pot amount with a chip stack icon.
 * Hidden when the pot is 0 (before blinds are posted).
 */
import ChipStack from "./ChipStack";

interface PotProps {
  amount: number;
}

function Pot({ amount }: PotProps) {
  if (amount <= 0) return null;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        background: "rgba(241, 196, 15, 0.15)",
        border: "1px solid #f1c40f",
        borderRadius: 20,
        padding: "6px 16px",
      }}
    >
      <ChipStack amount={amount} size="md" />
      <span
        style={{
          color: "#f1c40f",
          fontWeight: 700,
          fontSize: 16,
        }}
      >
        {amount}
      </span>
    </div>
  );
}

export default Pot;
