from __future__ import annotations

import argparse
import os
import random
import re
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset, DatasetDict
from sklearn.metrics import accuracy_score, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

LABEL_NAMES = ["very negative", "negative", "neutral", "positive", "very positive"]


def parse_sst_tree(tree: str) -> tuple[str, int]:
    root_match = re.match(r"^\s*\(([0-4])\s", tree)
    if not root_match:
        raise ValueError(f"Invalid SST root: {tree[:60]!r}")

    leaf_tokens = re.findall(r"\([0-4]\s+([^()]+?)\)", tree)
    if not leaf_tokens:
        raise ValueError(f"No leaf tokens found: {tree[:60]!r}")

    text = " ".join(token.strip().replace(r"\/", "/") for token in leaf_tokens)
    text = text.replace("`` ", '"').replace(" ''", '"')
    text = re.sub(r"\s+([,.;:!?%\)])", r"\1", text)
    text = re.sub(r"([\(\[\{])\s+", r"\1", text)
    text = re.sub(r"\s+'\s*", "'", text)
    return text, int(root_match.group(1))


def load_sst_file(path: Path) -> list[dict[str, object]]:
    records = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            text, label = parse_sst_tree(raw_line)
        except ValueError as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
        records.append({"text": text, "label": label})
    return records


def summarize_labels(records: list[dict[str, object]]) -> dict[str, int]:
    counts = Counter(int(record["label"]) for record in records)
    return {LABEL_NAMES[label_id]: counts[label_id] for label_id in range(len(LABEL_NAMES))}


def compute_metrics(eval_prediction) -> dict[str, float]:
    logits, labels = eval_prediction
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "macro_f1": f1_score(labels, predictions, average="macro"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune BERT on Stanford Sentiment Treebank.")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "dataset")
    parser.add_argument("--model-name", default=os.getenv("MODEL_NAME", "bert-base-uncased"))
    parser.add_argument("--output-dir", type=Path, default=Path(os.getenv("OUTPUT_DIR", "bert-sst5-output")))
    parser.add_argument("--max-length", type=int, default=int(os.getenv("MAX_LENGTH", "128")))
    parser.add_argument("--epochs", type=float, default=float(os.getenv("NUM_EPOCHS", "3")))
    parser.add_argument("--train-batch-size", type=int, default=int(os.getenv("TRAIN_BATCH_SIZE", "64")))
    parser.add_argument("--eval-batch-size", type=int, default=int(os.getenv("EVAL_BATCH_SIZE", "128")))
    parser.add_argument("--gradient-accumulation-steps", type=int, default=int(os.getenv("GRADIENT_ACCUMULATION_STEPS", "1")))
    parser.add_argument("--learning-rate", type=float, default=float(os.getenv("LEARNING_RATE", "2e-5")))
    parser.add_argument("--seed", type=int, default=int(os.getenv("SEED", "42")))
    parser.add_argument("--workers", type=int, default=int(os.getenv("DATALOADER_WORKERS", "4")))
    parser.add_argument("--resume", action="store_true", help="Resume from the latest checkpoint in output-dir.")
    parser.add_argument("--dry-run", action="store_true", help="Validate data, model download, and tokenization without training.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Run this training job on the Azure H100 VM.")
    torch.cuda.manual_seed_all(args.seed)

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GiB")
    print(f"PyTorch: {torch.__version__}; CUDA: {torch.version.cuda}")

    train_records = load_sst_file(args.data_dir / "train.txt")
    dev_records = load_sst_file(args.data_dir / "dev.txt")
    print(f"Train records: {len(train_records):,} {summarize_labels(train_records)}")
    print(f"Dev records: {len(dev_records):,} {summarize_labels(dev_records)}")

    raw_datasets = DatasetDict(
        train=Dataset.from_list(train_records),
        validation=Dataset.from_list(dev_records),
    )
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    def tokenize_batch(batch: dict[str, list[str]]) -> dict[str, list[list[int]]]:
        return tokenizer(
            batch["text"],
            truncation=True,
            padding=False,
            max_length=args.max_length,
        )

    tokenized_datasets = raw_datasets.map(
        tokenize_batch,
        batched=True,
        remove_columns=["text"],
    )
    print(f"Tokenized first example length: {len(tokenized_datasets['train'][0]['input_ids'])}")

    id_to_label = dict(enumerate(LABEL_NAMES))
    label_to_id = {label: index for index, label in id_to_label.items()}
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL_NAMES),
        id2label=id_to_label,
        label2id=label_to_id,
    )

    if args.dry_run:
        print("Dry run completed successfully; training was not started.")
        return

    supports_bf16 = torch.cuda.is_bf16_supported()
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.train_batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        weight_decay=float(os.getenv("WEIGHT_DECAY", "0.01")),
        warmup_steps=float(os.getenv("WARMUP_RATIO", "0.1")),
        bf16=supports_bf16,
        fp16=not supports_bf16,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="steps",
        logging_steps=int(os.getenv("LOGGING_STEPS", "25")),
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        save_total_limit=2,
        report_to="none",
        dataloader_num_workers=args.workers,
        seed=args.seed,
        data_seed=args.seed,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        processing_class=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )
    trainer.train(resume_from_checkpoint=True if args.resume else None)
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    print("Final validation metrics:", trainer.evaluate())


if __name__ == "__main__":
    main()
