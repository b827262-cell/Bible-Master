#!/usr/bin/env python3
"""為「福音音樂與經文圖區」合成 7 首依經文調性設計的柔和器樂循環音檔（純 Python 標準函式庫）。

每首對應一週七日經文主題，各自擁有獨立調性、BPM、和聲進行、鋼琴／豎琴分解和弦、
溫暖弦樂鋪底與柔和回聲殘響，並於首尾平滑淡入淡出形成無縫循環。

輸出位置：bible-site/site/assets/gallery-{1..7}-{mon..sun}.wav
規格：16-bit PCM、22050 Hz、單聲道、約 24 秒（單檔約 1.0 MB，瀏覽器 <audio> 全平台原生支援）。
日後站長若以 AI 工具生成專屬 MP3，直接更新 bible-site/data/gospel-gallery.json 的 audio 路徑即可替換。
"""

import array
import math
import os
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.abspath(os.path.join(HERE, "..", "site", "assets"))
SR = 22050

# MIDI 音高轉頻率
def midi_hz(n: int) -> float:
    return 440.0 * (2.0 ** ((n - 69) / 12.0))


# 七日經文專屬配樂譜面（依經文意象設計調性、速度、和聲與旋律輪廓）
TRACKS = [
    {
        "file": "gallery-1-mon.wav",
        "title": "清晨禱告（D 大調・60 BPM）",
        "bpm": 60,
        "timbre": "felt_piano",
        # Dmaj7 -> Bm7 -> Gmaj7 -> Asus4 (天未亮到微光破曉)
        "chords": [
            (50, [62, 66, 69, 73]),
            (47, [59, 62, 66, 69]),
            (43, [59, 62, 66, 67]),
            (45, [61, 64, 67, 69]),
        ],
        "pattern": [0, 2, 1, 3, 2, 3, 1, 2],
    },
    {
        "file": "gallery-2-tue.wav",
        "title": "先求神國（G 大調・68 BPM）",
        "bpm": 68,
        "timbre": "harp",
        # G -> D/F# -> Em7 -> Cmaj7 (遼闊山坡與盼望)
        "chords": [
            (43, [59, 62, 67, 71]),
            (42, [57, 62, 66, 69]),
            (40, [59, 62, 67, 71]),
            (48, [60, 64, 67, 71]),
        ],
        "pattern": [0, 1, 2, 3, 2, 1, 3, 2],
    },
    {
        "file": "gallery-3-wed.wav",
        "title": "風浪平靜（C 小調轉 C 大調・58 BPM）",
        "bpm": 58,
        "timbre": "felt_piano",
        # Cm7 -> Abmaj7 -> Fm7 -> Cmaj9 (風暴止息、大大平靜)
        "chords": [
            (48, [60, 63, 67, 70]),
            (44, [60, 63, 67, 68]),
            (41, [56, 60, 63, 68]),
            (48, [60, 64, 67, 74]),
        ],
        "pattern": [0, 1, 2, 1, 3, 2, 1, 0],
    },
    {
        "file": "gallery-4-thu.wav",
        "title": "活水泉源（F 大調・72 BPM）",
        "bpm": 72,
        "timbre": "harp",
        # Fmaj7 -> Dm7 -> Bbmaj7 -> Csus4 (清泉湧流、甘甜流動)
        "chords": [
            (41, [57, 60, 64, 69]),
            (50, [62, 65, 69, 72]),
            (46, [58, 62, 65, 69]),
            (48, [60, 65, 67, 72]),
        ],
        "pattern": [0, 2, 3, 1, 2, 3, 2, 1],
    },
    {
        "file": "gallery-5-fri.wav",
        "title": "祈求尋見（A 小調轉 C 大調・64 BPM）",
        "bpm": 64,
        "timbre": "felt_piano",
        # Am9 -> Fmaj7 -> Cmaj7 -> G6 (懇切叩門、開門應允)
        "chords": [
            (45, [60, 64, 67, 71]),
            (41, [57, 60, 64, 69]),
            (48, [60, 64, 67, 71]),
            (43, [59, 62, 64, 67]),
        ],
        "pattern": [0, 1, 3, 2, 1, 2, 3, 2],
    },
    {
        "file": "gallery-6-sat.wav",
        "title": "上好福分（Eb 大調・56 BPM）",
        "bpm": 56,
        "timbre": "bell_piano",
        # Ebmaj7 -> Cm9 -> Abmaj7 -> Bb6 (靜謐專注、安息主前)
        "chords": [
            (51, [63, 67, 70, 74]),
            (48, [60, 63, 67, 74]),
            (44, [60, 63, 67, 68]),
            (46, [62, 65, 67, 70]),
        ],
        "pattern": [0, 2, 1, 2, 3, 2, 1, 2],
    },
    {
        "file": "gallery-7-sun.wav",
        "title": "生命的光（Bb 大調・66 BPM）",
        "bpm": 66,
        "timbre": "bell_piano",
        # Bbmaj7 -> Gm7 -> Ebmaj7 -> Fadd9 (晨光穿透、照亮生命)
        "chords": [
            (46, [58, 62, 65, 69]),
            (43, [58, 62, 65, 67]),
            (51, [63, 67, 70, 74]),
            (41, [57, 60, 65, 67]),
        ],
        "pattern": [0, 1, 2, 3, 1, 2, 3, 2],
    },
]


def add_pluck(buf, start_idx, freq, dur_s, amp, timbre):
    """加入一顆帶有自然泛音與柔衰減的器樂音符。"""
    n_samples = int(dur_s * SR)
    total = len(buf)
    w = 2.0 * math.pi * freq / SR
    if timbre == "harp":
        harmonics = [(1, 1.0, 2.2), (2, 0.36, 4.0), (3, 0.14, 6.5), (4, 0.05, 9.0)]
        atk = int(0.008 * SR)
    elif timbre == "bell_piano":
        harmonics = [(1, 1.0, 1.6), (2, 0.28, 3.0), (3, 0.16, 5.2), (4, 0.08, 7.5)]
        atk = int(0.014 * SR)
    else:  # felt_piano
        harmonics = [(1, 1.0, 1.9), (2, 0.24, 3.8), (3, 0.08, 6.0)]
        atk = int(0.018 * SR)

    inv_sr = 1.0 / SR
    for i in range(n_samples):
        idx = start_idx + i
        if idx >= total:
            break
        t = i * inv_sr
        env_atk = (i / atk) if i < atk else 1.0
        val = 0.0
        for mult, gain, decay in harmonics:
            val += gain * math.sin(w * mult * i) * math.exp(-decay * t)
        buf[idx] += amp * env_atk * val


def add_pad(buf, start_idx, freqs, dur_s, amp):
    """加入柔和緩起緩落的弦樂鋪底和聲。"""
    n_samples = int(dur_s * SR)
    total = len(buf)
    atk = int(min(1.1, dur_s * 0.28) * SR)
    rel = int(min(1.4, dur_s * 0.32) * SR)
    ws = [(2.0 * math.pi * f / SR, 2.0 * math.pi * (f * 1.0022) / SR) for f in freqs]
    scale = amp / max(1, len(freqs))
    for i in range(n_samples):
        idx = start_idx + i
        if idx >= total:
            break
        if i < atk:
            env = 0.5 - 0.5 * math.cos(math.pi * i / atk)
        elif i > n_samples - rel:
            env = 0.5 - 0.5 * math.cos(math.pi * (n_samples - i) / rel)
        else:
            env = 1.0
        s = 0.0
        for w1, w2 in ws:
            s += 0.65 * math.sin(w1 * i) + 0.35 * math.sin(w2 * i)
        buf[idx] += scale * env * s


def apply_reverb(buf):
    """多延遲柔和空間殘響（營造大教堂與靜心空間感）。"""
    delays = [
        (int(0.083 * SR), 0.26),
        (int(0.149 * SR), 0.20),
        (int(0.241 * SR), 0.14),
        (int(0.367 * SR), 0.09),
    ]
    out = list(buf)
    n = len(buf)
    for d, g in delays:
        for i in range(d, n):
            out[i] += g * buf[i - d]
    return out


def synthesize_track(spec) -> str:
    beat_s = 60.0 / spec["bpm"]
    bar_s = beat_s * 4.0
    # 2 次完整四小節循環（共 8 小節，約 26–34 秒），尾端留自然餘韻與循環交叉淡化
    loops = 2
    total_bars = len(spec["chords"]) * loops
    total_s = total_bars * bar_s
    n_samples = int(total_s * SR)
    buf = [0.0] * n_samples

    step_s = beat_s * 0.5  # 八分音符分解和弦
    bar_idx = 0
    for loop_i in range(loops):
        for bass_midi, notes_midi in spec["chords"]:
            bar_start_s = bar_idx * bar_s
            bar_start_i = int(bar_start_s * SR)

            # 柔和弦樂鋪底（根音 + 和聲核心音）
            pad_freqs = [midi_hz(bass_midi), midi_hz(notes_midi[0]), midi_hz(notes_midi[2])]
            add_pad(buf, bar_start_i, pad_freqs, bar_s * 1.06, 0.22)

            # 低音長音（溫潤支撐）
            add_pluck(buf, bar_start_i, midi_hz(bass_midi), bar_s * 0.95, 0.20, "felt_piano")

            # 分解和弦主旋律（第二遍略提升八度泛音點綴）
            for step_i, pat_idx in enumerate(spec["pattern"]):
                note_midi = notes_midi[pat_idx % len(notes_midi)]
                if loop_i == 1 and step_i in (3, 6):
                    note_midi += 12
                t_i = int((bar_start_s + step_i * step_s) * SR)
                vel = 0.23 if step_i % 2 == 0 else 0.16
                add_pluck(buf, t_i, midi_hz(note_midi), beat_s * 2.2, vel, spec["timbre"])

            bar_idx += 1

    wet = apply_reverb(buf)

    # 首尾平滑淡入淡出（0.35s），確保 <audio loop> 無喀擦雜音
    fade_n = int(0.35 * SR)
    for i in range(fade_n):
        w = 0.5 - 0.5 * math.cos(math.pi * i / fade_n)
        wet[i] *= w
        wet[n_samples - 1 - i] *= w

    peak = max((abs(x) for x in wet), default=1.0)
    norm = (0.82 / peak) if peak > 0 else 1.0

    pcm = array.array("h", (max(-32767, min(32767, int(x * norm * 32767.0))) for x in wet))
    os.makedirs(ASSETS_DIR, exist_ok=True)
    out_path = os.path.join(ASSETS_DIR, spec["file"])
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
    return out_path


def main():
    for spec in TRACKS:
        path = synthesize_track(spec)
        kb = os.path.getsize(path) / 1024.0
        print(f"已產生：{os.path.relpath(path)}（{kb:.0f} KB）— {spec['title']}")


if __name__ == "__main__":
    main()
