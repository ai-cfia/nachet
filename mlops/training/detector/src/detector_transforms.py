"""Default image transforms for detector training and validation."""

import albumentations as A
from transformers.image_processing_utils import BaseImageProcessor


# ------------------------------------------------------------------------------------------------
# Define image augmentations and dataset transforms
# ------------------------------------------------------------------------------------------------

# Keep augmentation policy outside the shared trainer so callers can change it
# without duplicating the training flow.
def build_train_transform(
    image_processor: BaseImageProcessor,
    max_size: int,
) -> A.Compose:
    """Build the default detector training transforms."""
    return A.Compose(
        [
            # A.Compose(
            #     [
            #         A.SmallestMaxSize(max_size=max_size, p=1.0),
            #         A.RandomSizedBBoxSafeCrop(height=max_size, width=max_size, p=1.0),
            #     ],
            #     p=0.2,
            # ),
            # A.SmallestMaxSize(max_size=max_size, p=1.0),
            A.Perspective(p=0.1),
            A.HorizontalFlip(p=0.3),
            A.VerticalFlip(p=0.3),
            A.Rotate(360),
            A.OneOf(
                [
                    A.RandomBrightnessContrast(
                        brightness_limit=0.2, contrast_limit=0.2, p=1.0
                    ),
                    A.ColorJitter(
                        brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1, p=1.0
                    ),
                    A.CLAHE(clip_limit=4.0, tile_grid_size=(8, 8), p=1.0),
                ],
                p=0.5,
            ),
            A.OneOf(
                [
                    A.Blur(blur_limit=7, p=1),
                    A.MotionBlur(blur_limit=7, p=1),
                    A.Defocus(radius=(1, 5), alias_blur=(0.1, 0.25), p=1),
                ],
                p=0.2,
            ),
            # A.Resize(height=max_size, width=max_size),
            # A.CenterCrop(height=max_size, width=max_size),
            A.Normalize(mean=image_processor.image_mean, std=image_processor.image_std),
        ],
        bbox_params=A.BboxParams(
            format="coco", label_fields=["category"], clip=True, min_area=25
        ),
    )


def build_validation_transform(
    image_processor: BaseImageProcessor,
    max_size: int,
) -> A.Compose:
    """Build the default detector validation transforms."""
    return A.Compose(
        [
            # A.Resize(height=max_size, width=max_size),
            # A.CenterCrop(height=max_size, width=max_size),
            A.Normalize(mean=image_processor.image_mean, std=image_processor.image_std),
        ],
        bbox_params=A.BboxParams(format="coco", label_fields=["category"], clip=True),
    )
