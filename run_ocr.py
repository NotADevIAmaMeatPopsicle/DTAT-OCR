"""
LightOnOCR-1B-1025 - OCR Model Example
Run OCR on images or PDFs using LightOn's OCR model.
"""

import torch
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
from PIL import Image
import requests
from io import BytesIO
import sys


def get_device_and_dtype():
    """Determine the best available device and dtype."""
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    elif torch.backends.mps.is_available():
        return "mps", torch.float32
    else:
        return "cpu", torch.float32


def load_model():
    """Load the LightOnOCR model and processor."""
    device, dtype = get_device_and_dtype()
    print(f"Using device: {device}, dtype: {dtype}")

    print("Loading model (this may take a while on first run)...")
    model = LightOnOcrForConditionalGeneration.from_pretrained(
        "lightonai/LightOnOCR-1B-1025",
        torch_dtype=dtype
    ).to(device)

    processor = LightOnOcrProcessor.from_pretrained("lightonai/LightOnOCR-1B-1025")

    return model, processor, device, dtype


def run_ocr_on_url(model, processor, device, dtype, image_url: str) -> str:
    """Run OCR on an image URL."""
    conversation = [{"role": "user", "content": [{"type": "image", "url": image_url}]}]

    inputs = processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = {
        k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device)
        for k, v in inputs.items()
    }

    output_ids = model.generate(**inputs, max_new_tokens=1024)
    generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
    output_text = processor.decode(generated_ids, skip_special_tokens=True)

    return output_text


def run_ocr_on_image(model, processor, device, dtype, image_path: str) -> str:
    """Run OCR on a local image file."""
    image = Image.open(image_path)

    # Resize to recommended max dimension (1540px longest side)
    max_dim = 1540
    if max(image.size) > max_dim:
        ratio = max_dim / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    conversation = [{"role": "user", "content": [{"type": "image", "image": image}]}]

    inputs = processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = {
        k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device)
        for k, v in inputs.items()
    }

    output_ids = model.generate(**inputs, max_new_tokens=1024)
    generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
    output_text = processor.decode(generated_ids, skip_special_tokens=True)

    return output_text


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_ocr.py <image_path_or_url>")
        print("\nExamples:")
        print("  python run_ocr.py samples/receipt_asprise.jpg")
        print("  python run_ocr.py https://example.com/image.jpg")
        sys.exit(1)

    target = sys.argv[1]

    model, processor, device, dtype = load_model()

    # Check if it's a URL or local file
    if target.startswith("http://") or target.startswith("https://"):
        print(f"\n--- Running OCR on URL: {target} ---\n")
        result = run_ocr_on_url(model, processor, device, dtype, target)
    else:
        print(f"\n--- Running OCR on file: {target} ---\n")
        result = run_ocr_on_image(model, processor, device, dtype, target)

    print("OCR Result:")
    print("-" * 40)
    print(result)
    print("-" * 40)


if __name__ == "__main__":
    main()
