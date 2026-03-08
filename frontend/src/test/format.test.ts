import { describe, it, expect } from "vitest";
import { formatPlayerName } from "../utils/format";

describe("formatPlayerName", () => {
  it("returns 'You' for the human player", () => {
    expect(formatPlayerName("human")).toBe("You");
  });

  it("returns the player ID for bots", () => {
    expect(formatPlayerName("bot_1")).toBe("bot_1");
    expect(formatPlayerName("bot_3")).toBe("bot_3");
  });
});
