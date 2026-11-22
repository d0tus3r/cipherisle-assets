#!/usr/bin/env python3
"""Renders the "of the day" images for cipherisle.com. Runs every morning from the scheduled job in
.github/workflows/daily.yml; the homepage always points at the same file names, so it changes by itself.

    python daily.py                 # today (US Eastern)
    python daily.py --date 2026-12-25

today/quote.jpg, today/quote-answer.jpg, today/verse.jpg, today/verse-answer.jpg   (1600x1000)
week/1.jpg ... week/7.jpg   yesterday back to a week ago, solved (800x800)
"""
import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MIDNIGHT, DEEP, PARCH, SILVER, BRASS = (11, 18, 32), (22, 33, 58), (228, 224, 214), (185, 196, 207), (184, 134, 59)
GOLD = (214, 172, 92)
_fonts = {}


def font(name, size):
    if (name, size) not in _fonts:
        _fonts[name, size] = ImageFont.truetype(str(HERE / "fonts" / name), size)
    return _fonts[name, size]


def calendar(day):
    p = HERE / "data" / f"calendar-{day.year}.json"
    return json.loads(p.read_text(encoding="utf-8"))["days"].get(day.isoformat(), {}) if p.exists() else {}


def background(w, h, seed):
    rng = random.Random(seed)
    c = Image.new("RGB", (w, h), MIDNIGHT)
    mask = Image.linear_gradient("L").resize((w, h)).point(lambda v: 255 - v)
    c.paste(Image.new("RGB", (w, h), DEEP), (0, 0), mask)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(w * h // 9000):
        d.text((rng.randrange(w), rng.randrange(h)), chr(65 + rng.randrange(26)),
               font=font("Cardo-Regular.ttf", rng.choice([26, 34, 44])), fill=PARCH + (rng.choice([9, 13, 17]),))
    c.paste(layer, (0, 0), layer)
    d = ImageDraw.Draw(c)
    d.rectangle((14, 14, w - 15, h - 15), outline=BRASS + (0,), width=2)
    return c


def cipher(text, seed):
    rng = random.Random(seed)
    letters = [chr(65 + i) for i in range(26)]
    while True:
        perm = letters[:]
        rng.shuffle(perm)
        if all(a != b for a, b in zip(letters, perm)):
            key = dict(zip(letters, perm))
            return "".join(key.get(c, c) for c in text.upper())


def centered(d, y, text, f, fill, w):
    d.text(((w - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = word
    return lines + [cur] if cur else lines


def puzzle(item, title, day, seed, solved):
    """A cryptogram laid out like the books: code letter under a line you'd write the answer on."""
    W, H = 1600, 1000
    c = background(W, H, seed)
    d = ImageDraw.Draw(c)
    centered(d, 60, title.upper(), font("Cardo-Bold.ttf", 34), BRASS, W)
    centered(d, 108, day.strftime("%A, %B %-d, %Y"), font("CrimsonText-Italic.ttf", 34), SILVER, W)
    text = item["text"]
    enc = cipher(text, seed)
    words = list(zip(text.upper().split(), enc.split()))
    hint = next((ch for ch in sorted(set(enc), key=lambda x: -enc.count(x)) if ch.isalpha()), None)
    box_w, box_h = W - 200, 640
    for cw in range(64, 22, -2):                     # biggest cells that fit
        gap, rowh = cw * 0.6, cw * 2.3
        rows, cur, x = [], [], 0
        for pw, cw_ in words:
            ww = len(pw) * cw
            if cur and x + ww > box_w:
                rows.append(cur)
                cur, x = [], 0
            cur.append((pw, cw_))
            x += ww + gap
        rows.append(cur)
        if len(rows) * rowh <= box_h:
            break
    fa, fc = font("Cardo-Bold.ttf", int(cw * 0.78)), font("Cardo-Regular.ttf", int(cw * 0.5))
    y = 180 + (box_h - len(rows) * rowh) / 2
    for row in rows:
        rw = sum(len(p) * cw for p, _ in row) + gap * (len(row) - 1)
        x = (W - rw) / 2
        for plain, code in row:
            for p, k in zip(plain, code):
                cx = x + cw / 2
                if k.isalpha():
                    d.line((x + 4, y + cw * 1.05, x + cw - 4, y + cw * 1.05), fill=SILVER, width=2)
                    if solved or k == hint:
                        d.text((cx, y + cw * 1.0), p, font=fa, fill=GOLD if solved else PARCH, anchor="ms")
                    d.text((cx, y + cw * 1.2), k, font=fc, fill=SILVER, anchor="mt")
                else:
                    d.text((cx, y + cw * 1.0), p, font=fa, fill=PARCH, anchor="ms")
                x += cw
            x += gap
        y += rowh
    fi = font("CrimsonText-Italic.ttf", 40)
    centered(d, 840, "— " + item["credit"], fi, BRASS, W)
    foot = "Solved" if solved else f"Hint: {hint} = {text.upper()[enc.index(hint)]}   ·   each letter stands for another"
    centered(d, 910, foot, font("Cardo-Regular.ttf", 28), SILVER, W)
    return c


def card(item, label, seed):
    """A solved line for the 'this week' strip."""
    W = H = 800
    c = background(W, H, seed)
    d = ImageDraw.Draw(c)
    centered(d, 56, label.upper(), font("Cardo-Bold.ttf", 28), BRASS, W)
    for size in (52, 46, 40, 35, 31, 27):
        f = font("Cardo-Bold.ttf", size)
        lines = wrap(d, item["text"], f, W - 120)
        if len(lines) * size * 1.35 <= 520:
            break
    y = 120 + (560 - len(lines) * size * 1.35) / 2
    for ln in lines:
        centered(d, y, ln, f, PARCH, W)
        y += size * 1.35
    centered(d, y + 24, "— " + item["credit"], font("CrimsonText-Italic.ttf", 32), BRASS, W)
    centered(d, H - 80, "cipherisle.com", font("Cardo-Regular.ttf", 24), SILVER, W)
    return c


def save(im, path):
    path.parent.mkdir(exist_ok=True)
    im.save(path, quality=86, optimize=True, progressive=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    a = ap.parse_args()
    eastern = datetime.now(timezone(timedelta(hours=-5)))
    day = date.fromisoformat(a.date) if a.date else eastern.date()
    items = calendar(day)
    for feed, title in (("quote", "Quote of the day"), ("verse", "Verse of the day"), ("fact", "Fact of the day")):
        if feed in items:
            seed = f"{day}-{feed}"
            save(puzzle(items[feed], title, day, seed, False), HERE / "today" / f"{feed}.jpg")
            save(puzzle(items[feed], title, day, seed, True), HERE / "today" / f"{feed}-answer.jpg")
    for k in range(1, 8):
        past = day - timedelta(days=k)
        it = calendar(past).get("quote")
        if it:
            label = "Yesterday's answer" if k == 1 else past.strftime("%A, %b %-d")
            save(card(it, label, f"{past}-quote"), HERE / "week" / f"{k}.jpg")
    (HERE / "today" / "date.txt").write_text(day.isoformat() + "\n")
    print("rendered", day)


if __name__ == "__main__":
    main()
