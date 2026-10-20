"""Load the fine-tuned model and classify one email. Used by the agent and the evals."""

from functools import lru_cache

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from common.config import CLASSIFIER_MODEL


class IntentClassifier:
    def __init__(self, model_dir=CLASSIFIER_MODEL):
        if not (model_dir / "config.json").exists():
            raise FileNotFoundError(
                f"No trained classifier at {model_dir}. Run: python 03_classifier/train.py"
            )
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).eval()
        self.labels = [self.model.config.id2label[i] for i in range(self.model.config.num_labels)]

    @torch.no_grad()
    def predict(self, text: str) -> tuple[str, float]:
        """Return (intent, confidence between 0 and 1)."""
        inputs = self.tokenizer(text, truncation=True, max_length=128, return_tensors="pt")
        probs = torch.softmax(self.model(**inputs).logits, dim=-1)[0]
        best = int(probs.argmax())
        return self.labels[best], float(probs[best])


@lru_cache
def get_classifier() -> IntentClassifier:
    """Load once, reuse everywhere."""
    return IntentClassifier()
