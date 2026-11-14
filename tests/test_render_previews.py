import math
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import render_previews as previews


class RenderPreviewsTests(unittest.TestCase):
    def test_roof_paths_preserve_physical_segment_proportions(self):
        presets = previews.load_json(previews.ROOT / "roof-line.json")
        physical = [s for s in presets["14"]["seg"] if s.get("stop", 0) > 0]
        for segment, points in previews.roof_layout(physical):
            with self.subTest(segment=segment["id"]):
                length = sum(math.dist(a, b) for a, b in previews.line_pairs(points))
                self.assertAlmostEqual(length, (segment["stop"] - segment["start"]) * previews.SCALE)

    def test_separate_eaves_do_not_draw_or_place_leds_in_gaps(self):
        points = [(0, 0), (10, 0), None, (100, 20), (100, 40)]
        self.assertEqual(previews.path_data(points), "M 0.000,0.000 L 10.000,0.000 M 100.000,20.000 L 100.000,40.000")
        self.assertEqual(previews.point_at(points, 0.5), (100, 25))
        self.assertEqual(previews.point_at(points, 1), (100, 40))

    def test_roof_returns_turn_inward_and_down_like_the_porch(self):
        garage = previews.ROOF_EAVES[0][1]
        porch = previews.ROOF_EAVES[1][1]
        for right_inner, right_outer, left_outer, left_inner in (garage, porch):
            self.assertLess(right_inner[0], right_outer[0])
            self.assertGreater(right_inner[1], right_outer[1])
            self.assertGreater(left_inner[0], left_outer[0])
            self.assertGreater(left_inner[1], left_outer[1])
        left_corner, left_return = previews.ROOF_EAVES[1][0][-2:]
        self.assertGreater(left_return[0], left_corner[0])
        self.assertGreater(left_return[1], left_corner[1])

    @staticmethod
    def pieces(root):
        return [node for node in root.iter() if node.get("id", "").startswith("piece-")]

    def test_strip_pieces_cover_every_led_once_with_no_network_dependencies(self):
        for render, total in ((previews.roof_preview, 621), (previews.office_preview, 177)):
            root = render()
            ranges = sorted((float(p.get("data-start")), float(p.get("data-stop"))) for p in self.pieces(root))
            self.assertEqual(ranges[0][0], 0)
            self.assertEqual(ranges[-1][1], total)
            for (_, stop), (start, _) in zip(ranges, ranges[1:]):
                self.assertAlmostEqual(stop, start)
            for piece in self.pieces(root):
                self.assertAlmostEqual(float(piece.get("pathLength")), float(piece.get("data-stop")) - float(piece.get("data-start")), places=2)
            for node in root.iter():
                self.assertNotEqual(node.tag, f"{{{previews.SVG}}}script")
                if node.get("href"):
                    self.assertTrue(node.get("href").startswith("#"))
            self.assertIn("prefers-reduced-motion", ET.tostring(root, encoding="unicode"))

    def test_reel_includes_every_non_playlist_preset(self):
        for render, filename in ((previews.roof_preview, "roof-line.json"), (previews.office_preview, "office-shelves.json")):
            presets = previews.load_json(previews.ROOT / filename)
            expected = sorted(
                (key for key, preset in presets.items() if key != "0" and preset.get("seg") and "playlist" not in preset),
                key=int,
            )
            root = render()
            slots = [node.get("data-preset") for node in root.find(".//*[@id='preset-reel']")]
            self.assertEqual(slots, expected)
            firsts = [node for node in root.iter() if "first" in node.get("class", "").split()]
            self.assertEqual(len(firsts), 2, "One static fallback preset plus its label")

    def test_committed_images_match_renderer(self):
        for filename, render in (
            ("roofline-preview.svg", previews.roof_preview),
            ("office-shelves-preview.svg", previews.office_preview),
        ):
            root = render()
            ET.indent(root, space="  ")
            expected = ET.tostring(root, encoding="unicode") + "\n"
            self.assertEqual((previews.OUTPUT / filename).read_text(encoding="utf-8"), expected)

    def test_hardware_output_boundaries_and_roof_reversal(self):
        for render, expected in (
            (previews.roof_preview, {0: (0, 256), 257: (1, 0)}),
            (previews.office_preview, {0: (0, 0), 59: (1, 0), 118: (2, 0)}),
        ):
            root = render()
            starts = {float(p.get("data-start")): p for p in self.pieces(root)}
            for index, (output, offset) in expected.items():
                piece = starts[index]
                self.assertEqual(int(piece.get("data-output")), output)
                self.assertEqual(float(piece.get("data-output-index")), offset)
        for piece in self.pieces(previews.roof_preview()):
            self.assertFalse(float(piece.get("data-start")) < 257 < float(piece.get("data-stop")))

    def test_house_uses_only_plain_entry_and_garage_openings(self):
        root = previews.roof_preview()
        openings = []
        for output in range(2):
            facade = root.find(f".//*[@id='facade-{output}']")
            for node in facade:
                self.assertIn(node.tag, (f"{{{previews.SVG}}}path", f"{{{previews.SVG}}}rect"))
                self.assertIsNone(node.get("stroke"), "Facade should not have decorative outlines or panel lines")
                if node.tag == f"{{{previews.SVG}}}rect":
                    openings.append(node.get("id"))
        self.assertCountEqual(openings, ["recessed-entry", "garage-bay-0", "garage-bay-1", "garage-bay-2"])
        self.assertIsNone(root.find(f".//{{{previews.SVG}}}image"), "Do not embed a house photograph")

    def test_garage_walls_join_and_openings_stay_inside(self):
        root = previews.roof_preview()
        walls = []
        for name in ("left", "center", "right"):
            path = root.find(f".//*[@id='garage-wall-{name}']").get("d")
            walls.append([
                tuple(map(float, pair.split(",")))
                for pair in path.split() if "," in pair
            ])
        left, center, right = walls
        self.assertEqual(left[-2], center[-1])
        self.assertEqual(left[1][0], center[0][0])
        self.assertEqual(center[1], right[0])
        self.assertEqual(center[-2], right[-1])

        for index, wall in enumerate(walls):
            bay = root.find(f".//*[@id='garage-bay-{index}']")
            x, y = float(bay.get("x")), float(bay.get("y"))
            width, height = float(bay.get("width")), float(bay.get("height"))
            self.assertGreaterEqual(x, min(point[0] for point in wall))
            self.assertLessEqual(x + width, max(point[0] for point in wall))
            a, b = wall[-2:]
            for corner in (x, x + width):
                floor = a[1] + (b[1] - a[1]) * (corner - a[0]) / (b[0] - a[0])
                self.assertLessEqual(y + height, floor + 1e-6)

    def test_roof_data_split_preserves_output_directions(self):
        root = previews.roof_preview()
        text = [node.text for node in root.iter() if node.tag.endswith("text")]
        self.assertIn("DATA SPLIT · LEFT GARAGE CORNER", text)
        split = root.find(".//*[@id='roof-data-split']")
        self.assertEqual((float(split.get("cx")), float(split.get("cy"))), previews.ROOF_SPLIT)
        presets = previews.load_json(previews.ROOT / "roof-line.json")
        segment_3 = next(s for s in presets["14"]["seg"] if s["id"] == 3)
        self.assertEqual(int(split.get("data-index")) - segment_3["start"], 63)
        pieces = {p.get("data-stop"): p for p in self.pieces(root)}, {p.get("data-start"): p for p in self.pieces(root)}
        before, after = pieces[0]["257"], pieces[1]["257"]
        point = "{:.3f},{:.3f}".format(*previews.ROOF_SPLIT)
        self.assertTrue(before.get("d").endswith(point))
        self.assertTrue(after.get("d").startswith(f"M {point}"))
        for output, direction in ((0, 1), (1, -1)):
            arrow = root.find(f".//*[@id='output-{output}-direction']")
            coordinates = [tuple(map(float, pair.split(","))) for pair in arrow.get("d").split() if "," in pair]
            self.assertGreater(direction * (coordinates[-1][0] - coordinates[0][0]), 0)
            self.assertEqual(arrow.get("marker-end"), "url(#data-arrow)")


if __name__ == "__main__":
    unittest.main()
