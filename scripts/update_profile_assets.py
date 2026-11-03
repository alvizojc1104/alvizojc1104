from collections import Counter
from html import escape
import json
import math
import os
from pathlib import Path
import random
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
USERNAME = "alvizojc1104"
API_ROOT = "https://api.github.com"
CARD_WIDTH = 520
CARD_HEIGHT = 230


def get_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "alvizojc1104-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def profile_data():
    profile = get_json(f"{API_ROOT}/users/{USERNAME}")
    repositories = []
    for page in range(1, 11):
        page_repositories = get_json(
            f"{API_ROOT}/users/{USERNAME}/repos?per_page=100&page={page}"
        )
        repositories.extend(page_repositories)
        if len(page_repositories) < 100:
            break

    language_repositories = Counter()
    for repository in repositories:
        languages = get_json(repository["languages_url"])
        for language, byte_count in languages.items():
            if byte_count > 0:
                language_repositories[language] += 1

    return profile, repositories, language_repositories


def svg_start(title, subtitle, dark):
    colors = {
        "background": "#0d1117" if dark else "#ffffff",
        "border": "#30363d" if dark else "#d8dee4",
        "surface": "#161b22" if dark else "#f6f8fa",
        "title": "#c4a7ff" if dark else "#7048b8",
        "text": "#e6edf3" if dark else "#24292f",
        "muted": "#8b949e" if dark else "#57606a",
        "line": "#30363d" if dark else "#d8dee4",
    }
    heading = escape(title)
    caption = escape(subtitle)
    start = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}">
<rect x="1" y="1" width="518" height="228" rx="8" fill="{colors['background']}" stroke="{colors['border']}"/>
<text x="28" y="39" fill="{colors['title']}" font-family="Verdana, sans-serif" font-size="21" font-weight="700">{heading}</text>
<text x="28" y="61" fill="{colors['muted']}" font-family="Verdana, sans-serif" font-size="11">{caption}</text>
<path d="M28 75h464" stroke="{colors['line']}"/>
'''
    return start, colors


def stats_card(profile, repositories, dark):
    start, colors = svg_start(
        "GitHub Stats", f"{USERNAME}  /  public profile", dark
    )
    metrics = [
        ("Public repositories", profile.get("public_repos", len(repositories))),
        ("Stars across repositories", sum(repo["stargazers_count"] for repo in repositories)),
        ("Followers", profile.get("followers", 0)),
        ("Following", profile.get("following", 0)),
    ]
    accents = ["#bb9af7", "#f7768e", "#7dcfff", "#9ece6a"]
    body = []
    for index, (label, value) in enumerate(metrics):
        column = index % 2
        row = index // 2
        x = 28 + column * 238
        y = 91 + row * 61
        body.append(
            f'<rect x="{x}" y="{y}" width="224" height="50" rx="6" fill="{colors["surface"]}"/>'
            f'<rect x="{x}" y="{y + 10}" width="3" height="30" rx="1.5" fill="{accents[index]}"/>'
            f'<text x="{x + 14}" y="{y + 20}" fill="{colors["muted"]}" font-family="Verdana, sans-serif" font-size="11">{escape(label)}</text>'
            f'<text x="{x + 14}" y="{y + 41}" fill="{colors["text"]}" font-family="Verdana, sans-serif" font-size="17" font-weight="700">{value:,}</text>'
        )
    footer = f'<text x="28" y="222" fill="{colors["muted"]}" font-family="Verdana, sans-serif" font-size="10">Updated daily from GitHub</text></svg>\n'
    return start + "\n".join(body) + footer


def language_card(language_counts, repository_count, dark):
    start, colors = svg_start(
        "Languages by repo",
        f"Number of public repositories using each language  /  {repository_count} repos",
        dark,
    )
    language_colors = [
        "#7aa2f7", "#e0af68", "#9ece6a", "#bb9af7", "#f7768e", "#7dcfff"
    ]
    entries = sorted(language_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
    body = []
    if entries:
        total = sum(count for _, count in entries)
        bar_x = 28
        bar_width = 464
        for index, (language, count) in enumerate(entries):
            segment_width = bar_width * count / total
            body.append(
                f'<rect x="{bar_x:.2f}" y="87" width="{segment_width:.2f}" height="10" fill="{language_colors[index]}"/>'
            )
            bar_x += segment_width

        for index, (language, count) in enumerate(entries):
            column = index % 2
            row = index // 2
            x = 30 + column * 238
            y = 124 + row * 31
            count_label = "1 repo" if count == 1 else f"{count} repos"
            body.append(
                f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{language_colors[index]}"/>'
                f'<text x="{x + 17}" y="{y}" fill="{colors["text"]}" font-family="Verdana, sans-serif" font-size="12">{escape(language)}</text>'
                f'<text x="{x + 221}" y="{y}" text-anchor="end" fill="{colors["muted"]}" font-family="Verdana, sans-serif" font-size="11">{count_label}</text>'
            )
    else:
        body.append(
            f'<text x="28" y="126" fill="{colors["muted"]}" font-family="Verdana, sans-serif" font-size="13">No language data found.</text>'
        )
    return start + "\n".join(body) + "</svg>\n"


def write_cards(profile, repositories, language_counts):
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    cards = {
        "stats-light.svg": stats_card(profile, repositories, False),
        "stats-dark.svg": stats_card(profile, repositories, True),
        "languages-light.svg": language_card(language_counts, len(repositories), False),
        "languages-dark.svg": language_card(language_counts, len(repositories), True),
    }
    for filename, contents in cards.items():
        (assets / filename).write_text(contents, encoding="utf-8")


def draw_bonsai():
    width, height, frames_total = 480, 300, 48
    colors = {
        "trunk": (70, 43, 52), "bark": (111, 63, 76), "bark_light": (161, 99, 116),
        "leaf_dark": (47, 29, 82), "leaf_shadow": (74, 43, 123),
        "leaf": (119, 70, 185), "leaf_light": (166, 112, 225),
        "leaf_glow": (207, 165, 250), "pink": (243, 126, 181),
        "petal": (255, 190, 218), "pot": (143, 70, 52),
        "pot_light": (198, 104, 66), "pot_edge": (241, 161, 100),
        "soil": (52, 36, 43), "gold": (255, 203, 124),
    }
    palette = [0, 0, 0]
    for color in colors.values():
        palette.extend(color)
    palette.extend([0] * (768 - len(palette)))
    color_indexes = {
        color: index + 1 for index, color in enumerate(colors.values())
    }
    pads = [
        (81, 103, 176, 151), (117, 70, 211, 123), (169, 43, 260, 100),
        (228, 64, 323, 119), (288, 96, 391, 146), (125, 125, 226, 173),
        (202, 111, 303, 166), (91, 135, 174, 178),
    ]
    blossoms = [(112, 124), (151, 94), (194, 75), (243, 86), (291, 101), (343, 123), (190, 145), (252, 132)]
    falling_petals = [(58, 181, 3), (405, 159, 5), (371, 209, 7), (89, 226, 2), (423, 247, 6), (64, 113, 1)]
    rng = random.Random(174)
    texture = []
    for left, top, right, bottom in pads:
        dots = []
        for _ in range(92):
            x = rng.randrange(left + 5, right - 4)
            y = rng.randrange(top + 6, bottom - 4)
            dots.append((x, y, rng.choice(("leaf_shadow", "leaf_light", "leaf_glow"))))
        texture.append(dots)

    output_frames = []
    for frame_index in range(frames_total):
        sway = round(2 * math.sin(frame_index * 2 * math.pi / frames_total))
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # A tapered ceramic pot, soil rim, and subtle glazed highlights.
        draw.polygon([(143, 236), (340, 236), (320, 287), (163, 287)], fill=colors["pot"])
        draw.rectangle((137, 229, 347, 241), fill=colors["pot_edge"])
        draw.ellipse((145, 229, 338, 240), fill=colors["soil"])
        draw.line((169, 254, 314, 254), fill=colors["pot_light"], width=3)
        draw.line((178, 275, 303, 275), fill=colors["pot_light"], width=2)

        # Split, curved branches give the silhouette a more natural bonsai shape.
        draw.line([(241, 234), (235 + sway, 200), (216 + sway, 174), (230 + sway, 145), (204 + sway, 116), (218 + sway, 91)], fill=colors["trunk"], width=18, joint="curve")
        draw.line([(233 + sway, 190), (190 + sway, 170), (165 + sway, 146), (136 + sway, 133)], fill=colors["trunk"], width=12, joint="curve")
        draw.line([(220 + sway, 173), (265 + sway, 151), (292 + sway, 126), (332 + sway, 119)], fill=colors["trunk"], width=11, joint="curve")
        draw.line([(229 + sway, 144), (194 + sway, 121), (180 + sway, 98)], fill=colors["trunk"], width=8, joint="curve")
        draw.line([(253 + sway, 157), (280 + sway, 132), (274 + sway, 104)], fill=colors["bark"], width=6, joint="curve")
        draw.line([(238 + sway, 206), (234 + sway, 174), (246 + sway, 153)], fill=colors["bark"], width=4)
        draw.line([(191 + sway, 169), (165 + sway, 146), (136 + sway, 133)], fill=colors["bark_light"], width=3)

        for pad_index, (left, top, right, bottom) in enumerate(pads):
            left += sway
            right += sway
            draw.ellipse((left, top, right, bottom), fill=colors["leaf_dark"])
            draw.ellipse((left + 5, top + 5, right - 5, bottom - 6), fill=colors["leaf_shadow"])
            draw.ellipse((left + 9, top + 6, right - 9, bottom - 14), fill=colors["leaf"] if pad_index % 2 else colors["leaf_light"])
            draw.ellipse((left + 18, top + 7, right - 19, top + 21), fill=colors["leaf_light"])
            for x, y, shade in texture[pad_index]:
                if left + 4 < x + sway < right - 4 and top + 5 < y < bottom - 5:
                    draw.rectangle((x + sway, y, x + sway + 2, y + 2), fill=colors[shade])

        for blossom_index, (x, y) in enumerate(blossoms):
            x += sway + blossom_index % 3
            draw.rectangle((x - 4, y - 2, x + 3, y + 3), fill=colors["pink"])
            draw.rectangle((x - 1, y - 1, x + 1, y + 1), fill=colors["petal"])
            draw.point((x, y), fill=colors["gold"])

        for petal_index, (x, start_y, phase) in enumerate(falling_petals):
            y = (start_y + frame_index * (1 + petal_index % 2) // 3) % 224
            x += round(math.sin((frame_index + phase) * math.pi / 10) * 7)
            draw.polygon([(x, y), (x + 4, y + 2), (x + 1, y + 5), (x - 2, y + 3)], fill=colors["petal"])

        indexed = Image.new("P", (width, height))
        indexed.putpalette(palette)
        indexed.putdata(
            [0 if pixel[3] < 128 else color_indexes[pixel[:3]] for pixel in image.getdata()]
        )
        output_frames.append(indexed)

    output_frames[0].save(
        ROOT / "bonsai/bonsai.gif",
        save_all=True,
        append_images=output_frames[1:],
        duration=85,
        loop=0,
        transparency=0,
        disposal=2,
        optimize=False,
    )


def recolor_koi():
    source = Image.open(ROOT / "koi/koi.gif")
    source_palette = source.getpalette() or []
    source_colors = [
        tuple(source_palette[index:index + 3])
        for index in range(3, len(source_palette), 3)
    ]
    colors = Image.new("RGB", (len(source_colors), 1))
    colors.putdata(source_colors)
    hsv = colors.convert("HSV")
    shifted = Image.new("HSV", hsv.size)
    shifted.putdata([
        ((hue + 92) % 256, saturation, value)
        for hue, saturation, value in hsv.getdata()
    ])
    shifted_colors = list(shifted.convert("RGB").getdata())
    palette = [0, 0, 0] + [channel for color in shifted_colors for channel in color]
    palette += [0] * (768 - len(palette))
    color_indexes = {color: index + 1 for index, color in enumerate(source_colors)}
    frames = []
    durations = []
    for frame_index in range(source.n_frames):
        source.seek(frame_index)
        rgba = source.convert("RGBA")
        indexed = Image.new("P", rgba.size)
        indexed.putpalette(palette)
        indexed.putdata([
            0 if pixel[3] <= 64 else color_indexes[pixel[:3]]
            for pixel in rgba.getdata()
        ])
        frames.append(indexed)
        durations.append(source.info.get("duration", 70))
    frames[0].save(
        ROOT / "koi/koi-coral.gif",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=source.info.get("loop", 0),
        transparency=0,
        disposal=2,
        optimize=True,
    )


def crop_koi():
    path = ROOT / "koi/koi-coral.gif"
    source = Image.open(path)
    width, height = source.size
    base_palette = source.getpalette() or []
    active_bounds = []
    for frame_index in range(source.n_frames):
        source.seek(frame_index)
        alpha = source.convert("RGBA").getchannel("A")
        bounds = alpha.getbbox()
        if bounds:
            active_bounds.append(bounds)
    if not active_bounds:
        return
    top = max(0, min(bounds[1] for bounds in active_bounds) - 14)
    bottom = min(height, max(bounds[3] for bounds in active_bounds) + 15)
    if bottom - top >= height - 24:
        return

    base_palette = base_palette[:768] + [0] * max(0, 768 - len(base_palette))
    color_indexes = {}
    for index in range(1, 256):
        color = tuple(base_palette[index * 3:index * 3 + 3])
        color_indexes.setdefault(color, index)

    frames = []
    durations = []
    for frame_index in range(source.n_frames):
        source.seek(frame_index)
        rgba = source.convert("RGBA").crop((0, top, width, bottom))
        indexed = Image.new("P", rgba.size)
        indexed.putpalette(base_palette)
        indexed.putdata([
            0 if pixel[3] <= 64 else color_indexes[pixel[:3]]
            for pixel in rgba.getdata()
        ])
        frames.append(indexed)
        durations.append(source.info.get("duration", 70))

    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=source.info.get("loop", 0),
        transparency=0,
        disposal=2,
        optimize=True,
    )


def main():
    draw_bonsai()
    recolor_koi()
    crop_koi()
    try:
        profile, repositories, language_counts = profile_data()
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        print(f"GitHub API unavailable; leaving existing stat cards in place: {error}")
    else:
        write_cards(profile, repositories, language_counts)
        print(f"Updated stats for {len(repositories)} public repositories.")
    print("Updated bonsai and koi profile art.")


if __name__ == "__main__":
    main()