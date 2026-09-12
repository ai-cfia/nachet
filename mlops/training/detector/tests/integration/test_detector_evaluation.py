"""Offline evaluation checks using the trainer image's real dependencies."""

import tempfile
import unittest

import numpy as np
import torch
from PIL import Image
from transformers import (
    RTDetrImageProcessor,
    RTDetrResNetConfig,
    RTDetrV2Config,
    RTDetrV2ForObjectDetection,
    TrainingArguments,
)

from train_detector import DetectionEvaluationTrainer, collate_fn, compute_metrics


class DetectorEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(2438)
        cls.processor = RTDetrImageProcessor(size={"height": 64, "width": 64})

    def model(self):
        # Exercise real detection loss and metrics without downloading weights.
        backbone = RTDetrResNetConfig(
            embedding_size=16,
            hidden_sizes=[16, 32, 64, 128],
            depths=[1, 1, 1, 1],
            layer_type="basic",
            out_indices=[2, 3, 4],
        )
        config = RTDetrV2Config(
            backbone_config=backbone,
            encoder_in_channels=[32, 64, 128],
            encoder_hidden_dim=32,
            encoder_ffn_dim=64,
            encoder_attention_heads=4,
            d_model=32,
            decoder_in_channels=[32, 32, 32],
            decoder_ffn_dim=64,
            decoder_attention_heads=4,
            decoder_layers=2,
            num_queries=10,
            num_denoising=0,
            num_labels=1,
        )
        return RTDetrV2ForObjectDetection(config)

    def dataset(self, size):
        records = []
        for index in range(size):
            image = Image.fromarray(
                np.full((64 + index, 80 + index, 3), 50 + index, dtype=np.uint8)
            )
            annotations = [
                {
                    "bbox": [5 + box, 6 + box, 10, 12],
                    "category_id": 0,
                    "area": 120,
                    "iscrowd": 0,
                }
                for box in range(0 if index == 0 else 5 + index % 3)
            ]
            encoded = self.processor(
                images=image,
                annotations={"image_id": index, "annotations": annotations},
                return_tensors="pt",
            )
            records.append(
                {"pixel_values": encoded.pixel_values[0], "labels": encoded.labels[0]}
            )
        return records

    def test_batches_preserve_annotations_and_compute_metrics(self):
        # Distinct sizes and unequal box counts expose coordinate truncation,
        # lost annotations, and image-order changes in full and partial batches.
        for size, batch_size in ((1, 2), (2, 2), (3, 2), (5, 3), (9, 8)):
            with self.subTest(
                size=size, batch_size=batch_size
            ), tempfile.TemporaryDirectory() as output:
                dataset = self.dataset(size)

                def verify(result):
                    self.assertEqual(len(result.predictions), len(result.label_ids))
                    image_index = 0
                    for predictions, labels in zip(
                        result.predictions, result.label_ids
                    ):
                        counts = labels["box_count"][:, 0]
                        self.assertEqual(len(predictions[1]), len(counts))
                        self.assertEqual(len(predictions[2]), len(counts))
                        for index, count in enumerate(counts):
                            expected = dataset[image_index]["labels"]
                            self.assertEqual(count, len(expected["boxes"]))
                            np.testing.assert_array_equal(
                                labels["orig_size"][index], expected["orig_size"]
                            )
                            np.testing.assert_array_equal(
                                labels["boxes"][index, :count], expected["boxes"]
                            )
                            np.testing.assert_array_equal(
                                labels["class_labels"][index, :count],
                                expected["class_labels"],
                            )
                            image_index += 1
                    self.assertEqual(image_index, size)
                    return compute_metrics(result, self.processor, id2label={0: "seed"})

                trainer = DetectionEvaluationTrainer(
                    model=self.model(),
                    args=TrainingArguments(
                        output_dir=output,
                        use_cpu=True,
                        report_to=[],
                        disable_tqdm=True,
                        remove_unused_columns=False,
                        eval_do_concat_batches=False,
                        per_device_eval_batch_size=batch_size,
                        dataloader_pin_memory=False,
                    ),
                    data_collator=collate_fn,
                    compute_metrics=verify,
                    eval_dataset=dataset,
                )
                for _ in range(2):
                    metrics = trainer.evaluate()
                    self.assertTrue(np.isfinite(metrics["eval_loss"]))
                    self.assertIn("eval_map", metrics)
                    trainer.predict(dataset)

    def test_incompatible_gather_options_are_rejected(self):
        for options in (
            {"eval_do_concat_batches": True},
            {"eval_use_gather_object": True},
        ):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as output:
                arguments = {"eval_do_concat_batches": False, **options}
                with self.assertRaisesRegex(ValueError, "detector evaluation requires"):
                    DetectionEvaluationTrainer(
                        model=self.model(),
                        args=TrainingArguments(
                            output_dir=output, use_cpu=True, report_to=[], **arguments
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
