"""Chapter 3b: fine-tune DistilBERT to classify emails into 6 intents.

A plain PyTorch training loop, so you can see every step:
tokenize -> forward pass -> loss -> backward -> optimizer step.

Run:  python 03_classifier/train.py --epochs 1
Saves the model to artifacts/intent_model/ and prints val/test accuracy.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import torch  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402
from transformers import AutoModelForSequenceClassification, AutoTokenizer  # noqa: E402

from common.config import BASE_ENCODER, CLASSIFIER_DATA, CLASSIFIER_MODEL, INTENTS  # noqa: E402

LABEL_TO_ID = {label: i for i, label in enumerate(INTENTS)}


def load_split(name: str) -> list[dict]:
    with open(CLASSIFIER_DATA / f"{name}.jsonl") as f:
        return [json.loads(line) for line in f]


def pick_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")  # Apple Silicon GPU
    return torch.device("cpu")


def make_loader(rows, tokenizer, batch_size, shuffle):
    def collate(batch):
        enc = tokenizer([r["text"] for r in batch], truncation=True, max_length=128, padding=True, return_tensors="pt")
        enc["labels"] = torch.tensor([LABEL_TO_ID[r["label"]] for r in batch])
        return enc
    return DataLoader(rows, batch_size=batch_size, shuffle=shuffle, collate_fn=collate)


@torch.no_grad()
def accuracy(model, loader, device) -> float:
    model.eval()
    correct = total = 0
    for batch in loader:
        batch = {k: v.to(device) for k, v in batch.items()}
        preds = model(**batch).logits.argmax(dim=-1)
        correct += (preds == batch["labels"]).sum().item()
        total += len(preds)
    return correct / total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5e-5)
    args = parser.parse_args()

    torch.manual_seed(0)
    device = pick_device()
    tokenizer = AutoTokenizer.from_pretrained(BASE_ENCODER)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_ENCODER, num_labels=len(INTENTS),
        id2label=dict(enumerate(INTENTS)), label2id=LABEL_TO_ID,
    ).to(device)

    train_loader = make_loader(load_split("train"), tokenizer, args.batch_size, shuffle=True)
    val_loader = make_loader(load_split("val"), tokenizer, 64, shuffle=False)
    test_loader = make_loader(load_split("test"), tokenizer, 64, shuffle=False)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    print(f"Training {BASE_ENCODER} on {len(train_loader.dataset)} emails, device={device}, epochs={args.epochs}")
    start = time.time()
    for epoch in range(args.epochs):
        model.train()
        for step, batch in enumerate(train_loader):
            batch = {k: v.to(device) for k, v in batch.items()}
            loss = model(**batch).loss          # cross-entropy over the 6 intents
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            if step % 20 == 0:
                print(f"  epoch {epoch + 1} step {step:>3}/{len(train_loader)} loss {loss.item():.4f}")
        print(f"epoch {epoch + 1}: val accuracy {accuracy(model, val_loader, device):.3f}")

    test_acc = accuracy(model, test_loader, device)
    minutes = (time.time() - start) / 60
    print(f"test accuracy (synthetic, same templates): {test_acc:.3f}  | training time {minutes:.1f} min")
    print("The honest test is on hand-written emails: python 03_classifier/eval_vs_llm.py")

    model.to("cpu").save_pretrained(CLASSIFIER_MODEL)
    tokenizer.save_pretrained(CLASSIFIER_MODEL)
    (CLASSIFIER_MODEL / "train_info.json").write_text(json.dumps(
        {"base": BASE_ENCODER, "epochs": args.epochs, "synthetic_test_accuracy": round(test_acc, 4),
         "train_minutes": round(minutes, 2), "device": str(device)}, indent=2))
    print(f"Saved to {CLASSIFIER_MODEL}")


if __name__ == "__main__":
    main()
