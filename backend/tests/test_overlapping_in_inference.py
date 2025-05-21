import unittest
import asyncio

from model.inference import (
    process_inference_results,
    primary_colors,
    light_colors,
    mixing_palettes,
    shades_colors,
    ProcessInferenceResultsModelAPIError,
)

class TestInferenceProcessFunction(unittest.TestCase):
    def setUp(self):
        self.box1 = {
            "topX": 1,
            "topY": 1,
            "bottomX": 40,
            "bottomY": 40,
        }
        self.box2 = {
            "topX": 20,
            "topY": 20,
            "bottomX":60,
            "bottomY": 40,
        }
        self.colors = mixing_palettes(primary_colors, light_colors)

    def test_process_inference_overlap_results(self):
        boxes = [
            {"box": self.box1, "score": 20, "label": "box1"},
            {"box": self.box2, "score": 10, "label": "box2"}
        ]
        data = {
            "boxes": boxes,
            "totalBoxes": 2
        }
        result = asyncio.run(
            process_inference_results(data=[data], imageDims=[100, 100]))


        self.assertFalse(result[0]["boxes"][0]["overlapping"])
        self.assertTrue(result[0]["boxes"][1]["overlapping"])

    def test_process_inference_overlap_score_results(self):
        boxes = [
            {"box": self.box1, "score": 10, "label": "box1"},
            {"box": self.box2, "score": 10, "label": "box2"}
        ]
        data = {
            "boxes": boxes,
            "totalBoxes": 2
        }
        result = asyncio.run(
            process_inference_results(data=[data], imageDims=[100, 100]))


        self.assertFalse(result[0]["boxes"][0]["overlapping"])
        self.assertFalse(result[0]["boxes"][1]["overlapping"])

    def test_generate_color_hex(self):
        boxes = [{"box": self.box1, "score": 10, "label": f"box{i}"} for i in range(2)]
        boxes.extend([{"box": self.box2, "score": 10, "label": f"box{i}"} for i in range(2)])
        boxes.sort(key=lambda x: x["label"])
        data = [{"boxes": boxes}]

        expected_result = set([c for i, c in enumerate(self.colors["hex"][:len(boxes)]) if boxes[i]["label"] != boxes[i - 1]["label"]])

        result = asyncio.run(process_inference_results(data, [100, 100]))
        color_res = set([box["color"] for box in result[0]["boxes"]])

        self.assertEqual(color_res, expected_result)

    def test_generate_color_rgb(self):
        boxes = [{"box": self.box1, "score": 10, "label": f"box{i}"} for i in range(2)]
        boxes.extend([{"box": self.box2, "score": 10, "label": f"box{i}"} for i in range(2)])
        boxes.sort(key=lambda x: x["label"])
        data = [{"boxes": boxes}]

        expected_result = set(c for i, c in enumerate(self.colors["rgb"][:len(boxes)]) if boxes[i]["label"] != boxes[i - 1]["label"])

        result = asyncio.run(process_inference_results(data, [100, 100], color_format="rgb"))
        color_res = set([box["color"] for box in result[0]["boxes"]])

        self.assertEqual(color_res, expected_result)

    def test_boxes_over_available_colors(self):
        # Create 36 different boxes
        boxes = [{"box": self.box1, "score": 10, "label": f"box{i}"} for i in range(len(self.colors["hex"])*2)]
        data = [{"boxes": boxes}]

        expected_result = set(c for c in self.colors["hex"][:len(boxes)])
        expected_result.update(set([shades_colors(c) for c in self.colors["hex"]]))

        result = asyncio.run(process_inference_results(data, [100, 100]))
        color_res = set([box["color"] for box in result[0]["boxes"]])

        self.assertEqual(color_res, expected_result)

    def test_process_inference_error(self):
        boxes = [
            {"box": self.box1, "score": 10, "label": "box1"},
            {"box": self.box2, "score": 10, "label": "box2"}
        ]

        data = {
            "totalBoxes": 2
        }

        with self.assertRaises(ProcessInferenceResultsModelAPIError):
            asyncio.run(
                process_inference_results(data=[data], imageDims=[100, 100]))

        data ={
            "boxes": boxes,
            "totalBoxes": 2
        }

        with self.assertRaises(ProcessInferenceResultsModelAPIError):
            asyncio.run(process_inference_results(data=[data], imageDims=100))

        data ={
            "boxes": None,
            "totalBoxes": 2
        }

        with self.assertRaises(ProcessInferenceResultsModelAPIError):
            asyncio.run(
                process_inference_results(data=[data], imageDims=[100, 100]))
