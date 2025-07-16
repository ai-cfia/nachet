import pytest
# import asyncio

from model.inference import (
    process_inference_results,
    primary_colors,
    light_colors,
    mixing_palettes,
    shades_colors,
    ProcessInferenceResultsModelAPIError,
)

@pytest.fixture
def setup_boxes():
    return {
        "box1": {
            "topX": 1,
            "topY": 1,
            "bottomX": 40,
            "bottomY": 40,
        },
        "box2": {
            "topX": 20,
            "topY": 20,
            "bottomX":60,
            "bottomY": 40,
        },
        "colors": mixing_palettes(primary_colors, light_colors)
    }

@pytest.mark.asyncio
async def test_process_inference_overlap_results(setup_boxes):
    boxes = [
        {"box": setup_boxes["box1"], "score": 20, "label": "box1"},
        {"box": setup_boxes["box2"], "score": 10, "label": "box2"}
    ]
    data = {
        "boxes": boxes,
        "totalBoxes": 2
    }
    result = await process_inference_results(data=[data], imageDims=[100, 100])

    assert not result[0]["boxes"][0]["overlapping"]
    assert result[0]["boxes"][1]["overlapping"]

@pytest.mark.asyncio
async def test_process_inference_overlap_score_results(setup_boxes):
    boxes = [
        {"box": setup_boxes["box1"], "score": 10, "label": "box1"},
        {"box": setup_boxes["box2"], "score": 10, "label": "box2"}
    ]
    data = {
        "boxes": boxes,
        "totalBoxes": 2
    }
    result = await process_inference_results(data=[data], imageDims=[100, 100])

    assert not result[0]["boxes"][0]["overlapping"]
    assert not result[0]["boxes"][1]["overlapping"]

@pytest.mark.asyncio
async def test_generate_color_hex(setup_boxes):
    boxes = [{"box": setup_boxes["box1"], "score": 10, "label": f"box{i}"} for i in range(2)]
    boxes.extend([{"box": setup_boxes["box2"], "score": 10, "label": f"box{i}"} for i in range(2)])
    boxes.sort(key=lambda x: x["label"])
    data = [{"boxes": boxes}]

    expected_result = set([c for i, c in enumerate(setup_boxes["colors"]["hex"][:len(boxes)]) if boxes[i]["label"] != boxes[i - 1]["label"]])

    result = await process_inference_results(data, [100, 100])
    color_res = set([box["color"] for box in result[0]["boxes"]])

    assert color_res == expected_result

@pytest.mark.asyncio
async def test_generate_color_rgb(setup_boxes):
    boxes = [{"box": setup_boxes["box1"], "score": 10, "label": f"box{i}"} for i in range(2)]
    boxes.extend([{"box": setup_boxes["box2"], "score": 10, "label": f"box{i}"} for i in range(2)])
    boxes.sort(key=lambda x: x["label"])
    data = [{"boxes": boxes}]

    expected_result = set(c for i, c in enumerate(setup_boxes["colors"]["rgb"][:len(boxes)]) if boxes[i]["label"] != boxes[i - 1]["label"])

    result = await process_inference_results(data, [100, 100], color_format="rgb")
    color_res = set([box["color"] for box in result[0]["boxes"]])

    assert color_res == expected_result

@pytest.mark.asyncio
async def test_boxes_over_available_colors(setup_boxes):
    # Create 36 different boxes
    boxes = [{"box": setup_boxes["box1"], "score": 10, "label": f"box{i}"} for i in range(len(setup_boxes["colors"]["hex"])*2)]
    data = [{"boxes": boxes}]

    expected_result = set(c for c in setup_boxes["colors"]["hex"][:len(boxes)])
    expected_result.update(set([shades_colors(c) for c in setup_boxes["colors"]["hex"]]))

    result = await process_inference_results(data, [100, 100])
    color_res = set([box["color"] for box in result[0]["boxes"]])

    assert color_res == expected_result

@pytest.mark.asyncio
async def test_process_inference_error(setup_boxes):
    boxes = [
        {"box": setup_boxes["box1"], "score": 10, "label": "box1"},
        {"box": setup_boxes["box2"], "score": 10, "label": "box2"}
    ]

    data = {
        "totalBoxes": 2
    }

    with pytest.raises(ProcessInferenceResultsModelAPIError):
        await process_inference_results(data=[data], imageDims=[100, 100])

    data ={
        "boxes": boxes,
        "totalBoxes": 2
    }

    with pytest.raises(ProcessInferenceResultsModelAPIError):
        await process_inference_results(data=[data], imageDims=100)

    data ={
        "boxes": None,
        "totalBoxes": 2
    }

    with pytest.raises(ProcessInferenceResultsModelAPIError):
        await process_inference_results(data=[data], imageDims=[100, 100])
