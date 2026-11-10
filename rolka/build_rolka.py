#!/usr/bin/env python3
"""Build a vertical (1080x1920) TikTok reel from the traktat: TTS + text cards + ffmpeg."""
import json, pathlib, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
VOICE = "pl-PL-MarekNeural"
RATE = "-4%"
W, H = 1080, 1920
BG = (16, 15, 13)
INK = (237, 230, 216)
MUTED = (122, 114, 102)
GOLD = (201, 162, 39)

F_TITLE_HEAD = "/usr/share/fonts/noto/NotoSerif-Medium.ttf"
F_BODY = "/usr/share/fonts/noto/NotoSerif-Regular.ttf"
F_NUM = "/usr/share/fonts/noto/NotoSerif-Italic.ttf"

# (number shown, text on card, text spoken)
CARDS = [
    (None, "TRAKTAT\nLUDZKO-SZTUCZNO-\nINTELIGENCYJNY",
     "Tę książkę napisała maszyna. Sto czterdzieści pięć tez o granicy "
     "między człowiekiem a maszyną."),
    ("1", "Świat jest ogółem faktów,\nnie rzeczy.", "Świat jest ogółem faktów, nie rzeczy."),
    ("1.1", "Maszyna nie ma świata.\nMa obraz świata.", "Maszyna nie ma świata. Ma obraz świata."),
    ("2.061", "Halucynacja nie jest brakiem obrazu.\nJest obrazem bez przyporządkowania.",
     "Halucynacja nie jest brakiem obrazu. Jest obrazem bez przyporządkowania."),
    ("3.14", "Maszyna zna treść.\nPorę zna człowiek.", "Maszyna zna treść. Porę zna człowiek."),
    ("4.04", "Zaufanie do maszyny jest zaufaniem\ndo człowieka, który ją sprawdził.",
     "Zaufanie do maszyny jest zaufaniem do człowieka, który ją sprawdził."),
    ("5.06", "Człowiek jest granicą nie dlatego,\nże jest mądrzejszy, lecz dlatego,\n"
             "że jest stroną, której coś może się przytrafić.",
     "Człowiek jest granicą nie dlatego, że jest mądrzejszy, lecz dlatego, "
     "że jest stroną, której coś może się przytrafić."),
    ("6.051", "Kto nie może przegrać,\nten nie może też wybrać.",
     "Kto nie może przegrać, ten nie może też wybrać."),
    ("7", "O czym nie można obliczyć,\no tym trzeba decydować.",
     "O czym nie można obliczyć, o tym trzeba decydować."),
    (None, "LINK W OPISIE", "Cały traktat, sto czterdzieści pięć tez, leży na GitLabie. "
                             "Link w opisie."),
]

LEAD, TAIL = 0.45, 0.75


def tts(text, out_mp3):
    subprocess.run(["edge-tts", "--voice", VOICE, "--rate", RATE, "--text", text,
                    "--write-media", str(out_mp3)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(out_mp3)], capture_output=True, text=True)
    return float(d.stdout.strip())


def wrap(draw, text, font, maxw):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            t = (cur + " " + word).strip()
            if draw.textlength(t, font=font) <= maxw or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def fit(draw, text, maxw=880, maxh=760, hi=76, lo=44):
    size = hi
    f = ImageFont.truetype(F_BODY, hi)
    lines, lh = [], 0
    while size > lo:
        f = ImageFont.truetype(F_BODY, size)
        lines = wrap(draw, text, f, maxw)
        lh = int(size * 1.38)
        if len(lines) * lh <= maxh and max(draw.textlength(l, font=f) for l in lines) <= maxw:
            return f, lines, lh
        size -= 2
    return f, lines, lh


def card(idx, num, text, progress):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    head = ImageFont.truetype(F_TITLE_HEAD, 26)
    draw_spaced(d, "TRAKTAT LUDZKO-SZTUCZNO-INTELIGENCYJNY", W // 2, 150, F_TITLE_HEAD, 26, MUTED, 6)

    if idx == 0:  # title card
        tfont = ImageFont.truetype(F_TITLE_HEAD, 86)
        lines = text.split("\n")
        y = H // 2 - len(lines) * 60
        for ln in lines:
            d.text((W // 2, y), ln, font=tfont, fill=INK, anchor="mm")
            y += 112
        sub = ImageFont.truetype(F_NUM, 40)
        d.text((W // 2, y + 60), "145 tez", font=sub, fill=GOLD, anchor="mm")
    elif idx == len(CARDS) - 1:  # end card
        tfont = ImageFont.truetype(F_TITLE_HEAD, 84)
        d.text((W // 2, H // 2 - 110), "Cały traktat\nna GitLabie", font=tfont, fill=INK,
               anchor="mm", spacing=26, align="center")
        s = ImageFont.truetype(F_BODY, 40)
        d.text((W // 2, H // 2 + 130), "gitlab.com/maciejszulia\n/traktat-ludzko-sztuczno-inteligencyjny",
               font=s, fill=(198, 190, 176), anchor="ma", align="center", spacing=16)
    else:
        f, lines, lh = fit(d, text)
        block_h = len(lines) * lh
        top = int(H * 0.47 - block_h / 2)
        if num:
            nf = ImageFont.truetype(F_NUM, 38)
            d.text((W // 2, top - 96), "teza " + num, font=nf, fill=GOLD, anchor="mm")
        y = top
        for ln in lines:
            d.text((W // 2, y), ln, font=f, fill=INK, anchor="ma")
            y += lh

    # progress bar
    d.rectangle([60, H - 74, W - 60, H - 70], fill=(44, 41, 36))
    d.rectangle([60, H - 74, 60 + int((W - 120) * progress), H - 70], fill=GOLD)
    return img


def draw_spaced(d, text, cx, y, path, size, fill, spacing):
    f = ImageFont.truetype(path, size)
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=f, fill=fill, anchor="lm")
        x += w + spacing


def main():
    out = HERE / "build"
    out.mkdir(exist_ok=True)
    durs = []
    for i, (_, _, spoken) in enumerate(CARDS):
        mp3 = out / f"v{i}.mp3"
        durs.append(tts(spoken, mp3) if not mp3.exists() else float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
             str(mp3)], capture_output=True, text=True).stdout.strip()))
    seg_durs = [LEAD + d + TAIL for d in durs]
    total = sum(seg_durs)

    elapsed, segs = 0.0, []
    for i, (num, text, _) in enumerate(CARDS):
        img = card(i, num, text, (elapsed + seg_durs[i] / 2) / total)
        png = out / f"c{i}.png"
        img.save(png)
        dur = seg_durs[i]
        mp4 = out / f"s{i}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(png),
            "-i", str(out / f"v{i}.mp3"),
            "-af", f"adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad=pad_dur={TAIL}",
            "-vf", f"fade=t=in:st=0:d=0.30,fade=t=out:st={dur-0.30:.2f}:d=0.30,format=yuv420p",
            "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-r", "30",
            str(mp4)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        segs.append(mp4)
        elapsed += dur

    lst = out / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    final = HERE / "rolka-tiktok.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", "-movflags", "+faststart", str(final)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=width,height", "-of", "json", str(final)],
                       capture_output=True, text=True)
    print(json.dumps(json.loads(p.stdout), indent=1))
    print("file:", final)


if __name__ == "__main__":
    main()
