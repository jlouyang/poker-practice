/**
 * Keyboard shortcuts for poker actions and navigation.
 *
 * F = fold, C = call/check, R = raise/bet, Space/N = next hand.
 */
import { useEffect } from "react";
import type { LegalAction } from "../types";

interface Options {
  isMyTurn: boolean;
  legalActions: LegalAction[];
  handResult: unknown;
  showReview: boolean;
  sendAction: (action: string, amount: number) => void;
  nextHand: () => void;
}

export function useKeyboardShortcuts({
  isMyTurn,
  legalActions,
  handResult,
  showReview,
  sendAction,
  nextHand,
}: Options) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (handResult && (e.key === " " || e.key.toLowerCase() === "n") && !showReview) {
        e.preventDefault();
        nextHand();
        return;
      }
      if (!isMyTurn || showReview) return;
      const types = new Set(legalActions.map((a) => a.action_type));
      const key = e.key.toLowerCase();

      if (key === "f" && types.has("fold")) {
        sendAction("fold", 0);
      } else if (key === "c") {
        if (types.has("call")) {
          const ca = legalActions.find((a) => a.action_type === "call");
          sendAction("call", ca?.min_amount ?? 0);
        } else if (types.has("check")) {
          sendAction("check", 0);
        }
      } else if (key === "r") {
        const ra = legalActions.find((a) => a.action_type === "raise" || a.action_type === "bet");
        if (ra) sendAction(ra.action_type, ra.min_amount);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isMyTurn, legalActions, handResult, showReview, sendAction, nextHand]);
}
