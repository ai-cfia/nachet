"""
This module provides functions to process the inference results from a given
pipelines.

It returns the processed inference results with additional information such as
overlapping boxes, label occurrence, and colors for each species found.

The colors can be returned in HEX or RGB format depending on the frontend preference.
"""

import numpy as np
from typing import TYPE_CHECKING

from .color_palette import primary_colors, light_colors, mixing_palettes, shades_colors
from .exceptions import ModelAPIError

if TYPE_CHECKING:
    from app.model.inference import EnhancedClassificationResult, ProcessedInferenceResult, ApiReadyInferenceResult

class ProcessInferenceResultsModelAPIError(ModelAPIError) :
    pass

def generator(list_length):
    for i in range(list_length):
        yield i


async def process_inference_results(
        data: dict,
        imageDims: 'list[int, int]',
        area_ratio: float = 0.5,
        color_format: str = "hex"
) -> dict:
    """
    Process the inference results by performing various operations on the data.
      Indicate if there are overlapping boxes and calculates the label
      occurrence. Boxes can overlap if their common area is greater than the
      area_ratio (default = 0.5) of the area of each box.

    Args:
        data (dict): The inference result data.
        imageDims (tuple): The dimensions of the image.
        area_ratio (float): The area ratio of a box to consider in the box
        overlap claculation.
        color_format (str): Specified the format representation of the color.
        Support hex and rgb.

    Returns:
        dict: The processed inference result data.

    Raises:
        ProcessInferenceResultError: If there is an error processing the
        inference results.
    """
    try:
        boxes = data[0]['boxes']
        colors = mixing_palettes(primary_colors, light_colors).get(color_format)

        # Perform operations on each box in the data
        for i, box in enumerate(boxes):
            # Set default overlapping attribute to false for each box
            boxes[i]["overlapping"] = False
            # Set default overlapping indices to empty array for each box
            boxes[i]["overlappingIndices"] = []

            # Perform calculations on box coordinates
            box["box"]["bottomX"] = int(
                np.clip(box["box"]["bottomX"] * imageDims[0], 5, imageDims[0] - 5)
            )
            box["box"]["bottomY"] = int(
                np.clip(box["box"]["bottomY"] * imageDims[1], 5, imageDims[1] - 5)
            )
            box["box"]["topX"] = int(
                np.clip(box["box"]["topX"] * imageDims[0], 5, imageDims[0] - 5)
            )
            box["box"]["topY"] = int(
                np.clip(box["box"]["topY"] * imageDims[1], 5, imageDims[1] - 5)
            )

        # Check if there are any overlapping boxes, if so, put the lower score
        # box in the overlapping key
        for i, box in enumerate(boxes):
            for j, box2 in enumerate(boxes):
                if j > i:
                    # Calculate the common region of the two boxes to determine
                    # if they are overlapping
                    area_box = (box["box"]["bottomX"] - box["box"]["topX"]) \
                                * (box["box"]["bottomY"] - box["box"]["topY"])
                    area_candidate = (box2["box"]["bottomX"] - box2["box"]["topX"]) \
                                    * (box2["box"]["bottomY"] - box2["box"]["topY"])

                    intersection_topX = max(
                        box["box"]["topX"], box2["box"]["topX"])
                    intersection_topY = max(
                        box["box"]["topY"], box2["box"]["topY"])
                    intersection_bottomX = min(
                        box["box"]["bottomX"], box2["box"]["bottomX"])
                    intersection_bottomY = min(
                        box["box"]["bottomY"], box2["box"]["bottomY"])

                    width = max(0, intersection_bottomX - intersection_topX)
                    height = max(0, intersection_bottomY - intersection_topY)

                    common_area = width * height

                    if common_area >= area_box * area_ratio \
                        and common_area >= area_candidate * area_ratio:
                        # box2 is the lower score box
                        if box2["score"] < box["score"]:
                            boxes[j]["overlapping"] = True
                            boxes[i]["overlappingIndices"].append(j + 1)
                            box2["box"]["bottomX"] = box["box"]["bottomX"]
                            box2["box"]["bottomY"] = box["box"]["bottomY"]
                            box2["box"]["topX"] = box["box"]["topX"]
                            box2["box"]["topY"] = box["box"]["topY"]
                        # box is the lower score box
                        elif box["score"] < box2["score"]:
                            boxes[i]["overlapping"] = True
                            boxes[i]["overlappingIndices"].append(j + 1)
                            box["box"]["bottomX"] = box2["box"]["bottomX"]
                            box["box"]["bottomY"] = box2["box"]["bottomY"]
                            box["box"]["topX"] = box2["box"]["topX"]
                            box["box"]["topY"] = box2["box"]["topY"]

        # Calculate label occurrence
        gen = generator(i) # Number of individual seed (boxes)
        label_occurrence = {}
        label_colors = {}
        for i, box in enumerate(boxes):
            if i >= len(colors):
                colors = colors + (shades_colors(colors[next(gen)]),)

            if box["label"] not in label_occurrence:
                label_occurrence[box["label"]] = 1
                label_colors[box["label"]] = colors[i]
                box["color"] = colors[i]
            else:
                label_occurrence[box["label"]] += 1
                color = label_colors[box["label"]]
                box["color"] = color

        data[0]["labelOccurrence"] = label_occurrence
        data[0]["totalBoxes"] = sum(1 for _ in data[0]["boxes"])

        return data

    except (KeyError, TypeError, IndexError, ValueError, ZeroDivisionError) as error:
        print(error)
        raise ProcessInferenceResultsModelAPIError(f"Error while processing inference results :\n {str(error)}") from error


async def process_enhanced_classification_result(
        result: "EnhancedClassificationResult",
        imageDims: list[int],
        area_ratio: float = 0.5,
        color_format: str = "hex"
) -> "ProcessedInferenceResult":
    """
    Process enhanced classification results using Pydantic models.
    
    This is a modernized version of process_inference_results that works with
    Pydantic models instead of raw dictionaries.
    
    Adds overlapping detection, colors, label occurrence, and converts normalized
    coordinates to pixel coordinates.
    
    Args:
        result: EnhancedClassificationResult with boxes and classifications
        imageDims: Image dimensions as [width, height]
        area_ratio: Area ratio threshold for overlapping detection (default 0.5)
        color_format: Color format - "hex" or "rgb"
        
    Returns:
        ProcessedInferenceResult with all post-processing applied
        
    Raises:
        ProcessInferenceResultsModelAPIError: If processing fails
    """
    try:
        from app.model.inference import ProcessedInferenceResult, ProcessedClassifiedBox, PixelBoundingBox
        
        colors = mixing_palettes(primary_colors, light_colors).get(color_format)
        
        # Create ProcessedClassifiedBox instances with converted coordinates
        processed_boxes: list[ProcessedClassifiedBox] = []
        for box in result.boxes:
            # Convert normalized coordinates (0.0-1.0) to pixel coordinates
            pixel_box = PixelBoundingBox(
                topX=int(np.clip(box.box.topX * imageDims[0], 5, imageDims[0] - 5)),
                topY=int(np.clip(box.box.topY * imageDims[1], 5, imageDims[1] - 5)),
                bottomX=int(np.clip(box.box.bottomX * imageDims[0], 5, imageDims[0] - 5)),
                bottomY=int(np.clip(box.box.bottomY * imageDims[1], 5, imageDims[1] - 5))
            )
            
            processed_boxes.append(ProcessedClassifiedBox(
                box=pixel_box,
                label=box.label,
                score=box.score,
                topN=box.topN,
                overlapping=False,
                overlappingIndices=[],
                color=""  # Will be assigned later
            ))
        
        # Detect overlapping boxes
        for i, box in enumerate(processed_boxes):
            for j, box2 in enumerate(processed_boxes):
                if j > i:
                    # Calculate box areas
                    area_box = (box.box.bottomX - box.box.topX) * (box.box.bottomY - box.box.topY)
                    area_candidate = (box2.box.bottomX - box2.box.topX) * (box2.box.bottomY - box2.box.topY)
                    
                    # Calculate intersection
                    intersection_topX = max(box.box.topX, box2.box.topX)
                    intersection_topY = max(box.box.topY, box2.box.topY)
                    intersection_bottomX = min(box.box.bottomX, box2.box.bottomX)
                    intersection_bottomY = min(box.box.bottomY, box2.box.bottomY)
                    
                    width = max(0, intersection_bottomX - intersection_topX)
                    height = max(0, intersection_bottomY - intersection_topY)
                    common_area = width * height
                    
                    # Check if boxes overlap significantly
                    if (common_area >= area_box * area_ratio and 
                        common_area >= area_candidate * area_ratio):
                        # Mark lower score box as overlapping
                        if box2.score < box.score:
                            processed_boxes[j].overlapping = True
                            processed_boxes[i].overlappingIndices.append(j + 1)
                            # Copy coordinates from higher score box
                            processed_boxes[j].box.bottomX = box.box.bottomX
                            processed_boxes[j].box.bottomY = box.box.bottomY
                            processed_boxes[j].box.topX = box.box.topX
                            processed_boxes[j].box.topY = box.box.topY
                        elif box.score < box2.score:
                            processed_boxes[i].overlapping = True
                            processed_boxes[i].overlappingIndices.append(j + 1)
                            # Copy coordinates from higher score box
                            processed_boxes[i].box.bottomX = box2.box.bottomX
                            processed_boxes[i].box.bottomY = box2.box.bottomY
                            processed_boxes[i].box.topX = box2.box.topX
                            processed_boxes[i].box.topY = box2.box.topY
        
        # Assign colors and calculate label occurrence
        gen = generator(len(processed_boxes))
        label_occurrence: dict[str, int] = {}
        label_colors: dict[str, str] = {}
        
        for i, box in enumerate(processed_boxes):
            # Extend color palette if needed
            if i >= len(colors):
                colors = colors + (shades_colors(colors[next(gen)]),)
            
            # Assign color and count occurrences
            if box.label not in label_occurrence:
                label_occurrence[box.label] = 1
                label_colors[box.label] = colors[i]
                box.color = colors[i]
            else:
                label_occurrence[box.label] += 1
                box.color = label_colors[box.label]
        
        # Return Pydantic model
        return ProcessedInferenceResult(
            boxes=processed_boxes,
            labelOccurrence=label_occurrence,
            totalBoxes=len(processed_boxes),
            filename=result.filename,
        )
        
    except (KeyError, TypeError, IndexError, ValueError, ZeroDivisionError) as error:
        print(error)
        raise ProcessInferenceResultsModelAPIError(
            f"Error while processing enhanced classification results:\n {str(error)}"
        ) from error


async def process_api_ready_classification_result(
        result: "EnhancedClassificationResult",
        imageDims: list[int],
        area_ratio: float = 0.5,
        color_format: str = "hex"
) -> "ApiReadyInferenceResult":
    """
    Process enhanced classification results for API response (maintains normalized coordinates).
    
    Similar to process_enhanced_classification_result but keeps coordinates in normalized
    form (0.0-1.0) for direct use in API responses. Performs overlapping detection using
    pixel coordinates but returns normalized coordinates.
    
    Args:
        result: EnhancedClassificationResult with boxes and classifications
        imageDims: Image dimensions as [width, height]
        area_ratio: Area ratio threshold for overlapping detection (default 0.5)
        color_format: Color format - "hex" or "rgb"
        
    Returns:
        ApiReadyInferenceResult with normalized coordinates and overlapping/color info
        
    Raises:
        ProcessInferenceResultsModelAPIError: If processing fails
    """
    try:
        from app.model.inference import ApiReadyInferenceResult, ApiInferenceBox
        import uuid
        
        colors = mixing_palettes(primary_colors, light_colors).get(color_format)
        
        # Store original boxes with normalized coordinates
        api_boxes: list[ApiInferenceBox] = []
        
        # Convert normalized coordinates to pixel coordinates for frontend rendering
        from app.model.inference import PixelBoundingBox
        
        for i, box in enumerate(result.boxes):
            # Convert normalized (0.0-1.0) coordinates to pixel coordinates
            pixel_box = PixelBoundingBox(
                topX=int(np.clip(box.box.topX * imageDims[0], 5, imageDims[0] - 5)),
                topY=int(np.clip(box.box.topY * imageDims[1], 5, imageDims[1] - 5)),
                bottomX=int(np.clip(box.box.bottomX * imageDims[0], 5, imageDims[0] - 5)),
                bottomY=int(np.clip(box.box.bottomY * imageDims[1], 5, imageDims[1] - 5))
            )
            
            # Create ApiInferenceBox with pixel coordinates for frontend
            api_boxes.append(ApiInferenceBox(
                box=pixel_box,
                label=box.label,
                score=box.score,
                topN=box.topN,
                classId=str(uuid.uuid4()),  # Generate unique ID for each box
                object_type_id="seed",  # Default object type for seed detection
                box_id=str(uuid.uuid4()),  # Generate unique box ID
                overlapping=False,  # Will be updated during overlap detection
                overlappingIndices=-1,  # -1 means no overlap, will be updated if overlap detected
                is_verified=False,  # Not verified initially
            ))
        
        # Detect overlapping boxes using pixel coordinates
        for i in range(len(api_boxes)):
            for j in range(i + 1, len(api_boxes)):
                box = api_boxes[i].box
                box2 = api_boxes[j].box
                
                # Calculate box areas
                area_box = (box.bottomX - box.topX) * (box.bottomY - box.topY)
                area_candidate = (box2.bottomX - box2.topX) * (box2.bottomY - box2.topY)
                
                # Calculate intersection
                intersection_topX = max(box.topX, box2.topX)
                intersection_topY = max(box.topY, box2.topY)
                intersection_bottomX = min(box.bottomX, box2.bottomX)
                intersection_bottomY = min(box.bottomY, box2.bottomY)
                
                width = max(0, intersection_bottomX - intersection_topX)
                height = max(0, intersection_bottomY - intersection_topY)
                common_area = width * height
                
                # Check if boxes overlap significantly
                if (common_area >= area_box * area_ratio and 
                    common_area >= area_candidate * area_ratio):
                    # Mark lower score box as overlapping
                    if api_boxes[j].score < api_boxes[i].score:
                        api_boxes[j].overlapping = True
                        api_boxes[j].overlappingIndices = i  # Store index of higher-score box
                        # Update pixel coordinates to match higher-score box
                        api_boxes[j].box.bottomX = api_boxes[i].box.bottomX
                        api_boxes[j].box.bottomY = api_boxes[i].box.bottomY
                        api_boxes[j].box.topX = api_boxes[i].box.topX
                        api_boxes[j].box.topY = api_boxes[i].box.topY
                    elif api_boxes[i].score < api_boxes[j].score:
                        api_boxes[i].overlapping = True
                        api_boxes[i].overlappingIndices = j  # Store index of higher-score box
                        # Update pixel coordinates to match higher-score box
                        api_boxes[i].box.bottomX = api_boxes[j].box.bottomX
                        api_boxes[i].box.bottomY = api_boxes[j].box.bottomY
                        api_boxes[i].box.topX = api_boxes[j].box.topX
                        api_boxes[i].box.topY = api_boxes[j].box.topY
        
        # Assign colors and calculate label occurrence
        gen = generator(len(api_boxes))
        label_occurrence: dict[str, int] = {}
        label_colors: dict[str, str] = {}
        
        for i, box in enumerate(api_boxes):
            # Extend color palette if needed
            if i >= len(colors):
                colors = colors + (shades_colors(colors[next(gen)]),)
            
            # Count label occurrences and assign colors
            if box.label not in label_occurrence:
                label_occurrence[box.label] = 1
                label_colors[box.label] = colors[i]
            else:
                label_occurrence[box.label] += 1
        
        # Return API-ready result
        return ApiReadyInferenceResult(
            boxes=api_boxes,
            labelOccurrence=label_occurrence,
            totalBoxes=len(api_boxes),
            filename=result.filename,
        )
        
    except (KeyError, TypeError, IndexError, ValueError, ZeroDivisionError) as error:
        print(error)
        raise ProcessInferenceResultsModelAPIError(
            f"Error while processing API-ready classification results:\n {str(error)}"
        ) from error

