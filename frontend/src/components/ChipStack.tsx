/**
 * Visual chip stack that decomposes a chip amount into colored poker chips.
 *
 * Uses standard casino denominations (500/100/25/5/1) with distinct colors.
 * Chips are stacked vertically with overlap. Capped at 8 chips max to keep
 * the visual compact. Available in sm/md/lg sizes.
 */

interface ChipStackProps {
  amount: number;
  size?: "sm" | "md" | "lg";
}

const CHIP_DENOM = [
  { value: 500, color: "#9b59b6", rim: "#7d3c98", label: "500" },
  { value: 100, color: "#e74c3c", rim: "#c0392b", label: "100" },
  { value: 25,  color: "#2ecc71", rim: "#27ae60", label: "25" },
  { value: 5,   color: "#3498db", rim: "#2980b9", label: "5" },
  { value: 1,   color: "#ecf0f1", rim: "#bdc3c7", label: "1" },
];

const MAX_CHIPS = 8;

function decompose(amount: number): { color: string; rim: string; label: string }[] {
  const chips: { color: string; rim: string; label: string }[] = [];
  let remaining = amount;

  for (const denom of CHIP_DENOM) {
    while (remaining >= denom.value && chips.length < MAX_CHIPS) {
      chips.push({ color: denom.color, rim: denom.rim, label: denom.label });
      remaining -= denom.value;
    }
  }

  if (remaining > 0 && chips.length === 0) {
    chips.push(CHIP_DENOM[CHIP_DENOM.length - 1]);
  }

  return chips;
}

const SIZES = {
  sm: { chip: 18, overlap: 3, font: 6, stripe: 1.5 },
  md: { chip: 24, overlap: 4, font: 7, stripe: 2 },
  lg: { chip: 30, overlap: 5, font: 8, stripe: 2.5 },
};

function ChipStack({ amount, size = "sm" }: ChipStackProps) {
  if (amount <= 0) return null;

  const chips = decompose(amount);
  const s = SIZES[size];
  const stackHeight = s.chip + (chips.length - 1) * s.overlap;

  return (
    <div
      style={{
        position: "relative",
        width: s.chip,
        height: stackHeight,
        flexShrink: 0,
      }}
    >
      {chips.map((chip, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            bottom: i * s.overlap,
            left: 0,
            width: s.chip,
            height: s.chip,
            borderRadius: "50%",
            background: `radial-gradient(circle at 40% 35%, ${chip.color}, ${chip.rim})`,
            border: `${s.stripe}px solid ${chip.rim}`,
            boxShadow:
              i === 0
                ? `0 2px 4px rgba(0,0,0,0.4)`
                : `0 1px 2px rgba(0,0,0,0.3)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: chips.length - i,
          }}
        >
          {/* Dashed stripe ring */}
          <div
            style={{
              position: "absolute",
              inset: s.stripe + 1,
              borderRadius: "50%",
              border: `${s.stripe}px dashed rgba(255,255,255,0.35)`,
              pointerEvents: "none",
            }}
          />
        </div>
      ))}
    </div>
  );
}

export default ChipStack;
