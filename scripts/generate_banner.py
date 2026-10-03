"""
PIYUSH Modern Animated ASCII Profile Banner Generator
Produces a high-framerate, silky-smooth looping GIF for GitHub README profiles.
"""

import os
import sys
import numpy as np
from PIL import Image, ImageFilter

def generate_banner(
    source_img_path,
    output_gif_path,
    num_frames=60,
    fps=20,
):
    print(f"Loading source image from: {source_img_path}")
    orig = Image.open(source_img_path).convert("RGB")
    arr = np.array(orig, dtype=np.float32)
    H, W, C = arr.shape

    # Identify elements by brightness
    bright = (arr[:, :, 0] > 70)

    # Simple 2D morphological operations
    def erode(mask, k=5):
        pad = k // 2
        padded = np.pad(mask, pad, mode='constant', constant_values=0)
        res = np.ones_like(mask)
        for dy in range(k):
            for dx in range(k):
                res = res & padded[dy:dy+mask.shape[0], dx:dx+mask.shape[1]]
        return res

    def dilate(mask, k=5):
        pad = k // 2
        padded = np.pad(mask, pad, mode='constant', constant_values=0)
        res = np.zeros_like(mask)
        for dy in range(k):
            for dx in range(k):
                res = res | padded[dy:dy+mask.shape[0], dx:dx+mask.shape[1]]
        return res

    # Separate letter tiles from wireframe lines
    letter_region = bright[90:300, 120:900]
    core = erode(letter_region, k=7)
    blocks_sub = dilate(core, k=9) & letter_region
    wire_sub = letter_region & (~blocks_sub)

    blocks_mask = np.zeros((H, W), dtype=bool)
    blocks_mask[90:300, 120:900] = blocks_sub

    wire_mask = np.zeros((H, W), dtype=bool)
    wire_mask[90:300, 120:900] = wire_sub

    # Mask for bottom line text: y in 325..350, x in 50..660
    bottom_text_mask = (np.arange(H)[:, None] >= 325) & (np.arange(H)[:, None] <= 350) & (np.arange(W) >= 80) & (np.arange(W) <= 660) & (arr[:, :, 0] > 60)

    # Prompt mask '>'
    prompt_mask = (np.arange(H)[:, None] >= 332) & (np.arange(H)[:, None] <= 348) & (np.arange(W) >= 55) & (np.arange(W) <= 75) & (arr[:, :, 0] > 70)

    # Divider line mask at y=306
    divider_mask = (np.arange(H)[:, None] >= 305) & (np.arange(H)[:, None] <= 308) & (arr[:, :, 0] > 20)

    # Top text mask: 'PIYUSH' part in 'github://profile/PIYUSH' (x in 235..380, y in 45..75)
    top_piyush_mask = (np.arange(H)[:, None] >= 45) & (np.arange(H)[:, None] <= 75) & (np.arange(W) >= 230) & (np.arange(W) <= 380) & (arr[:, :, 0] > 70)

    Y, X = np.indices((H, W))

    frames = []
    print(f"Rendering {num_frames} frames ({fps} fps)...")

    for i in range(num_frames):
        t = i / num_frames
        frame_arr = arr.copy()

        # 1. Primary Cyan Laser Pulse across the wireframe traces
        # Sweeps from left (x=70) to right (x=950)
        p1_x = 70 + t * (950 - 70)
        # 2. Secondary Violet Trail Pulse offset by 180 degrees
        p2_x = 70 + ((t + 0.5) % 1.0) * (950 - 70)

        dist1 = np.abs(X - p1_x)
        dist2 = np.abs(X - p2_x)

        pulse1 = np.exp(-((dist1 / 40.0) ** 2))
        pulse2 = np.exp(-((dist2 / 34.0) ** 2)) * 0.75

        # Glow layer for soft bloom
        glow_layer = np.zeros((H, W, 3), dtype=np.float32)
        cyan_rgb = np.array([0, 245, 255], dtype=np.float32)
        purple_rgb = np.array([160, 110, 255], dtype=np.float32)

        glow_layer[wire_mask] = (
            pulse1[wire_mask, None] * cyan_rgb * 1.7 +
            pulse2[wire_mask, None] * purple_rgb * 1.3
        )

        glow_img = Image.fromarray(np.clip(glow_layer, 0, 255).astype(np.uint8))
        bloom_soft = glow_img.filter(ImageFilter.GaussianBlur(radius=5))
        bloom_core = glow_img.filter(ImageFilter.GaussianBlur(radius=2))

        bloom_arr = np.array(bloom_soft, dtype=np.float32) * 1.1 + np.array(bloom_core, dtype=np.float32) * 0.9
        frame_arr += bloom_arr

        # Direct illumination boost on the wireframe traces
        frame_arr[wire_mask] += pulse1[wire_mask, None] * np.array([130, 185, 230], dtype=np.float32)
        frame_arr[wire_mask] += pulse2[wire_mask, None] * np.array([100, 80, 180], dtype=np.float32)

        # 2. Specular Holographic Sheen on the Letters PIYUSH
        # Diagonal beam reflection across the tiles
        diag = X * 0.72 + Y * 0.55
        sheen_pos = t * (W * 0.72 + H * 0.55)
        dist_sheen = np.abs(diag - sheen_pos)
        sheen = np.exp(-((dist_sheen / 42.0) ** 2))
        frame_arr[blocks_mask] += sheen[blocks_mask, None] * np.array([55, 70, 90], dtype=np.float32)

        # 3. Divider line subtle energy ripple
        frame_arr[divider_mask] += (pulse1[divider_mask, None] * 0.45 + pulse2[divider_mask, None] * 0.3) * np.array([0, 180, 220], dtype=np.float32)

        # 4. Prompt '>' glowing pulse
        prompt_glow = 0.55 + 0.45 * np.sin(2 * np.pi * t)
        frame_arr[prompt_mask] = np.array([0, 215, 250], dtype=np.float32) * prompt_glow + np.array([190, 210, 235], dtype=np.float32) * (1 - prompt_glow)

        # 5. Bottom text soft highlight as the wave passes over each word
        sub_dist = np.abs(X - p1_x)
        sub_wave = np.exp(-((sub_dist / 65.0) ** 2)) * 0.45
        frame_arr[bottom_text_mask] += sub_wave[bottom_text_mask, None] * np.array([0, 180, 220], dtype=np.float32)

        # 6. Top text 'PIYUSH' subtle accent glow as primary pulse passes
        top_dist = np.abs(X - p1_x)
        top_wave = np.exp(-((top_dist / 60.0) ** 2)) * 0.4
        frame_arr[top_piyush_mask] += top_wave[top_piyush_mask, None] * np.array([0, 200, 240], dtype=np.float32)

        # 7. Terminal Cursor Blink (rhythmic blink on/off)
        # 2 blinks per cycle (on for 15 frames, off for 15 frames)
        cursor_on = (i % 30) < 16
        if cursor_on:
            # Cursor block located right after 'shipping '
            cursor_rect = (Y >= 333) & (Y <= 347) & (X >= 668) & (X <= 677)
            frame_arr[cursor_rect] = np.array([0, 240, 255], dtype=np.float32)

        # Final clip and PIL Image
        frame_arr = np.clip(frame_arr, 0, 255).astype(np.uint8)
        frame_img = Image.fromarray(frame_arr)
        frames.append(frame_img)

    print("Quantizing and optimizing GIF palette...")
    # Sample frames to generate high-fidelity palette
    sample_img = frames[num_frames // 4].copy()
    palette_ref = sample_img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)

    quantized_frames = [
        f.quantize(palette=palette_ref, dither=Image.Dither.FLOYDSTEINBERG)
        for f in frames
    ]

    frame_duration_ms = int(1000 / fps)
    print(f"Saving animated GIF to: {output_gif_path} (delay={frame_duration_ms}ms, duration={num_frames * frame_duration_ms / 1000:.1f}s)")
    
    quantized_frames[0].save(
        output_gif_path,
        save_all=True,
        append_images=quantized_frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True
    )
    file_size_kb = os.path.getsize(output_gif_path) / 1024
    print(f"Successfully created {output_gif_path} ({file_size_kb:.1f} KB)")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))
    
    source = r"C:\Users\piyus\.gemini\antigravity-ide\brain\d4ffc2bc-1ca9-4f77-818c-9e94b11baab0\.user_uploaded\media_1791037912832.png"
    target = os.path.join(repo_root, "assets", "banner.gif")
    
    generate_banner(source, target, num_frames=60, fps=20)
