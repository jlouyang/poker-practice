import { useState, useEffect } from "react";
import Card from "./Card";

interface CommunityCardsProps {
  cards: string[];
}

function CommunityCards({ cards }: CommunityCardsProps) {
  const [prevCount, setPrevCount] = useState(0);

  useEffect(() => {
    const n = cards.length;
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) setPrevCount(n);
    });
    return () => { cancelled = true; };
  }, [cards.length]);
  const slots = 5;
  const rendered = [];

  for (let i = 0; i < slots; i++) {
    if (i < cards.length) {
      const isNew = i >= prevCount;
      const delay = isNew ? (i - prevCount) * 0.1 : undefined;
      rendered.push(<Card key={`${i}-${cards[i]}`} card={cards[i]} animationDelay={delay} />);
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
}

export default CommunityCards;
