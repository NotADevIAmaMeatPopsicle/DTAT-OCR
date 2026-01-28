"""
Download sample OCR test images from various public sources.
Focused on English/American documents.
"""

import requests
from pathlib import Path
import time

# Create samples directory
SAMPLES_DIR = Path(__file__).parent / "samples"
SAMPLES_DIR.mkdir(exist_ok=True)

# English/American focused OCR test samples
SAMPLE_IMAGES = {
    # === RECEIPTS (English) ===
    "receipt_sroie.jpg": "https://huggingface.co/datasets/hf-internal-testing/fixtures_ocr/resolve/main/SROIE-receipt.jpeg",
    "receipt_asprise.jpg": "https://raw.githubusercontent.com/Asprise/receipt-ocr/main/receipt.jpg",
    "receipt_mistral.png": "https://raw.githubusercontent.com/mistralai/cookbook/refs/heads/main/mistral/ocr/receipt.png",

    # === NUTRITION LABEL / PRINTED TEXT ===
    "nutrition_label.jpg": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/printed_text.jpg",

    # === HANDWRITTEN ENGLISH ===
    "handwritten_eng.png": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/handwritten_text.jpg",

    # === BUSINESS DOCUMENTS ===
    "business_card.jpg": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/business_card.jpg",

    # === INVOICES ===
    "invoice_sample.png": "https://raw.githubusercontent.com/mindee/doctr/main/docs/images/example.png",

    # === SCENE TEXT (English signs) ===
    "street_sign.jpg": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/doc/imgs_en/img_12.jpg",
    "store_sign.jpg": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/doc/imgs_en/img623.jpg",

    # === TYPED DOCUMENTS ===
    "typed_document.jpg": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/doc/imgs_en/254.jpg",

    # === DENSE TEXT ===
    "dense_text.jpg": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/ppstructure/docs/table/example_image.jpg",

    # === TABLES ===
    "table_document.jpg": "https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/ppstructure/docs/table/paper-image.jpg",

    # === FORMS ===
    "form_document.png": "https://raw.githubusercontent.com/clovaai/donut/master/misc/sample_image_cord_test_receipt_00004.png",
}

def download_image(url: str, filename: str) -> bool:
    """Download an image from URL to samples directory."""
    filepath = SAMPLES_DIR / filename

    if filepath.exists():
        print(f"  [SKIP] {filename} (already exists)")
        return True

    try:
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        response.raise_for_status()

        # Check if it's actually an image (not HTML error page)
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type.lower() and len(response.content) < 10000:
            print(f"  [FAIL] {filename}: Got HTML instead of image")
            return False

        filepath.write_bytes(response.content)
        size_kb = len(response.content) / 1024
        print(f"  [OK] {filename} ({size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"  [FAIL] {filename}: {type(e).__name__}")
        return False


def main():
    print(f"Downloading English OCR samples to: {SAMPLES_DIR}\n")
    print("Categories:")
    print("  - Receipts (3 samples)")
    print("  - Nutrition labels / Printed text")
    print("  - Handwritten English")
    print("  - Business documents")
    print("  - Invoices")
    print("  - Street/store signs")
    print("  - Tables and forms")
    print()

    success = 0
    failed = 0

    for filename, url in SAMPLE_IMAGES.items():
        if download_image(url, filename):
            success += 1
        else:
            failed += 1
        time.sleep(0.3)

    print(f"\n{'='*50}")
    print(f"Done! {success} downloaded, {failed} failed")
    print(f"{'='*50}")

    print(f"\nTo run OCR:")
    print(f"  python run_ocr.py samples/<filename>")

    print(f"\nAvailable English samples:")
    for f in sorted(SAMPLES_DIR.glob("*")):
        if f.is_file() and f.suffix.lower() in ['.jpg', '.png', '.jpeg']:
            size = f.stat().st_size / 1024
            print(f"  - {f.name} ({size:.1f} KB)")

    # Check for PDF
    pdfs = list(SAMPLES_DIR.glob("*.pdf"))
    if pdfs:
        print(f"\nPDF samples:")
        for f in pdfs:
            size = f.stat().st_size / 1024
            print(f"  - {f.name} ({size:.1f} KB)")


if __name__ == "__main__":
    main()
