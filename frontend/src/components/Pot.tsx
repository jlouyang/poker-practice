import React from "react";

interface PotProps {
  amount: number;
}

const Pot: React.FC<PotProps> = ({ amount }) => {
  if (amount <= 0) return null;

  return (
    <div
      style={{
        background: "rgba(241, 196, 15, 0.15)",
        border: "1px solid #f1c40f",
        borderRadius: 20,
        padding: "6px 16px",
        color: "#f1c40f",
        fontWeight: 700,
        fontSize: 16,
        textAlign: "center",
      }}
    >
      Pot: {amount}
    </div>
  );
};

export default Pot;
