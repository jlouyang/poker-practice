import React from "react";
import Card from "./Card";

interface CommunityCardsProps {
  cards: string[];
}

const CommunityCards: React.FC<CommunityCardsProps> = ({ cards }) => {
  const slots = 5;
  const rendered = [];

  for (let i = 0; i < slots; i++) {
    if (i < cards.length) {
      rendered.push(<Card key={i} card={cards[i]} />);
    } else {
      rendered.push(
        <div
          key={i}
          style={{
            width: 56,
            height: 80,
            borderRadius: 6,
            border: "2px dashed #4a6785",
            opacity: 0.3,
          }}
        />
      );
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
      {rendered}
    </div>
  );
};

export default CommunityCards;
