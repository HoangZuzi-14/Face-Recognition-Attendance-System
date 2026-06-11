# rPPG liveness design
## Goal

rPPG adds a weak physiological signal to liveness. It does not prove identity
or measure health. It only checks whether the face region carries a plausible
periodic color signal in a human pulse band.

## Data Flow

`src/rppg.py` provides:

- `RppgFrameBuffer` for one tracked face/session.
- `RppgSessionStore` for managing buffers by session key.
- `mean_rgb()` for stable face ROI color extraction.
- `estimate_pulse()` for POS-style pulse confidence from RGB series.
- `estimate_pulse_from_buffer()` for using timestamps to infer FPS.

The recognition tracker owns one `RppgFrameBuffer`. When `RPPG_ENABLED=True`,
each accepted face match adds the current face crop mean RGB into that buffer
and passes the current pulse result into `assess_liveness()`.

## Signal Method

The first implementation uses a lightweight POS-style transform:

1. Normalize RGB channels over time.
2. Build a pulse-like signal from channel differences.
3. Run FFT over the windowed signal.
4. Search the human pulse band from `0.7` to `4.0` Hz.
5. Convert the dominant band peak into `pulse_confidence`.

Short, flat, invalid, or noisy signals return `UNKNOWN` rather than crashing.

## Operational Notes

- `RPPG_ENABLED` defaults to `False`.
- `RPPG_WINDOW` controls buffer length and defaults to `90`.
- The implementation stores channel means, not full frames, so it stays light.
- rPPG is a fusion signal, not a standalone decision source.
