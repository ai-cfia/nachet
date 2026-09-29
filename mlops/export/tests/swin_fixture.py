"""The same small saved Swin checkpoint and pixels for both export stages."""


def create_swin_fixture(root):
    import numpy as np
    import torch
    from PIL import Image
    from transformers import SwinConfig, SwinForImageClassification, ViTImageProcessor

    torch.manual_seed(42)
    torch.set_num_threads(1)
    model = SwinForImageClassification(SwinConfig(
        image_size=32, patch_size=4, embed_dim=8, depths=[1, 1],
        num_heads=[1, 2], window_size=2, num_labels=3,
        id2label={0: "Beta", 1: "Alpha", 2: "Gamma"},
        label2id={"Beta": 0, "Alpha": 1, "Gamma": 2},
    )).eval()
    processor = ViTImageProcessor(size={"height": 32, "width": 32})
    checkpoint = root / "checkpoint"
    model.save_pretrained(checkpoint)
    processor.save_pretrained(checkpoint)
    image = Image.fromarray(np.random.default_rng(42).integers(
        0, 256, size=(48, 40, 3), dtype=np.uint8,
    ))
    pixels = processor(images=image, return_tensors="pt")["pixel_values"]
    return model, checkpoint, pixels
