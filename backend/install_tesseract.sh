#!/usr/bin/env bash

set -e

echo "Installing Tesseract OCR..."

apt-get update

apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-tel

echo "Tesseract version:"
tesseract --version

echo "Installed OCR languages:"
tesseract --list-langs
