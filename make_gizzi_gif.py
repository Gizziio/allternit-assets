#!/usr/bin/env python3
"""
Gizzi animated GIF — 30-second looping animation.

Timeline:
  0.0 – 20.0s  │  IDLE FLOAT   — gentle bob, blink, beacon pulse
  20.0 – 22.5s │  EXCITED      — bigger/faster bounce, eyes wide open
  22.5 – 23.0s │  WIND-UP      — arm rises, body stills briefly
  23.0 – 27.0s │  WAVE         — right arm waves hello 3×
  27.0 – 30.0s │  SETTLE       — arm lowers, returns to normal float
"""

import math, os, subprocess, tempfile, shutil
from PIL import Image

# ── helpers ────────────────────────────────────────────────────────────────────

def ease_in_out(t):       return t * t * (3 - 2 * t)
def ease_out(t):          return 1 - (1 - t) ** 3
def ease_in(t):           return t ** 3
def lerp(a, b, t):        return a + (b - a) * t
def clamp(v, lo, hi):     return max(lo, min(hi, v))

def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3 - 2 * t)

# ── animation state at time t (seconds) ───────────────────────────────────────

FPS        = 10           # frames per second
DURATION   = 30.0         # total loop length in seconds
TOTAL_FRAMES = int(FPS * DURATION)   # 300
MS_FRAME   = int(1000 / FPS)         # 100 ms
SCALE      = 4
OUTPUT     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gizzi-animation.gif")

# Timeline markers (seconds)
T_IDLE_END       = 20.0
T_EXCITED_END    = 22.5
T_WINDUP_END     = 23.0
T_WAVE_END       = 27.0
T_SETTLE_END     = 30.0   # = DURATION


def anim_state(sec):
    """
    Returns a dict of all animation parameters for the given time (seconds).
    """
    # ── which phase are we in? ─────────────────────────────────────────────
    if sec < T_IDLE_END:
        phase = "idle"
        phase_t = sec / T_IDLE_END                          # 0→1 across idle
    elif sec < T_EXCITED_END:
        phase = "excited"
        phase_t = (sec - T_IDLE_END) / (T_EXCITED_END - T_IDLE_END)
    elif sec < T_WINDUP_END:
        phase = "windup"
        phase_t = (sec - T_EXCITED_END) / (T_WINDUP_END - T_EXCITED_END)
    elif sec < T_WAVE_END:
        phase = "wave"
        phase_t = (sec - T_WINDUP_END) / (T_WAVE_END - T_WINDUP_END)
    else:
        phase = "settle"
        phase_t = (sec - T_WAVE_END) / (T_SETTLE_END - T_WAVE_END)

    # ── base float (always running in background) ──────────────────────────
    # Idle: 1 cycle / 2.4 s  →  freq = 1/2.4 Hz
    float_freq  = 1.0 / 2.4
    float_raw   = math.sin(2 * math.pi * float_freq * sec)   # -1 → +1

    # ── IDLE ───────────────────────────────────────────────────────────────
    if phase == "idle":
        bob_amp   = 3.0
        bob       = float_raw * bob_amp
        eye_h     = 10.0
        # blink every ~4 s; tie to when float_raw ≈ 0 crossing (near peak)
        blink_phase = (sec % 4.0) / 4.0           # 0→1 every 4 s
        if 0.70 <= blink_phase < 0.76:
            p = ease_in_out((blink_phase - 0.70) / 0.03) if blink_phase < 0.73 else \
                ease_in_out(1 - (blink_phase - 0.73) / 0.03)
            eye_h = lerp(10.0, 0.4, p)
        beacon_op   = clamp(0.55 + 0.45 * ((float_raw + 1) / 2), 0.5, 1.0)
        ant_dx      = math.sin(2 * math.pi * float_freq * sec + math.pi) * 1.8
        shadow_rx   = clamp(21 - bob * 0.65, 16, 26)
        shadow_op   = clamp(0.14 - bob * 0.007, 0.07, 0.20)
        arm_raise   = 0.0
        arm_wave_dx = 0.0
        arm_wave_dy = 0.0

    # ── EXCITED ────────────────────────────────────────────────────────────
    elif phase == "excited":
        # Fade from idle params into excited over first 0.3 of phase
        mix       = smoothstep(0.0, 0.3, phase_t)
        # Excited: faster bob (freq × 2) + bigger amplitude
        exc_freq  = float_freq * 2.2
        exc_raw   = math.sin(2 * math.pi * exc_freq * sec)
        bob_amp   = lerp(3.0, 6.5, mix)
        bob       = lerp(float_raw, exc_raw, mix) * bob_amp
        # Eyes go wide (slightly taller)
        eye_h     = lerp(10.0, 12.5, mix)
        beacon_op = lerp(0.7, 1.0, abs(exc_raw) * mix + (1 - mix) * 0.7)
        ant_dx    = math.sin(2 * math.pi * exc_freq * sec + math.pi) * lerp(1.8, 4.0, mix)
        shadow_rx = clamp(21 - bob * 0.65, 14, 28)
        shadow_op = clamp(0.14 - bob * 0.007, 0.06, 0.22)
        arm_raise   = 0.0
        arm_wave_dx = 0.0
        arm_wave_dy = 0.0

    # ── WIND-UP ────────────────────────────────────────────────────────────
    # body slows to almost still while arm starts to rise
    elif phase == "windup":
        calm      = ease_out(phase_t)
        bob       = float_raw * lerp(6.5, 1.5, calm)
        eye_h     = lerp(12.5, 10.0, calm)
        beacon_op = lerp(1.0, 0.8, calm)
        ant_dx    = math.sin(2 * math.pi * float_freq * sec + math.pi) * lerp(4.0, 2.0, calm)
        shadow_rx = clamp(21 - bob * 0.65, 16, 26)
        shadow_op = clamp(0.14 - bob * 0.007, 0.07, 0.20)
        arm_raise   = ease_in(phase_t)    # 0 → 1
        arm_wave_dx = 0.0
        arm_wave_dy = 0.0

    # ── WAVE ───────────────────────────────────────────────────────────────
    # Arm is fully raised, waves side-to-side ~3 cycles
    elif phase == "wave":
        bob       = float_raw * 2.0           # calm float while waving
        eye_h     = 10.0
        beacon_op = 0.9 + 0.1 * float_raw
        ant_dx    = math.sin(2 * math.pi * float_freq * sec + math.pi) * 2.0
        shadow_rx = clamp(21 - bob * 0.5, 16, 26)
        shadow_op = clamp(0.14 - bob * 0.005, 0.07, 0.20)
        arm_raise   = 1.0
        # wave: 3 full side-to-side cycles over the wave window (4 s)
        wave_cycles = 3.0
        wave_raw    = math.sin(2 * math.pi * wave_cycles * phase_t)
        arm_wave_dx = wave_raw * 8.0       # ±8 px side-to-side
        # slight vertical follow-through
        arm_wave_dy = abs(wave_raw) * 3.0  # rises a little at extremes

    # ── SETTLE ─────────────────────────────────────────────────────────────
    else:
        calm      = ease_out(phase_t)
        bob       = float_raw * lerp(2.0, 3.0, calm)
        eye_h     = 10.0
        beacon_op = clamp(0.55 + 0.45 * ((float_raw + 1) / 2), 0.5, 1.0)
        ant_dx    = math.sin(2 * math.pi * float_freq * sec + math.pi) * lerp(2.0, 1.8, calm)
        shadow_rx = clamp(21 - bob * 0.65, 16, 26)
        shadow_op = clamp(0.14 - bob * 0.007, 0.07, 0.20)
        arm_raise   = lerp(1.0, 0.0, ease_out(phase_t))
        arm_wave_dx = lerp(0.0, 0.0, phase_t)   # dampen wave side-to-side
        arm_wave_dx = math.sin(2 * math.pi * 1.5 * phase_t) * lerp(6.0, 0.0, ease_out(phase_t))
        arm_wave_dy = 0.0

    return dict(
        bob=bob, eye_h=eye_h, eye_y=36 + (10 - eye_h) / 2,
        beacon_op=beacon_op, ant_dx=ant_dx,
        shadow_rx=shadow_rx, shadow_op=shadow_op,
        arm_raise=arm_raise, arm_wave_dx=arm_wave_dx, arm_wave_dy=arm_wave_dy,
    )


# ── SVG builder ────────────────────────────────────────────────────────────────

def make_frame_svg(sec, scale=4):
    s   = anim_state(sec)
    sz  = 96 * scale

    bob         = s["bob"]
    eye_h       = s["eye_h"]
    eye_y       = s["eye_y"]
    beacon_op   = s["beacon_op"]
    ant_dx      = s["ant_dx"]
    shadow_rx   = s["shadow_rx"]
    shadow_op   = s["shadow_op"]

    # Right arm: normally sits at body coords; when raised, translate up & wave
    # arm_raise=0 → normal position, arm_raise=1 → fully lifted
    ARM_LIFT_MAX = 22.0   # pixels up when fully raised
    arm_dy = -(s["arm_raise"] * ARM_LIFT_MAX) - s["arm_wave_dy"]
    arm_dx = s["arm_wave_dx"]

    return f'''<svg viewBox="0 0 96 96" width="{sz}" height="{sz}"
     xmlns="http://www.w3.org/2000/svg" shape-rendering="geometricPrecision">

  <!-- shadow (stays grounded) -->
  <ellipse cx="48" cy="86" rx="{shadow_rx:.2f}" ry="4"
           fill="rgba(9,11,14,{shadow_op:.3f})"/>

  <!-- full body group bobs together -->
  <g transform="translate(0,{bob:.2f})">

    <!-- beacon -->
    <rect x="44" y="8" width="8" height="5" rx="2"
          fill="#D97757" opacity="{beacon_op:.3f}"/>

    <!-- antennae -->
    <rect x="{24 + ant_dx:.2f}" y="15" width="17" height="7" rx="3" fill="#D4B08C"/>
    <rect x="{55 - ant_dx:.2f}" y="15" width="17" height="7" rx="3" fill="#D4B08C"/>

    <!-- body -->
    <path d="M25 23H71L78 30V56L72 63V69L64 76H32L24 69V63L18 56V30L25 23Z"
          fill="#D4B08C"/>

    <!-- left hand (static relative to body) -->
    <path d="M18 40H14V44H10V48H14V52H18V56H22V40H18Z" fill="#D4B08C"/>

    <!-- right hand (independent transform for waving) -->
    <g transform="translate({arm_dx:.2f},{arm_dy:.2f})">
      <path d="M78 40H82V44H86V48H82V52H78V56H74V40H78Z" fill="#D4B08C"/>
    </g>

    <!-- face panel -->
    <rect x="24" y="29" width="48" height="31" rx="9"
          fill="rgba(17,19,24,0.16)"/>

    <!-- eyes -->
    <rect x="33" y="{eye_y:.2f}" width="8" height="{eye_h:.2f}" rx="2" fill="#111318"/>
    <rect x="59" y="{eye_y:.2f}" width="8" height="{eye_h:.2f}" rx="2" fill="#111318"/>

    <!-- nose -->
    <path d="M44.5 52L48 42L51.5 52H49.6L48.8 49.5H47.2L46.4 52H44.5Z
             M47.75 47.7H48.25L48 46.65L47.75 47.7Z" fill="#D97757"/>
    <rect x="46" y="47.2" width="4" height="1.4" rx="0.7" fill="#D97757"/>

    <!-- mouth -->
    <text x="48" y="57.5" text-anchor="middle" fill="#D97757"
          font-size="8.2" font-weight="700"
          font-family='"SFMono-Regular","SF Mono",Consolas,"Liberation Mono",Menlo,monospace'
          letter-spacing="-0.4">://</text>

    <!-- legs -->
    <rect x="24" y="74" width="8" height="12" fill="#D4B08C"/>
    <rect x="36" y="74" width="8" height="12" fill="#D4B08C"/>
    <rect x="52" y="74" width="8" height="12" fill="#D4B08C"/>
    <rect x="64" y="74" width="8" height="12" fill="#D4B08C"/>

  </g>
</svg>'''


# ── GIF assembly ───────────────────────────────────────────────────────────────

def to_palette_transparent(img, ref_q=None):
    SENTINEL = (255, 0, 255)
    r, g, b, a = img.split()
    rgb  = Image.merge("RGB", (r, g, b))
    mask = Image.eval(a, lambda v: 0 if v < 128 else 255)
    sentinel_layer = Image.new("RGB", img.size, SENTINEL)
    comp = Image.composite(rgb, sentinel_layer, mask)

    if ref_q is None:
        q = comp.quantize(colors=255, method=Image.Quantize.FASTOCTREE)
    else:
        q = comp.quantize(palette=ref_q, dither=Image.Dither.NONE)

    palette_data = q.getpalette()
    trans_index  = 0
    for idx in range(256):
        if tuple(palette_data[idx*3:idx*3+3]) == SENTINEL:
            trans_index = idx
            break

    px   = q.load()
    mpx  = mask.load()
    w, h = q.size
    for y in range(h):
        for x in range(w):
            if mpx[x, y] == 0:
                px[x, y] = trans_index

    return q, trans_index


def main():
    tmpdir    = tempfile.mkdtemp(prefix="gizzi_")
    png_files = []

    try:
        print(f"Rendering {TOTAL_FRAMES} frames ({DURATION}s @ {FPS}fps, {SCALE}× scale)…")
        for i in range(TOTAL_FRAMES):
            sec = i / FPS
            svg = make_frame_svg(sec, SCALE)

            svg_path = os.path.join(tmpdir, f"f{i:04d}.svg")
            png_path = os.path.join(tmpdir, f"f{i:04d}.png")

            with open(svg_path, "w") as f:
                f.write(svg)

            subprocess.run(["rsvg-convert", svg_path, "-o", png_path],
                           check=True, capture_output=True)
            png_files.append(png_path)

            if (i + 1) % 30 == 0 or i == TOTAL_FRAMES - 1:
                sec_done = (i + 1) / FPS
                print(f"  {i+1:3d}/{TOTAL_FRAMES}  ({sec_done:.0f}s)")

        print("Quantizing & assembling GIF…")
        rgba_frames = [Image.open(p).convert("RGBA") for p in png_files]

        ref_q, _ = to_palette_transparent(rgba_frames[0])
        quantized, trans_idxs = [], []
        for frame in rgba_frames:
            q, ti = to_palette_transparent(frame, ref_q)
            quantized.append(q)
            trans_idxs.append(ti)

        quantized[0].save(
            OUTPUT,
            format="GIF",
            save_all=True,
            append_images=quantized[1:],
            loop=0,
            duration=MS_FRAME,
            optimize=False,
            transparency=trans_idxs[0],
            disposal=2,
        )

        kb = os.path.getsize(OUTPUT) / 1024
        print(f"\nSaved → {OUTPUT}  ({kb:.0f} KB, {TOTAL_FRAMES} frames)")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
