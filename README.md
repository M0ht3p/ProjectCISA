[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22816158.svg)](https://doi.org/10.5281/zenodo.22816158)

# 📸 Project CISA (Coordinate Image Search API)

An interactive [Streamlit](https://streamlit.io/) web application that extracts embedded EXIF metadata from uploaded JPEG and TIFF photos, performs reverse-geocoding using OpenStreetMap's Nominatim API, and renders interactive map markers alongside full camera shot details.

---

## ✨ Features

* **Automated EXIF Extraction:** Reads camera settings (Make, Model, Date/Time, ISO, Aperture, Shutter Speed, Focal Length).
* **GPS Coordinate Conversion:** Converts degree/minute/second EXIF GPS coordinates into decimal coordinates.
* **Reverse Geocoding:** Automatically queries OpenStreetMap (Nominatim API) to fetch human-readable addresses without needing an API key.
* **Interactive Map:** Displays photo locations as customizable markers on a [Folium](https://python-visualization.github.io/folium/) map centered on your photo uploads.
* **Detailed Photo Grid:** Clean layout showing side-by-side image previews with collapsible metadata cards.

---

## 🚀 Quick Start

### 1. Prerequisites

Make sure you have Python 3.8+ installed on your system.

### 2. Clone the Repository

```bash
git clone [https://github.com/M0ht3p/Project-CISA.git](https://github.com/M0ht3p/Project-CISA.git)
cd Project-CISA
```
### 3. Install dependencies
```bash
pip install streamlit pillow exifread geopy folium streamlit-folium
```
### 4. Run the Application
```bash
streamlit run app.py
```

📄 License : 
This project is licensed under the Apache 2.0 License ; see LICENSE file for more information.
