"""Display images and Matplotlib figures with lossless PNG downloads."""

from io import BytesIO

import streamlit as st


def download_image(image, filename, label="Download image (PNG)"):
    buffer = BytesIO()
    # PNG cannot encode CMYK and some floating-point Pillow modes.
    if image.mode not in ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"):
        image = image.convert("RGB")
    image.save(buffer, format="PNG")
    st.download_button(
        label, data=buffer.getvalue(), file_name=filename, mime="image/png",
        key=f"image_download_{filename}", on_click="ignore",
    )


def show_image(image, *, filename, caption=None, **kwargs):
    st.image(image, caption=caption, **kwargs)
    download_image(image, filename)


def show_figure(figure, *, filename):
    st.pyplot(figure)
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    st.download_button(
        "Download chart (PNG)", data=buffer.getvalue(), file_name=filename,
        mime="image/png", key=f"image_download_{filename}", on_click="ignore",
    )
