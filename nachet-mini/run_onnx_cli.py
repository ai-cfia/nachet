from pathlib import Path
import argparse
import numpy as np
from PIL import Image
import onnxruntime as ort
import cv2

DETECTION_MODEL_PATH = "model.onnx"
IMAGE_PATH = "test-image.png"

MODEL_W = 640
MODEL_H = 640
THRESHOLD = 0.5
DISPLAY_SCALE = 2.0


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def decode_outputs(logits, pred_boxes, img_w, img_h, threshold=0.5):
    # logits: (1, 300, 1)
    # pred_boxes: (1, 300, 4) normalized cxcywh
    scores = logits[0, :, 0]
    boxes = pred_boxes[0]

    # Only sigmoid if scores look like raw logits.
    if scores.min() < 0.0 or scores.max() > 1.0:
        scores = sigmoid(scores)

    keep = scores > threshold
    scores = scores[keep]
    boxes = boxes[keep]

    # normalized cxcywh -> pixel xyxy
    cx = boxes[:, 0] * img_w
    cy = boxes[:, 1] * img_h
    w = boxes[:, 2] * img_w
    h = boxes[:, 3] * img_h

    x1 = cx - w / 2
    y1 = cy - h / 2
    x2 = cx + w / 2
    y2 = cy + h / 2

    boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1)
    return boxes_xyxy, scores


def parse_args():
    parser = argparse.ArgumentParser(description="Run ONNX object detection")
    parser.add_argument("--detector-model", default=DETECTION_MODEL_PATH)
    parser.add_argument("--image", default=IMAGE_PATH)
    parser.add_argument("--threshold", type=float, default=THRESHOLD)
    parser.add_argument("--display-scale", type=float, default=DISPLAY_SCALE)
    return parser.parse_args()


def main():
    args = parse_args()
    providers = ["CPUExecutionProvider"]

    if not Path(args.detector_model).exists():
        raise FileNotFoundError(f"Detector model not found: {args.detector_model}")

    if not Path(args.image).exists():
        raise FileNotFoundError(f"Image not found: {args.image}")

    detector_session = ort.InferenceSession(args.detector_model, providers=providers)

    print("Inputs:")
    for inp in detector_session.get_inputs():
        print(inp.name, inp.shape, inp.type)

    print("\nOutputs:")
    for out in detector_session.get_outputs():
        print(out.name, out.shape, out.type)

    # Load original image.
    pil_img = Image.open(args.image).convert("RGB")
    orig_w, orig_h = pil_img.size

    # Resize for model input and convert HWC -> CHW.
    model_img = pil_img.resize((MODEL_W, MODEL_H))
    x = np.asarray(model_img).astype(np.float32) / 255.0
    x = np.transpose(x, (2, 0, 1))
    x = np.expand_dims(x, axis=0)

    input_name = detector_session.get_inputs()[0].name
    outputs = detector_session.run(None, {input_name: x})
    
    print("\n", outputs)
    decoded_boxes, scores = decode_outputs(
        outputs[0],
        outputs[1],
        MODEL_W,
        MODEL_H,
        threshold=args.threshold,
    )

    for i, out in enumerate(outputs):
        print(f"Output {i}: shape={np.array(out).shape}")

    print("\nDecoded boxes in 640x640 model space:")
    for i, (box, score) in enumerate(zip(decoded_boxes, scores)):
        print(f"Box {i}: {box}, Score: {score:.4f}")

    # Load original image with OpenCV for drawing.
    img = cv2.imread(args.image)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    # Scale decoded boxes from model space (640x640) to original image size.
    scale_to_orig_x = orig_w / MODEL_W
    scale_to_orig_y = orig_h / MODEL_H

    boxes_on_original = []
    for box in decoded_boxes:
        x1, y1, x2, y2 = box
        boxes_on_original.append(
            [
                x1 * scale_to_orig_x,
                y1 * scale_to_orig_y,
                x2 * scale_to_orig_x,
                y2 * scale_to_orig_y,
            ]
        )

    # Enlarge original image for display.
    display_w = int(orig_w * args.display_scale)
    display_h = int(orig_h * args.display_scale)
    img_big = cv2.resize(img, (display_w, display_h), interpolation=cv2.INTER_LINEAR)

    # Scale original-image boxes to display-image boxes.
    scaled_boxes = []
    for box in boxes_on_original:
        x1, y1, x2, y2 = box
        scaled_boxes.append(
            [
                x1 * args.display_scale,
                y1 * args.display_scale,
                x2 * args.display_scale,
                y2 * args.display_scale,
            ]
        )

    for box, score in zip(scaled_boxes, scores):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(img_big, (x1, y1), (x2, y2), (255, 0, 255), 4)

        label_text = f"det:{score:.2f}"

        text_y = max(y1 - 8, 20)
        cv2.putText(
            img_big,
            label_text,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 255),
            2,
        )

    cv2.namedWindow("detections", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("detections", min(display_w, 1600), min(display_h, 1200))
    cv2.imshow("detections", img_big)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
