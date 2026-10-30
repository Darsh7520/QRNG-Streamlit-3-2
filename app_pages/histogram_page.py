import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app_pages.image_downloads import show_image, show_figure
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from PIL import Image, UnidentifiedImageError


def render():
    st.title("🖼️ Pixel Intensity Histogram")
    st.markdown(
        "Upload an image to see how its pixel values are distributed. "
        "Grayscale intensity uses Pillow's luminance conversion; RGB mode "
        "shows the red, green, and blue channels separately."
    )

    uploaded = st.file_uploader(
        "Upload an image",
        type=["png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"],
    )

    if uploaded is None:
        st.info("Upload an image to generate its histogram.")
        return

    try:
        with Image.open(uploaded) as source:
            source.load()
            image = source.copy()
    except (UnidentifiedImageError, OSError, ValueError):
        st.error("The uploaded file could not be read as an image.")
        return

    grayscale_pixels = np.asarray(image.convert("L"))
    preview, details = st.columns([1.2, 1])
    with preview:
        show_image(image, caption="Image preview", width="stretch", filename='histogram_source.png')
    with details:
        st.subheader("Image details")
        st.metric("File name", uploaded.name)
        st.metric("Dimensions", f"{image.width} × {image.height} px")
        st.metric("Mean intensity", f"{grayscale_pixels.mean():.2f} / 255")

    histogram_type = st.radio(
        "Histogram type",
        ["Grayscale intensity", "RGB channels"],
        horizontal=True,
    )

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.set_box_aspect(1)
    levels = np.arange(256)
    if histogram_type == "Grayscale intensity":
        counts = np.bincount(grayscale_pixels.ravel(), minlength=256)
        # Bars, not a line: each intensity level is a separate count, and a
        # line would draw a misleading slope between isolated spikes.
        ax.bar(levels, counts, width=1.0, color="#555555", edgecolor="#555555")
        ax.axvline(grayscale_pixels.mean(), color="#e45756", linestyle="--",
                   linewidth=1.2, label=f"Mean = {grayscale_pixels.mean():.1f}")
        ax.legend()
        ax.set_ylabel("Pixel count")
        ax.set_title("Grayscale Pixel Intensity")
    else:
        pixels = np.asarray(image.convert("RGB"))
        for channel, color in enumerate(("red", "green", "blue")):
            counts = np.bincount(pixels[:, :, channel].ravel(), minlength=256)
            ax.bar(levels, counts, width=1.0, color=color, alpha=0.45,
                   label=color.title())
        ax.set_ylabel("Pixel count")
        ax.set_title("RGB Channel Intensities")
        ax.legend()

    ax.set_xlabel("Intensity value (0 = black, 255 = white)")
    ax.set_xlim(-2, 257)
    ax.set_xticks(list(range(0, 256, 32)) + [255])
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    show_figure(fig, filename='pixel_intensity_histogram.png')
    plt.close(fig)


if __name__ == "__main__":
    st.set_page_config(page_title="Pixel Intensity Histogram")
    render()