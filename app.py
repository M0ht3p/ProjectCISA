import streamlit as st
import exifread
from PIL import Image, ExifTags
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import folium
from streamlit_folium import st_folium
import io

st.set_page_config(
    page_title="Project CISA",
    page_icon="📸",
    layout="wide"
)

st.title("📸 Project CISA")
st.markdown(
    "Upload one or more photos (JPEG/TIFF) containing GPS EXIF metadata. "
    "The app will extract location coordinates, perform reverse-geocoding, and map the photos!"
)

@st.cache_resource
def get_geocoder():
    return Nominatim(user_agent="project_cisa_streamlit_app")

geolocator = get_geocoder()


def convert_to_degrees(value):
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)
    return d + (m / 60.0) + (s / 3600.0)


def extract_exif_data(file_bytes):
    tags = exifread.process_file(file_bytes, details=False)
    
    metadata = {
        "Latitude": None,
        "Longitude": None,
        "Make": tags.get("Image Make", "N/A"),
        "Model": tags.get("Image Model", "N/A"),
        "Date Time": tags.get("EXIF DateTimeOriginal", tags.get("Image DateTime", "N/A")),
        "ISO": tags.get("EXIF ISOSpeedRatings", "N/A"),
        "Focal Length": tags.get("EXIF FocalLength", "N/A"),
        "Aperture": tags.get("EXIF FNumber", "N/A"),
        "Shutter Speed": tags.get("EXIF ExposureTime", "N/A")
    }

    gps_latitude = tags.get("GPS GPSLatitude")
    gps_latitude_ref = tags.get("GPS GPSLatitudeRef")
    gps_longitude = tags.get("GPS GPSLongitude")
    gps_longitude_ref = tags.get("GPS GPSLongitudeRef")

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = convert_to_degrees(gps_latitude)
        if gps_latitude_ref.values[0] != 'N':
            lat = -lat

        lon = convert_to_degrees(gps_longitude)
        if gps_longitude_ref.values[0] != 'E':
            lon = -lon

        metadata["Latitude"] = lat
        metadata["Longitude"] = lon

    return metadata


@st.cache_data(show_spinner=False)
def reverse_geocode(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, language="en")
        if location:
            return location.address
    except (GeocoderTimedOut, GeocoderServiceError):
        return "Address lookup timed out or service unavailable"
    return "Address not found"


st.sidebar.header("Upload Photos")
uploaded_files = st.sidebar.file_uploader(
    "Choose photo files (JPG / JPEG / TIFF)",
    type=["jpg", "jpeg", "tiff"],
    accept_multiple_files=True
)

if uploaded_files:
    extracted_records = []

    for file in uploaded_files:
        file_bytes = io.BytesIO(file.read())
        metadata = extract_exif_data(file_bytes)
        
        file_bytes.seek(0)
        
        record = {
            "filename": file.name,
            "bytes": file_bytes,
            "metadata": metadata,
            "address": "N/A"
        }

        if metadata["Latitude"] and metadata["Longitude"]:
            address = reverse_geocode(metadata["Latitude"], metadata["Longitude"])
            record["address"] = address

        extracted_records.append(record)

    gps_records = [r for r in extracted_records if r["metadata"]["Latitude"] is not None]

    st.sidebar.success(f"Processed {len(uploaded_files)} file(s). Found GPS in {len(gps_records)} file(s).")

    if gps_records:
        st.subheader("🗺️ Map View")

        avg_lat = sum(r["metadata"]["Latitude"] for r in gps_records) / len(gps_records)
        avg_lon = sum(r["metadata"]["Longitude"] for r in gps_records) / len(gps_records)

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=11)

        for r in gps_records:
            lat = r["metadata"]["Latitude"]
            lon = r["metadata"]["Longitude"]
            meta = r["metadata"]

            popup_html = f"""
            <div style="font-family: sans-serif; width: 220px;">
                <h4><b>{r['filename']}</b></h4>
                <p><b>Date:</b> {meta['Date Time']}</p>
                <p><b>Camera:</b> {meta['Make']} {meta['Model']}</p>
                <p><b>Address:</b> {r['address']}</p>
                <p><b>Coordinates:</b> {lat:.5f}, {lon:.5f}</p>
            </div>
            """

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=r["filename"],
                icon=folium.Icon(color="red", icon="camera", prefix="fa")
            ).add_to(m)

        st_folium(m, width="100%", height=500)

    else:
        st.warning("⚠️ None of the uploaded images contained embedded GPS coordinates.")

    st.markdown("---")
    st.subheader("🖼️ Detailed Photo & Metadata Viewer")

    cols = st.columns(2)
    for idx, r in enumerate(extracted_records):
        with cols[idx % 2]:
            st.image(r["bytes"], caption=r["filename"], use_container_width=True)
            meta = r["metadata"]
            
            with st.expander(f"Metadata for {r['filename']}", expanded=True):
                if meta["Latitude"] and meta["Longitude"]:
                    st.markdown(f"**📍 Coordinates:** `{meta['Latitude']:.6f}, {meta['Longitude']:.6f}`")
                    st.markdown(f"**🏠 Address:** {r['address']}")
                else:
                    st.markdown("**📍 Coordinates:** *No GPS metadata found in file.*")

                st.markdown(f"**📷 Camera:** {meta['Make']} {meta['Model']}")
                st.markdown(f"**📅 Date Taken:** {meta['Date Time']}")
                st.markdown(f"**⚙️ Settings:** ISO {meta['ISO']} | F/{meta['Aperture']} | {meta['Shutter Speed']}s | {meta['Focal Length']}mm")

else:
    st.info("👈 Please upload photo files using the sidebar to begin.")
