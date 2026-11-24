#!/usr/bin/env python3
"""Renders the "of the day" images for cipherisle.com. Runs every morning from the scheduled job in
.github/workflows/daily.yml; the homepage always points at the same file names, so it changes by itself.

    python daily.py                 # today (US Eastern)
    python daily.py --date 2026-12-25

today/quote.jpg, today/quote-answer.jpg, today/verse.jpg, today/verse-answer.jpg   (1600x1000)
today/*-m.jpg   the same for phones (1000x1500)
today/word.jpg, today/fact.jpg, today/history.jpg (+ -answer, -m): the day's quiz questions, when the
calendar has them (Forgotten Word, Fact of the Day, Today in History)
week/1.jpg ... week/7.jpg   yesterday back to a week ago, solved (800x800)
"""
import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MIDNIGHT, DEEP, PARCH, SILVER, BRASS = (11, 18, 32), (22, 33, 58), (228, 224, 214), (185, 196, 207), (226, 184, 101)
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


def puzzle(item, title, day, seed, solved, W=1600, H=1000):
    """A cryptogram laid out like the books: code letter under a line you'd write the answer on.
    1600x1000 for desktop; 1000x1500 for phones, where the letters need to be bigger."""
    c = background(W, H, seed)
    d = ImageDraw.Draw(c)
    centered(d, 60, title.upper(), font("Cardo-Bold.ttf", 34), BRASS, W)
    centered(d, 108, day.strftime("%A, %B %-d, %Y"), font("CrimsonText-Italic.ttf", 34), SILVER, W)
    text = item["text"]
    enc = cipher(text, seed)
    words = list(zip(text.upper().split(), enc.split()))
    hint = next((ch for ch in sorted(set(enc), key=lambda x: -enc.count(x)) if ch.isalpha()), None)
    box_w, box_h = W - (200 if W > H else 90), H - 360
    for cw in range(64 if W > H else 110, 22, -2):                     # biggest cells that fit
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
    fa, fc = font("Cardo-Bold.ttf", int(cw * 0.78)), font("Cardo-Regular.ttf", int(cw * (0.5 if W > H else 0.58)))
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
    centered(d, H - 160, "— " + item["credit"], fi, BRASS, W)
    foot = "Solved" if solved else f"Hint: {hint} = {text.upper()[enc.index(hint)]}   ·   each letter stands for another"
    if W < H and not solved:
        foot = f"Hint: {hint} = {text.upper()[enc.index(hint)]}"
    centered(d, H - 90, foot, font("Cardo-Regular.ttf", 28), SILVER, W)
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


def quiz(spec, day, seed, solved, W=1600, H=1000):
    """A four-choice question card in the site's look; the answer version rings the right choice in gold
    and adds the note. spec: title, big, sub, prompt, options, answer, note."""
    c = background(W, H, seed)
    d = ImageDraw.Draw(c)
    wide = W > H
    centered(d, 56, spec["title"].upper(), font("Cardo-Bold.ttf", 34 if wide else 44), BRASS, W)
    centered(d, 104 if wide else 116, day.strftime("%A, %B %-d, %Y"), font("CrimsonText-Italic.ttf", 32 if wide else 40), SILVER, W)
    y = 170 if wide else 210
    for size in ((96, 84, 72, 62, 54, 48) if wide else (110, 96, 84, 72, 62, 54)):
        fb = font("Cardo-Bold.ttf", size)
        lines = wrap(d, spec["big"], fb, W - 200)
        if len(lines) <= (2 if wide else 4):
            break
    for ln in lines:
        centered(d, y, ln, fb, PARCH, W)
        y += int(size * 1.15)
    if spec.get("sub"):
        fs = font("CrimsonText-Italic.ttf", 38 if wide else 46)
        for ln in wrap(d, spec["sub"], fs, W - 220)[:2]:
            centered(d, y + 4, ln, fs, SILVER, W)
            y += 50
    if spec.get("prompt"):
        centered(d, y + 18, spec["prompt"], font("Cardo-Bold.ttf", 34 if wide else 46), BRASS, W)
        y += 70
    opts = [o[:1].upper() + o[1:] for o in spec["options"]]
    cols = 2 if wide and all(len(o) <= 34 for o in opts) else 1
    gap, bw = 24, (W - 200 - (cols - 1) * 24) // cols
    rows = (len(opts) + cols - 1) // cols
    foot = 160 if solved and spec.get("note") else 100
    for osz in ((40, 36, 32, 28) if wide else (58, 52, 46, 40, 36)):   # the largest answers that fit
        fo = font("CrimsonText-SemiBold.ttf", osz)
        lh = int(osz * 1.25)
        boxes = [wrap(d, o, fo, bw - 130)[:3] for o in opts]
        bh = max(int(osz * 2.4), max(len(b) for b in boxes) * lh + 44)
        if y + 20 + rows * (bh + gap) <= H - foot:
            break
    y0 = y + 20 + max(0, (H - foot - (y + 20) - rows * (bh + gap)) // 2)
    for i, lines_ in enumerate(boxes):
        x = 100 + (i % cols) * (bw + gap)
        yy = y0 + (i // cols) * (bh + gap)
        right = solved and i == spec["answer"]
        dim = solved and not right
        d.rounded_rectangle((x, yy, x + bw, yy + bh), radius=18, fill=DEEP,
                            outline=GOLD if right else (SILVER if not dim else (70, 80, 100)), width=4 if right else 2)
        d.text((x + 34, yy + bh / 2), "ABCD"[i] + ".", font=font("Cardo-Bold.ttf", osz + 2),
               fill=GOLD if not dim else (110, 120, 140), anchor="lm")
        ty = yy + bh / 2 - len(lines_) * lh / 2
        for ln in lines_:
            d.text((x + 100 + (0 if wide else 14), ty), ln, font=fo, fill=PARCH if not dim else (120, 128, 145))
            ty += lh
    note = spec.get("note", "")
    if note and note.rstrip(".").lower() in opts[spec["answer"]].lower():
        note = ""                                        # the ringed choice already says it
    if solved and note:
        fn = font("CrimsonText-Italic.ttf", 34 if wide else 42)
        for k, ln in enumerate(wrap(d, note, fn, W - 200)[:2]):
            centered(d, H - 140 + k * 42, ln, fn, GOLD, W)
    else:
        centered(d, H - 80, "Think you know it? Tap Show the answer." if not solved else "cipherisle.com",
                 font("Cardo-Regular.ttf", 28), SILVER, W)
    return c


POS = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb"}


def quiz_specs(items):
    """The day's quiz cards from the calendar: (file name, spec)."""
    out = []
    w = items.get("word")
    if w:
        out.append(("word", dict(title="Forgotten word of the day", big=w["word"], sub=POS.get(w.get("pos") or "", ""),
                                 prompt="What does it mean?", options=w["options"], answer=w["answer"],
                                 note=w.get("definition", ""))))
    f = items.get("fact")
    if f and f.get("question"):
        out.append(("fact", dict(title="Fact of the day", big=f["question"], options=f["options"],
                                 answer=f["answer"], note=f.get("why", ""))))
    h = items.get("history")
    if h:
        out.append(("history", dict(title="Today in history", big=h["about"].rsplit(",", 1)[0], sub=h["headline"],
                                    prompt="What year was it?", options=h["options"], answer=h["answer"],
                                    note=h["about"])))
    return out


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
    quiz_items = dict(items)
    for feed in ("word", "fact", "history"):         # the Shorts rotate, but the site shows all three daily:
        for k in [-b for b in range(1, 31)] + list(range(1, 31)):   # a day without one shows the latest
            if feed in quiz_items:                                   # before it, else the next one coming
                break
            got = calendar(day + timedelta(days=k)).get(feed)
            if got:
                quiz_items[feed] = got
    for name, spec in quiz_specs(quiz_items):
        seed = f"{day}-{name}"
        save(quiz(spec, day, seed, False), HERE / "today" / f"{name}.jpg")
        save(quiz(spec, day, seed, True), HERE / "today" / f"{name}-answer.jpg")
        save(quiz(spec, day, seed, False, 1000, 1500), HERE / "today" / f"{name}-m.jpg")
        save(quiz(spec, day, seed, True, 1000, 1500), HERE / "today" / f"{name}-answer-m.jpg")
    for feed, title in (("quote", "Quote of the day"), ("verse", "Verse of the day")):
        if feed in items and items[feed].get("text"):
            seed = f"{day}-{feed}"
            save(puzzle(items[feed], title, day, seed, False), HERE / "today" / f"{feed}.jpg")
            save(puzzle(items[feed], title, day, seed, True), HERE / "today" / f"{feed}-answer.jpg")
            save(puzzle(items[feed], title, day, seed, False, 1000, 1500), HERE / "today" / f"{feed}-m.jpg")
            save(puzzle(items[feed], title, day, seed, True, 1000, 1500), HERE / "today" / f"{feed}-answer-m.jpg")
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
