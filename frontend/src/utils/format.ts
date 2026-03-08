export function formatPlayerName(playerId: string): string {
  return playerId === "human" ? "You" : playerId;
}
