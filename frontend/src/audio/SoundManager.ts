type SoundName =
  | "deal"
  | "check"
  | "call"
  | "bet"
  | "fold"
  | "allIn"
  | "win"
  | "lose"
  | "yourTurn";

const SOUND_ENABLED_KEY = "poker-sound-enabled";

class SoundManager {
  private ctx: AudioContext | null = null;
  private _enabled: boolean;

  constructor() {
    try {
      this._enabled = localStorage.getItem(SOUND_ENABLED_KEY) !== "false";
    } catch {
      this._enabled = true;
    }
  }

  get enabled(): boolean {
    return this._enabled;
  }

  setEnabled(v: boolean) {
    this._enabled = v;
    try { localStorage.setItem(SOUND_ENABLED_KEY, String(v)); } catch { /* noop */ }
  }

  private ensureCtx(): AudioContext | null {
    if (!this.ctx) {
      try { this.ctx = new AudioContext(); } catch { return null; }
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume();
    }
    return this.ctx;
  }

  play(name: SoundName) {
    if (!this._enabled) return;
    const ctx = this.ensureCtx();
    if (!ctx) return;

    switch (name) {
      case "deal": this.playDeal(ctx); break;
      case "check": this.playTap(ctx, 300, 0.03); break;
      case "call": this.playChipClick(ctx); break;
      case "bet": this.playChipStack(ctx); break;
      case "fold": this.playFold(ctx); break;
      case "allIn": this.playAllIn(ctx); break;
      case "win": this.playWin(ctx); break;
      case "lose": this.playLose(ctx); break;
      case "yourTurn": this.playBell(ctx); break;
    }
  }

  private playTone(ctx: AudioContext, freq: number, duration: number, volume: number, type: OscillatorType = "sine", startDelay = 0) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(volume, ctx.currentTime + startDelay);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startDelay + duration);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime + startDelay);
    osc.stop(ctx.currentTime + startDelay + duration + 0.01);
  }

  private playNoiseBurst(ctx: AudioContext, duration: number, volume: number, startDelay = 0) {
    const bufferSize = Math.floor(ctx.sampleRate * duration);
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = (Math.random() * 2 - 1) * 0.5;
    }
    const source = ctx.createBufferSource();
    source.buffer = buffer;

    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 3000;
    filter.Q.value = 0.8;

    const gain = ctx.createGain();
    gain.gain.setValueAtTime(volume, ctx.currentTime + startDelay);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startDelay + duration);

    source.connect(filter).connect(gain).connect(ctx.destination);
    source.start(ctx.currentTime + startDelay);
  }

  private playTap(ctx: AudioContext, freq: number, duration: number) {
    this.playTone(ctx, freq, duration, 0.15, "sine");
  }

  private playDeal(ctx: AudioContext) {
    this.playNoiseBurst(ctx, 0.06, 0.12, 0);
    this.playNoiseBurst(ctx, 0.05, 0.08, 0.08);
  }

  private playChipClick(ctx: AudioContext) {
    this.playTone(ctx, 1200, 0.04, 0.1, "sine");
    this.playTone(ctx, 2400, 0.02, 0.06, "sine", 0.01);
  }

  private playChipStack(ctx: AudioContext) {
    this.playTone(ctx, 1000, 0.03, 0.1, "sine");
    this.playTone(ctx, 1400, 0.03, 0.08, "sine", 0.04);
    this.playTone(ctx, 1100, 0.03, 0.06, "sine", 0.08);
  }

  private playFold(ctx: AudioContext) {
    this.playNoiseBurst(ctx, 0.08, 0.08, 0);
    this.playTone(ctx, 150, 0.08, 0.1, "sine");
  }

  private playAllIn(ctx: AudioContext) {
    for (let i = 0; i < 5; i++) {
      this.playTone(ctx, 900 + i * 150, 0.04, 0.08, "sine", i * 0.04);
    }
  }

  private playWin(ctx: AudioContext) {
    this.playTone(ctx, 523, 0.15, 0.12, "sine", 0);
    this.playTone(ctx, 659, 0.15, 0.12, "sine", 0.12);
    this.playTone(ctx, 784, 0.25, 0.14, "sine", 0.24);
  }

  private playLose(ctx: AudioContext) {
    this.playTone(ctx, 400, 0.2, 0.08, "sine", 0);
    this.playTone(ctx, 320, 0.3, 0.06, "sine", 0.15);
  }

  private playBell(ctx: AudioContext) {
    this.playTone(ctx, 880, 0.12, 0.08, "sine");
    this.playTone(ctx, 1760, 0.08, 0.04, "sine", 0.02);
  }
}

export const soundManager = new SoundManager();
