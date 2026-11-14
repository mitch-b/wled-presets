"""Generate illustrative, self-contained SVGs from the saved WLED presets."""

import json
import math
import xml.etree.ElementTree as ET

from validate_presets import ROOT, load_json


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
OUTPUT = ROOT / ".docs"
SCALE = 2.1
# Read-only controller hardware configuration; stop indices are exclusive.
ROOF_OUTPUTS = ((0, 257, True), (257, 621, False))
OFFICE_OUTPUTS = ((0, 59, False), (59, 118, False), (118, 177, False))
ROOF_SPLIT = (571, 234)
# Simplified front fascia and short side returns. Separate runs
# represent overlapping roof tiers, never a lit vertical line across a wall.
ROOF_EAVES = (
    (
        [(1030, 259), (1044, 254), (902, 247)],
        [(899, 235), (914, 223), (705, 204), (727, 219)],
        [(722, 244), ROOF_SPLIT],
    ),
    (
        [ROOF_SPLIT, (557, 233), (513, 286), (118, 278), (132, 287)],
        [(444, 250), (458, 239), (257, 226), (278, 247)],
    ),
)


def element(parent, tag, **attributes):
    return ET.SubElement(
        parent, f"{{{SVG}}}{tag}", {key.rstrip("_").replace("_", "-"): str(value) for key, value in attributes.items()}
    )


def text(parent, x, y, value, **attributes):
    element(parent, "text", x=x, y=y, **attributes).text = value


def document(title, subtitle, description):
    root = ET.Element(
        f"{{{SVG}}}svg",
        {"viewBox": "0 0 1100 500", "role": "img", "aria-labelledby": "title description"},
    )
    element(root, "title", id="title").text = title
    element(root, "desc", id="description").text = description
    element(root, "style").text = """
      text { font-family: system-ui, sans-serif; fill: #a5b4ca; font-size: 13px; }
      .heading { fill: #edf4ff; font-size: 26px; font-weight: 650; }
      .caption { fill: #70849f; font-size: 12px; }
      .motion { display: inline; }
      @media (prefers-reduced-motion: reduce) { .motion { display: none; } }
    """
    defs = element(root, "defs")
    gradient = element(defs, "linearGradient", id="sky", x2="0", y2="1")
    element(gradient, "stop", offset="0", stop_color="#101c30")
    element(gradient, "stop", offset="1", stop_color="#070d18")
    element(root, "rect", width=1100, height=500, rx=20, fill="url(#sky)")
    text(root, 40, 48, title, class_="heading")
    text(root, 40, 76, subtitle)
    text(root, 40, 474, "Illustrative motion and colors, not a WLED emulator. Reduced motion supported.", **{"class": "caption"})
    return root


def line_pairs(points):
    return [(a, b) for a, b in zip(points, points[1:]) if a is not None and b is not None]


def roof_scale(output):
    runs = ROOF_EAVES[output]
    length = sum(math.dist(a, b) for run in runs for a, b in line_pairs(run))
    start, stop, _ = ROOF_OUTPUTS[output]
    return (stop - start) * SCALE / length


def roof_eaves():
    runs = []
    for output, eaves in enumerate(ROOF_EAVES):
        factor = roof_scale(output)
        for run in eaves:
            runs.append([
                tuple(anchor + (value - anchor) * factor for value, anchor in zip(point, ROOF_SPLIT))
                for point in run
            ])
    return runs


def roof_layout(segments):
    """Slice measured-length eave runs at preset boundaries, not at roof corners."""
    edges = []
    distance = 0
    for run_id, run in enumerate(roof_eaves()):
        for a, b in line_pairs(run):
            length = math.dist(a, b)
            edges.append((distance, distance + length, a, b, run_id))
            distance += length
    result = []
    for segment in segments:
        start, stop = segment["start"] * SCALE, segment["stop"] * SCALE
        points, previous_run = [], None
        for low, high, a, b, run_id in edges:
            left, right = max(start, low), min(stop, high)
            if right - left < 1e-8:
                continue
            first = point_at([a, b], (left - low) / (high - low))
            last = point_at([a, b], (right - low) / (high - low))
            if run_id != previous_run or not points:
                if points:
                    points.append(None)
                points.append(first)
            points.append(last)
            previous_run = run_id
        result.append((segment, points))
    return result


def point_at(points, fraction):
    pairs = line_pairs(points)
    lengths = [math.dist(a, b) for a, b in pairs]
    distance = fraction * sum(lengths)
    for (a, b), length in zip(pairs, lengths):
        if distance <= length:
            ratio = distance / length
            return (a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio)
        distance -= length
    return points[-1]


def path_data(points):
    commands, move = [], True
    for point in points:
        if point is None:
            move = True
            continue
        x, y = point
        commands.append(f"{'M' if move else 'L'} {x:.3f},{y:.3f}")
        move = False
    return " ".join(commands)


def rgb(channels):
    return "#" + "".join(f"{value:02x}" for value in channels[:3])


# Effect names from WLED's /json/eff list, limited to effects used by these presets.
FX_NAMES = {
    0: "Solid", 2: "Breathe", 15: "Running", 20: "Sparkle", 27: "Android", 28: "Chase",
    34: "Colorful", 37: "Chase 2", 54: "Chase 3", 63: "Pride 2015", 67: "Colorwaves",
    69: "Fill Noise", 74: "Colortwinkles", 75: "Lake", 76: "Meteor", 79: "Ripple",
    80: "Twinklefox", 81: "Twinklecat", 84: "Solid Pattern Tri", 87: "Glitter", 88: "Candle",
    90: "Fireworks 1D", 102: "Candle Multi", 106: "Twinkleup", 110: "Flow",
    112: "Dancing Shadows", 113: "Washing Machine", 114: "Rotozoomer", 115: "Blends",
    161: "Shimmer", 210: "PS Chase", 218: "Color Clouds",
}
# Approximate CSS stand-ins; unknown effects fall back to soft twinkles.
FX_KINDS = {
    "solid": {0},
    "chase": {15, 27, 28, 37, 54},
    "pattern": {34, 84},
    "wave": {63, 67, 69, 75, 110, 112, 113, 114, 115, 218},
    "comet": {76, 161, 210},
    "breathe": {2},
    "flicker": {88, 102},
    "sparkle": {20, 87, 106},
}
# Representative stops for named WLED palettes used by these presets.
PALETTES = {
    6: ["#5500ab", "#84007c", "#b5004b", "#e5001b", "#e81700", "#ab7700"],
    8: ["#8b0000", "#ff2a00", "#ff8c00", "#ffd040"],
    9: ["#000080", "#0060c0", "#00a0ff", "#40e0d0"],
    11: ["#ff0000", "#ffa500", "#ffff00", "#00ff00", "#0080ff", "#8000ff"],
    36: ["#003070", "#0060ff", "#00c8ff", "#e0f8ff"],
    51: ["#002848", "#0060ff", "#00b080", "#20ff90"],
    52: ["#ff0000", "#ff8c00", "#00a000", "#1840ff"],
    54: ["#1e50ff", "#00c8ff", "#ffe060", "#ff3000"],
}
SLOT_SECONDS = 4


def is_dark(color):
    return max(color[:3]) < 40


def segment_colors(segment):
    colors = [c for c in segment.get("col", []) if c and not is_dark(c)]
    palette = segment.get("pal", 0)
    if palette in PALETTES and segment.get("fx") not in FX_KINDS["chase"]:
        return PALETTES[palette]
    if palette == 2 and colors:
        colors = colors[:1]
    elif palette == 3:
        colors = colors[:2]
    return [rgb(c) for c in colors] or PALETTES.get(palette, ["#ffd9a0"])


def fx_kind(fx):
    return next((kind for kind, ids in FX_KINDS.items() if fx in ids), "twinkle")


def sparse_dashes(seed, dots=10, low=4, high=15):
    gaps, value = [], seed * 7919 + 17
    for _ in range(dots):
        value = (value * 1103515245 + 12345) % 2**31
        gaps.append(low + value % (high - low + 1))
    return " ".join(f"0 {gap}" for gap in gaps), sum(gaps)


def band_dashes(width, count):
    return " ".join(["0 1"] * (width - 1) + [f"0 {1 + (count - 1) * width}"])


class Strip:
    """Dotted strip paths: pathLength = LEDs, so a dash pattern of ``0 1`` is one dot per LED."""

    def __init__(self, root, groups, total):
        self.root, self.groups, self.total = root, groups, total
        self.periods = set()
        self.dashes = {}

    def targets(self, spans):
        targets = [
            g for g, (low, high) in self.groups.items()
            if any(low < min(stop, self.total) and high > start for start, stop in spans)
        ]
        return ["all"] if len(targets) == len(self.groups) else targets

    def layer(self, parent, spans, color, dashes, style="", cls=None, opacity=1.0):
        dash_class = self.dashes.setdefault(dashes, f"d{len(self.dashes)}")
        attributes = dict(stroke=color)
        if opacity < 1:
            attributes["opacity"] = f"{opacity:.2f}"
        attributes["class"] = f"{dash_class} {cls}" if cls else dash_class
        if style:
            attributes["style"] = style
        targets = self.targets(spans)
        if len(targets) == 1:
            return element(parent, "use", href=f"#{targets[0]}", **attributes)
        group = element(parent, "g", **attributes)
        for target in targets:
            element(group, "use", href=f"#{target}")
        return group

    def chase(self, parent, spans, colors, width, seconds, moving=True):
        period = width * len(colors)
        self.periods.add(period)
        for index, color in enumerate(colors):
            if color == "none":
                continue
            style = f"animation-duration:{seconds:g}s;animation-delay:-{seconds * index / len(colors):.2f}s" if moving else ""
            dashes = band_dashes(width, len(colors))
            if not moving:
                style = f"stroke-dashoffset:{-index * width}"
            self.layer(parent, spans, color, dashes, style, f"run run{period}" if moving else None)

    def twinkle(self, parent, spans, colors, seconds, base=0.12, layers=6, seed=0):
        if base:
            self.layer(parent, spans, colors[0], "0 1", opacity=base)
        for index in range(layers):
            dashes, _ = sparse_dashes(seed % 4 * 10 + index)
            duration = seconds * (0.8 + 0.13 * index)
            self.layer(
                parent, spans, colors[index % len(colors)], dashes,
                f"animation-duration:{duration:.2f}s;animation-delay:-{duration * index / layers:.2f}s", "tw",
            )

    def effect(self, parent, segment, overlay=False, seed=0):
        fx, kind = segment.get("fx", 0), fx_kind(segment.get("fx", 0))
        spans = segment["spans"]
        colors = segment_colors(segment)
        pace = 1.6 - segment.get("sx", 128) / 255
        level = segment.get("bri", 255) / 255
        group = element(parent, "g", data_fx=fx, data_leds=" ".join(f"{low}-{min(high, self.total)}" for low, high in spans), opacity=f"{0.55 + 0.45 * level:.2f}")
        if overlay and kind not in ("sparkle", "twinkle", "flicker"):
            group.set("opacity", "0.35")
        if kind == "solid":
            self.layer(group, spans, colors[0], "0 1")
        elif kind in ("chase", "pattern"):
            if kind == "chase":
                chase_colors = ["none" if is_dark(c) else rgb(c) for c in segment.get("col", []) if c]
                if all(c == "none" for c in chase_colors):
                    chase_colors = colors
                if fx == 15:
                    chase_colors = [chase_colors[0], "none"]
                width = max(1, round(1 + segment.get("ix", 128) / 64))
            else:
                chase_colors, width = colors, 2
            moving = kind == "chase"
            self.chase(group, spans, chase_colors, width, round(12 * pace, 1), moving)
        elif kind == "wave":
            if len(colors) == 1:
                colors = colors + [rgb([int(colors[0][i:i + 2], 16) * 2 // 5 for i in (1, 3, 5)])]
            self.chase(group, spans, colors, 6, round(30 * pace, 1))
        elif kind == "comet":
            if not overlay and len(colors) > 1:
                self.layer(group, spans, colors[0], "0 1", opacity=0.3)
            self.periods.add(65)
            self.layer(group, spans, colors[-1], band_dashes(5, 13), f"animation-duration:{9 * pace:.1f}s", "run run65")
        elif kind == "breathe":
            self.layer(group, spans, colors[0], "0 1", f"animation-duration:{10 * pace:.1f}s", "breathe")
        elif kind == "flicker":
            for index, color in enumerate(colors[:3]):
                dashes, _ = sparse_dashes(index, low=1, high=4)
                self.layer(group, spans, color, dashes, f"animation-duration:{2.4 + index * 0.7:.1f}s", "flicker")
        elif kind == "sparkle":
            self.twinkle(group, spans, colors, 5 * pace, base=0 if overlay else 0.1, layers=4, seed=seed + 2)
        else:
            self.twinkle(group, spans, colors, 7 * pace, base=0 if overlay else 0.12, seed=seed)

    def reel(self, lights, labels, presets, label_xy):
        styles = []
        names = [
            key for key, preset in presets.items()
            if key != "0" and "playlist" not in preset
            and any(isinstance(s, dict) and s.get("stop", 1) and "fx" in s for s in preset.get("seg", []))
        ]
        names.sort(key=int)
        total_seconds = SLOT_SECONDS * len(names)
        fade = 100 * 0.6 / total_seconds
        shown = 100 / len(names)
        styles.append(
            f"@keyframes slot {{ 0% {{ opacity: 0 }} {fade:.3f}% {{ opacity: 1 }} {shown - fade:.3f}% {{ opacity: 1 }} "
            f"{shown:.3f}% {{ opacity: 0 }} 100% {{ opacity: 0 }} }}"
        )
        lights.set("data-presets", str(len(names)))
        for slot, key in enumerate(names):
            preset = presets[key]
            timing = dict(
                style=f"animation-duration:{total_seconds}s;animation-delay:-{(total_seconds - slot * SLOT_SECONDS) % total_seconds}s",
                **{"class": "slot" + (" first" if slot == 0 else "")},
            )
            group = element(lights, "g", id=f"preset-{key}", data_preset=key, **timing)
            caption = element(labels, "g", **timing)
            covered, effects, merged = [], [], {}
            for segment in preset["seg"]:
                if not isinstance(segment, dict) or not segment.get("stop", 1) or "fx" not in segment or segment.get("on") is False:
                    continue
                span = (segment.get("start", 0), min(segment.get("stop", self.total), self.total))
                look = json.dumps({k: segment.get(k) for k in ("fx", "sx", "ix", "pal", "col", "bri")}, sort_keys=True)
                overlay = any(low <= span[0] and span[1] <= high for low, high in covered)
                covered.append(span)
                entry = merged.setdefault((look, overlay), dict(segment, spans=[]))
                entry["spans"].append(span)
            for index, ((_, overlay), segment) in enumerate(merged.items()):
                self.effect(group, segment, overlay=overlay, seed=int(key) + index * 11)
                name = FX_NAMES.get(segment.get("fx"), f"Effect {segment.get('fx')}")
                if name not in effects:
                    effects.append(name)
            x, y = label_xy
            text(caption, x, y, f"Preset {key} · {preset.get('n', '').strip(' /')}", **{"class": "preset"})
            text(caption, x, y + 20, " + ".join(effects), **{"class": "caption"})
        return "\n".join(styles)


def strip_style(strip, slots_css):
    periods = strip.periods
    dashes = "\n".join(f".{name} {{ stroke-dasharray: {value} }}" for value, name in strip.dashes.items())
    runs = dashes + "\n" + "\n".join(f"@keyframes run{p} {{ to {{ stroke-dashoffset: -{p}px }} }} .run{p} {{ animation-name: run{p} }}" for p in sorted(periods))
    return f"""
      .glow {{ filter: url(#glow); fill: none; stroke-linecap: round; stroke-width: 3.4; }}
      .preset {{ fill: #edf4ff; font-size: 17px; font-weight: 600; }}
      .slot {{ opacity: 0; animation: slot linear infinite; }}
      .slot.first {{ opacity: 1; }}
      .run {{ animation-timing-function: linear; animation-iteration-count: infinite; }}
      .tw {{ animation: tw ease-in-out infinite; }}
      .breathe {{ animation: breathe ease-in-out infinite; }}
      .flicker {{ animation: flicker ease-in-out infinite alternate; }}
      @keyframes tw {{ 0%, 100% {{ opacity: .05 }} 50% {{ opacity: 1 }} }}
      @keyframes breathe {{ 0%, 100% {{ opacity: .3 }} 50% {{ opacity: 1 }} }}
      @keyframes flicker {{ 0% {{ opacity: .9 }} 30% {{ opacity: .6 }} 55% {{ opacity: .95 }} 80% {{ opacity: .7 }} 100% {{ opacity: .85 }} }}
      {slots_css}
      {runs}
      @media (prefers-reduced-motion: reduce) {{
        .slot, .run, .tw, .breathe, .flicker {{ animation: none; }}
        .slot.first {{ opacity: 1; }}
      }}
    """


def add_pieces(root, pieces, outputs):
    """Define strip pieces once; preset layers reference them with ``<use>``."""
    defs = root.find(f"{{{SVG}}}defs")
    glow = element(defs, "filter", id="glow", x="-5%", y="-50%", width="110%", height="200%")
    element(glow, "feGaussianBlur", stdDeviation="2.5", result="blur")
    merge = element(glow, "feMerge")
    element(merge, "feMergeNode", **{"in": "blur"})
    element(merge, "feMergeNode", **{"in": "SourceGraphic"})
    groups = {}
    for number, (group_id, start, stop, points) in enumerate(pieces):
        output, (bus_start, bus_stop, reverse) = next(
            (output, bus) for output, bus in enumerate(outputs) if bus[0] <= start < bus[1]
        )
        first = bus_stop - start - 1 if reverse else start - bus_start
        element(
            defs, "path", id=f"piece-{number}", d=path_data(points), pathLength=f"{stop - start:g}",
            data_start=f"{start:g}", data_stop=f"{stop:g}", data_output=output, data_output_index=f"{first:g}",
            data_group=group_id,
        )
        low, high = groups.get(group_id, (start, stop))
        groups[group_id] = (min(low, start), max(high, stop))
    everything = element(defs, "g", id="all")
    for group_id in groups:
        element(everything, "use", href=f"#{group_id}")
        group = element(defs, "g", id=group_id)
        for number, piece in enumerate(pieces):
            if piece[0] == group_id:
                element(group, "use", href=f"#piece-{number}")
    return groups


def split_pieces(group_id, start, stop, points):
    """Split a path at gaps (None) into pieces with fractional LED ranges."""
    pieces, current = [], []
    for point in points + [None]:
        if point is None:
            if len(current) > 1:
                pieces.append(current)
            current = []
        else:
            current.append(point)
    lengths = [sum(math.dist(a, b) for a, b in zip(p, p[1:])) for p in pieces]
    result, cursor, total = [], start, sum(lengths)
    for piece, length in zip(pieces, lengths):
        count = (stop - start) * length / total
        result.append((group_id, round(cursor, 3), round(cursor + count, 3), piece))
        cursor += count
    return result


def boundary_segments(physical, extra):
    """Logical segments split at hardware boundaries, tagged with their segment group."""
    result = []
    for segment in physical:
        cuts = sorted({segment["start"], segment["stop"], *[c for c in extra if segment["start"] < c < segment["stop"]]})
        for low, high in zip(cuts, cuts[1:]):
            result.append({"id": segment["id"], "start": low, "stop": high, "group": f"seg-{segment['id']}"})
    return result


def roof_preview():
    presets = load_json(ROOT / "roof-line.json")
    physical = [s for s in presets["14"]["seg"] if s.get("stop", 0) > 0]
    root = document(
        "Roofline preset reel",
        "621 LEDs / nine segments / every saved effect preset in roof-line.json",
        "An anonymized geometric house with a long, low silhouette, recessed entry, "
        "three plain garage bays and asymmetric, stepped roof tiers. "
        "Roof paths are sized to saved LED segment counts; separate eaves are not joined across walls.",
    )
    layout = roof_layout(physical)
    defs = root.find(f"{{{SVG}}}defs")
    for name, top, bottom in (
        ("wall", "#3c4a5b", "#2c3747"),
        ("bay", "#202c3c", "#263343"),
        ("entry", "#1b2838", "#293647"),
    ):
        gradient = element(defs, "linearGradient", id=name, x1="0%", y1="0%", x2="0%", y2="100%")
        element(gradient, "stop", offset="0", stop_color=top)
        element(gradient, "stop", offset="1", stop_color=bottom)
    shadow = element(defs, "radialGradient", id="ground-shadow")
    element(shadow, "stop", offset="0", stop_color="#030912", stop_opacity=".45")
    element(shadow, "stop", offset="1", stop_color="#030912", stop_opacity="0")
    element(root, "ellipse", cx=554, cy=386, rx=505, ry=20, fill="url(#ground-shadow)")
    facades = []
    for output in range(2):
        factor = roof_scale(output)
        group = element(
            root, "g", id=f"facade-{output}",
            transform=f"translate(571 234) scale({factor:.8f}) translate(-571 -234)",
        )
        facades.append(group)
    garage, wing = facades
    # Broad planes intentionally omit identifying facade and landscaping details.
    element(wing, "path", d="M 132,287 L 513,286 L 557,233 L 571,234 V 398 L 513,384 H 132 Z", fill="url(#wall)")
    element(wing, "path", d="M 118,278 L 272,235 L 423,246 L 513,278 L 513,286 L 132,287 Z", fill="#243244")
    element(wing, "path", d="M 513,286 L 557,233 L 571,234 V 398 L 513,384 Z", fill="#293646")
    element(wing, "path", d="M 132,287 L 513,290 V 298 L 132,295 Z", fill="#182536", opacity=".3")
    element(wing, "path", d="M 278,247 L 444,250 V 384 H 278 Z", fill="url(#wall)")
    element(wing, "rect", id="recessed-entry", x=315, y=287, width=92, height=97, fill="url(#entry)")
    element(wing, "path", d="M 315,384 V 287 H 407 V 292 H 320 V 384 Z", fill="#111d2c", opacity=".4")
    element(wing, "path", d="M 257,226 L 343,208 L 458,232 L 458,239 L 444,250 L 278,247 Z", fill="#2b3b4e")

    element(
        garage, "path", id="garage-wall-left",
        d=path_data([(571, 234), (722, 244), (722, 398), (571, 398)]) + " Z",
        fill="url(#wall)",
    )
    element(garage, "path", d="M 557,233 L 700,192 L 788,208 L 722,244 Z", fill="#27364a")
    element(
        garage, "path", id="garage-wall-center",
        d=path_data([(722, 219), (899, 235), (899, 392), (722, 398)]) + " Z",
        fill="url(#wall)",
    )
    element(garage, "path", d="M 705,204 L 752,183 L 914,216 V 223 L 899,235 L 727,219 Z", fill="#2e4054")
    element(
        garage, "path", id="garage-wall-right",
        d=path_data([(899, 235), (902, 247), (1044, 254), (1028, 266), (1028, 388), (899, 392)]) + " Z",
        fill="url(#wall)",
    )
    element(garage, "path", d="M 902,247 L 944,234 L 1044,248 V 254 Z", fill="#253448")
    for index, (x, y, width, bottom) in enumerate(((589, 291, 119, 398), (744, 291, 143, 392), (927, 291, 94, 388))):
        element(garage, "rect", id=f"garage-bay-{index}", x=x, y=y, width=width, height=bottom - y, fill="url(#bay)")
        element(garage, "path", d=f"M {x},{bottom} V {y} H {x + width} v 4 H {x + 4} V {bottom} Z", fill="#111d2c", opacity=".3")

    # Retain the hidden lower eave's LED indices without painting lights across
    # the projecting entry volume.
    mask = element(root.find(f"{{{SVG}}}defs"), "mask", id="portico-occlusion", maskUnits="userSpaceOnUse", x=0, y=0, width=1100, height=500)
    element(mask, "rect", width=1100, height=500, fill="white")
    element(mask, "rect", x=278, y=258, width=166, height=142, fill="black", transform=wing.get("transform"))
    eave_layer = element(root, "g", id="roof-lighting", mask="url(#portico-occlusion)")
    for run in roof_eaves():
        roof_path = path_data(run)
        element(eave_layer, "path", d=roof_path, fill="none", stroke="#526173", stroke_width=7, stroke_linejoin="round", stroke_linecap="round")
        element(eave_layer, "path", d=roof_path, fill="none", stroke="#a6afbb", stroke_width=1, stroke_linejoin="round")
    pieces = []
    for segment, points in roof_layout(boundary_segments(physical, [bus[0] for bus in ROOF_OUTPUTS])):
        pieces += split_pieces(segment["group"], segment["start"], segment["stop"], points)
    strip = Strip(root, add_pieces(root, pieces, ROOF_OUTPUTS), 621)
    lights = element(eave_layer, "g", id="preset-reel", **{"class": "glow"})
    reel_css = strip.reel(lights, element(root, "g", id="preset-labels"), presets, (40, 112))
    style = root.find(f"{{{SVG}}}style")
    style.text += strip_style(strip, reel_css)

    # The two configured data outputs meet around the left garage corner (LED 257).
    split_index = 257
    split_segment, split_path = next(
        (segment, points)
        for segment, points in layout
        if segment["start"] <= split_index < segment["stop"]
    )
    split = point_at(
        split_path,
        (split_index - split_segment["start"]) / (split_segment["stop"] - split_segment["start"]),
    )
    marker = element(root, "marker", id="data-arrow", markerWidth=8, markerHeight=8, refX=6, refY=3, orient="auto")
    element(marker, "path", d="M 0,0 L 6,3 L 0,6 Z", fill="#71cbe0")
    element(
        root, "path", id="output-0-direction", d=path_data([(split[0] + 9, split[1] - 16), (split[0] + 83, split[1] - 11)]),
        data_output=0, fill="none", stroke="#71cbe0", stroke_width=1.5, marker_end="url(#data-arrow)",
    )
    element(
        root, "path", id="output-1-direction", d=path_data([(split[0] - 9, split[1] - 16), (split[0] - 26, split[1] - 17), (split[0] - 60, split[1] + 23)]),
        data_output=1, fill="none", stroke="#71cbe0", stroke_width=1.5, marker_end="url(#data-arrow)",
    )
    element(root, "circle", id="roof-data-split", data_index=split_index, cx=f"{split[0]:.2f}", cy=f"{split[1]:.2f}", r=5, fill="#71cbe0", stroke="#101c30", stroke_width=2)
    text(root, split[0], 128, "DATA SPLIT · LEFT GARAGE CORNER", text_anchor="middle", fill="#a8e7f2", font_size=10)
    text(root, split[0], 146, "LED 257 boundary · 63 LEDs into segment 3", text_anchor="middle", **{"class": "caption"})
    element(root, "path", d=f"M {split[0]},155 V {split[1] - 24}", stroke="#71cbe0", opacity=.4, stroke_dasharray="3 5")
    text(root, 75, 414, "OUT 2 · 364 LEDs · forward", fill="#a8e7f2", font_size=11)
    text(root, 1025, 414, "OUT 1 · 257 LEDs · reversed", text_anchor="end", fill="#a8e7f2", font_size=11)
    text(root, 40, 445, "Simplified silhouette / stepped roof tiers · architectural details intentionally omitted.", **{"class": "caption"})
    return root


def office_preview():
    presets = load_json(ROOT / "office-shelves.json")
    physical = presets["1"]["seg"][:3]
    root = document(
        "Office shelves preset reel",
        "177 LEDs / three equal 59-LED strips / every saved effect preset in office-shelves.json",
        "Three staggered LED strips on a shelf frame, matching the supplied sketch. "
        "Top-to-bottom strip order and left-to-right direction are illustrative.",
    )
    for x in (225, 550, 875):
        element(root, "path", d=f"M {x},140 V 402", stroke="#344a62", stroke_width=4)
    pieces = []
    for row, segment in enumerate(physical):
        y = 190 + row * 80
        x = 170 if row != 1 else 330
        width = (segment["stop"] - segment["start"]) * 8
        element(root, "path", d=f"M 110,{y + 6} H 990", stroke="#41556d", stroke_width=3)
        element(root, "rect", x=x - 5, y=y - 9, width=width + 10, height=13, rx=3, fill="#25394e", stroke="#4b6178")
        pieces.append((f"seg-{segment['id']}", segment["start"], segment["stop"], [(x, y - 2.5), (x + width, y - 2.5)]))
        text(root, 970, y - 16, f"{segment['stop'] - segment['start']} LEDs", text_anchor="end")
    strip = Strip(root, add_pieces(root, pieces, OFFICE_OUTPUTS), 177)
    lights = element(root, "g", id="preset-reel", **{"class": "glow"})
    reel_css = strip.reel(lights, element(root, "g", id="preset-labels"), presets, (40, 112))
    root.find(f"{{{SVG}}}style").text += strip_style(strip, reel_css)
    text(root, 40, 435, "Equal strip lengths, staggered placement. Thin lines are shelves and supports, not LEDs.", **{"class": "caption"})
    return root


def main():
    for filename, render in (("roofline-preview.svg", roof_preview), ("office-shelves-preview.svg", office_preview)):
        root = render()
        ET.indent(root, space="  ")
        (OUTPUT / filename).write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")
        print(f"Rendered {OUTPUT / filename}")


if __name__ == "__main__":
    main()
