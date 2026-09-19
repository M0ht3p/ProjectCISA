import io
import exifread
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

geolocator = Nominatim(user_agent="project_cisa_cython_app")


cpdef double convert_to_degrees(object value):
    """Converts EXIF degree/minute/second ratio tuples to decimal degrees."""
    cdef double d, m, s
    d = float(value.values[0].num) / float(value.values[0].den)
    m = float(value.values[1].num) / float(value.values[1].den)
    s = float(value.values[2].num) / float(value.values[2].den)
    return d + (m / 60.0) + (s / 3600.0)


cpdef dict extract_exif_data(object file_stream):
    """Extracts EXIF metadata tags and converts GPS coordinates to floats."""
    cdef dict metadata
    cdef double lat, lon
    
    tags = exifread.process_file(file_stream, details=False)
    
    metadata = {
        "Latitude": None,
        "Longitude": None,
        "Make": str(tags.get("Image Make", "N/A")),
        "Model": str(tags.get("Image Model", "N/A")),
        "Date Time": str(tags.get("EXIF DateTimeOriginal", tags.get("Image DateTime", "N/A"))),
        "ISO": str(tags.get("EXIF ISOSpeedRatings", "N/A")),
        "Focal Length": str(tags.get("EXIF FocalLength", "N/A")),
        "Aperture": str(tags.get("EXIF FNumber", "N/A")),
        "Shutter Speed": str(tags.get("EXIF ExposureTime", "N/A"))
    }

    gps_latitude = tags.get("GPS GPSLatitude")
    gps_latitude_ref = tags.get("GPS GPSLatitudeRef")
    gps_longitude = tags.get("GPS GPSLongitude")
    gps_longitude_ref = tags.get("GPS GPSLongitudeRef")

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = convert_to_degrees(gps_latitude)
        if str(gps_latitude_ref.values[0]).upper() != 'N':
            lat = -lat

        lon = convert_to_degrees(gps_longitude)
        if str(gps_longitude_ref.values[0]).upper() != 'E':
            lon = -lon

        metadata["Latitude"] = lat
        metadata["Longitude"] = lon

    return metadata


cpdef str reverse_geocode(double lat, double lon):
    """Performs reverse geocoding on given latitude and longitude."""
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, language="en")
        if location:
            return str(location.address)
    except (GeocoderTimedOut, GeocoderServiceError):
        return "Address lookup timed out or service unavailable"
    return "Address not found"


cpdef list process_image_files(list file_paths):
    """Processes a list of file paths, extracting metadata and reverse geocoding GPS coordinates."""
    cdef list records = []
    cdef str path, address
    cdef dict metadata, record
    cdef double lat, lon

    for path in file_paths:
        with open(path, 'rb') as f:
            metadata = extract_exif_data(f)
        
        address = "N/A"
        if metadata["Latitude"] is not None and metadata["Longitude"] is not None:
            lat = metadata["Latitude"]
            lon = metadata["Longitude"]
            address = reverse_geocode(lat, lon)

        record = {
            "filename": path,
            "metadata": metadata,
            "address": address
        }
        records.append(record)

    return records
