"""Image transforms from the existing classifier training script."""

# Adapted from HFTrainer_classifier_2026061801_js.py.
# The training and validation transforms retain the original settings.

import torch
from transformers import TimmWrapperImageProcessor
from torchvision.transforms.v2 import (
    CenterCrop,
    ColorJitter,
    Compose,
    GaussianBlur,
    Lambda,
    Normalize,
    # RandomAffine,
    # RandomResizedCrop,
    RandomHorizontalFlip,
    RandomGrayscale,
    # RandomEqualize,
    # RandomAutocontrast,
    RandomApply,
    RandomRotation,
    RandomVerticalFlip,
    Resize,
    # ToTensor,
    ToDtype,
    ToImage,
)


# Keep the historical augmentations separate so callers can supply alternatives.
def build_transforms(image_processor):
    if isinstance(image_processor, TimmWrapperImageProcessor):
        _train_transforms = image_processor.train_transforms
        _val_transforms = image_processor.val_transforms
    else:
        if "shortest_edge" in image_processor.size:
            size = image_processor.size["shortest_edge"]
        else:
            size = (image_processor.size["height"], image_processor.size["width"])

        # Create normalization transform
        if hasattr(image_processor, "image_mean") and hasattr(
            image_processor, "image_std"
        ):
            normalize = Normalize(
                mean=image_processor.image_mean, std=image_processor.image_std
            )
        else:
            normalize = Lambda(lambda x: x)
        _train_transforms = Compose(
            [
                RandomHorizontalFlip(p=0.3),
                RandomVerticalFlip(p=0.3),
                RandomRotation(degrees=(0, 360)),
                GaussianBlur(kernel_size=(5, 7), sigma=(0.1, 3.0)),
                RandomApply(transforms=[CenterCrop(size=size)], p=0.3),
                RandomApply(transforms=[CenterCrop(size=(192, 192))], p=0.3),
                Resize(size=size),
                ColorJitter(brightness=0.25, contrast=0.25, saturation=0.25),
                RandomGrayscale(p=0.20),
                # RandomAutocontrast(p=0.05),
                # RandomEqualize(p=0.05),
                # ToTensor(),
                ToImage(),
                ToDtype(torch.float32, scale=True),
                normalize,
            ]
        )
        _val_transforms = Compose(
            [
                Resize(size),
                CenterCrop(size),
                # ToTensor(),
                ToImage(),
                ToDtype(torch.float32, scale=True),
                normalize,
            ]
        )

    return _train_transforms, _val_transforms
