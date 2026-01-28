"""
LightOnOCR-1B-1025 - PDF OCR Example
Extract text from PDF files using LightOn's OCR model.
"""

import torch
from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor
import pypdfium2 as pdfium
from PIL import Image
import sys
from pathlib import Path


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


def pdf_to_images(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
    """Convert PDF pages to PIL Images."""
    # Scale factor for desired DPI (72 is default PDF DPI)
    scale = dpi / 72

    pdf = pdfium.PdfDocument(pdf_path)
    images = []

    for i in range(len(pdf)):
        page = pdf[i]
        pil_image = page.render(scale=scale).to_pil()
        images.append(pil_image)

    return images


def run_ocr_on_image(model, processor, device, dtype, image: Image.Image) -> str:
    """Run OCR on a PIL Image."""
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

    output_ids = model.generate(**inputs, max_new_tokens=2048)
    generated_ids = output_ids[0, inputs["input_ids"].shape[1]:]
    output_text = processor.decode(generated_ids, skip_special_tokens=True)

    return output_text


def process_pdf(pdf_path: str, output_path: str | None = None, pages: list[int] | None = None):
    """Process a PDF file and extract text from all or specified pages."""
    model, processor, device, dtype = load_model()

    print(f"\nConverting PDF to images: {pdf_path}")
    images = pdf_to_images(pdf_path)
    print(f"Found {len(images)} pages")

    # Filter to specific pages if requested
    if pages:
        pages = [p for p in pages if 0 <= p < len(images)]
        images = [images[p] for p in pages]
        print(f"Processing pages: {pages}")

    all_text = []

    for i, image in enumerate(images):
        page_num = pages[i] + 1 if pages else i + 1
        print(f"\nProcessing page {page_num}/{len(images)}...")

        text = run_ocr_on_image(model, processor, device, dtype, image)
        all_text.append(f"--- Page {page_num} ---\n{text}")
        print(f"Page {page_num} complete")

    full_text = "\n\n".join(all_text)

    # Save to file if output path specified
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        print(f"\nOutput saved to: {output_path}")

    return full_text


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_ocr_pdf.py <pdf_path> [output_path] [page_numbers...]")
        print("  pdf_path: Path to the PDF file")
        print("  output_path: Optional path to save extracted text")
        print("  page_numbers: Optional specific pages to process (0-indexed)")
        print("\nExample:")
        print("  python run_ocr_pdf.py document.pdf")
        print("  python run_ocr_pdf.py document.pdf output.txt")
        print("  python run_ocr_pdf.py document.pdf output.txt 0 1 2  # First 3 pages")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    output_path = None
    pages = None

    if len(sys.argv) > 2:
        # Check if second arg is a page number or output path
        try:
            pages = [int(sys.argv[2])]
            pages.extend(int(x) for x in sys.argv[3:])
        except ValueError:
            output_path = sys.argv[2]
            if len(sys.argv) > 3:
                pages = [int(x) for x in sys.argv[3:]]

    result = process_pdf(pdf_path, output_path, pages)

    if not output_path:
        print("\n" + "=" * 50)
        print("EXTRACTED TEXT:")
        print("=" * 50)
        print(result)


if __name__ == "__main__":
    main()
