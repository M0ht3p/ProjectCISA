use exif::{In, Tag, Value};
use serde::Deserialize;
use std::env;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

#[derive(Debug, Default)]
struct ImageMetadata {
    filename: String,
    make: String,
    model: String,
    date_time: String,
    iso: String,
    focal_length: String,
    aperture: String,
    shutter_speed: String,
    latitude: Option<f64>,
    longitude: Option<f64>,
    address: String,
}

#[derive(Deserialize)]
struct NominatimResponse {
    display_name: Option<String>,
}

fn convert_dms_to_degrees(field: &exif::Field) -> Option<f64> {
    if let Value::Rational(ref rationals) = field.value {
        if rationals.len() >= 3 {
            let d = rationals[0].num as f64 / rationals[0].den as f64;
            let m = rationals[1].num as f64 / rationals[1].den as f64;
            let s = rationals[2].num as f64 / rationals[2].den as f64;
            return Some(d + (m / 60.0) + (s / 3600.0));
        }
    }
    None
}

fn extract_exif_data(file_path: &Path) -> Result<ImageMetadata, Box<dyn std::error::Error>> {
    let file = File::open(file_path)?;
    let mut bufreader = BufReader::new(file);
    let exifreader = exif::Reader::new();
    let exif_data = exifreader.read_from_container(&mut bufreader)?;

    let get_tag_value = |tag: Tag| -> String {
        exif_data
            .get_field(tag, In::PRIMARY)
            .map(|f| f.display_value().with_unit(&exif_data).to_string())
            .unwrap_or_else(|| "N/A".to_string())
    };

    let mut metadata = ImageMetadata {
        filename: file_path
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string(),
        make: get_tag_value(Tag::Make),
        model: get_tag_value(Tag::Model),
        date_time: get_tag_value(Tag::DateTimeOriginal),
        iso: get_tag_value(Tag::PhotographicSensitivity),
        focal_length: get_tag_value(Tag::FocalLength),
        aperture: get_tag_value(Tag::FNumber),
        shutter_speed: get_tag_value(Tag::ExposureTime),
        address: "N/A".to_string(),
        ..Default::default()
    };

    if metadata.date_time == "N/A" {
        metadata.date_time = get_tag_value(Tag::DateTime);
    }

    let lat_field = exif_data.get_field(Tag::GPSLatitude, In::PRIMARY);
    let lat_ref_field = exif_data.get_field(Tag::GPSLatitudeRef, In::PRIMARY);
    let lon_field = exif_data.get_field(Tag::GPSLongitude, In::PRIMARY);
    let lon_ref_field = exif_data.get_field(Tag::GPSLongitudeRef, In::PRIMARY);

    if let (Some(lat_f), Some(lat_ref), Some(lon_f), Some(lon_ref)) =
        (lat_field, lat_ref_field, lon_field, lon_ref_field)
    {
        if let (Some(mut lat), Some(mut lon)) =
            (convert_dms_to_degrees(lat_f), convert_dms_to_degrees(lon_f))
        {
            let lat_ref_str = lat_ref.display_value().to_string();
            if lat_ref_str.contains('S') {
                lat = -lat;
            }

            let lon_ref_str = lon_ref.display_value().to_string();
            if lon_ref_str.contains('W') {
                lon = -lon;
            }

            metadata.latitude = Some(lat);
            metadata.longitude = Some(lon);
        }
    }

    Ok(metadata)
}

async fn reverse_geocode(
    client: &reqwest::Client,
    lat: f64,
    lon: f64,
) -> Result<String, Box<dyn std::error::Error>> {
    let url = format!(
        "https://nominatim.openstreetmap.org/reverse?format=json&lat={}&lon={}&accept-language=en",
        lat, lon
    );

    let res = client
        .get(&url)
        .header("User-Agent", "project_cisa_rust_app/1.0")
        .send()
        .await?;

    if res.status().is_success() {
        let payload: NominatimResponse = res.json().await?;
        Ok(payload
            .display_name
            .unwrap_or_else(|| "Address not found".to_string()))
    } else {
        Ok("Address lookup timed out or service unavailable".to_string())
    }
}

#[tokio::main]
async fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        println!("Usage: cargo run -- <image_file_1> [image_file_2 ...]");
        return;
    }

    let http_client = reqwest::Client::new();
    let mut records = Vec::new();
    let mut gps_count = 0;

    for arg in &args[1..] {
        let path = Path::new(arg);
        match extract_exif_data(path) {
            Ok(mut meta) => {
                if let (Some(lat), Some(lon)) = (meta.latitude, meta.longitude) {
                    gps_count += 1;
                    match reverse_geocode(&http_client, lat, lon).await {
                        Ok(addr) => meta.address = addr,
                        Err(_) => {
                            meta.address = "Address lookup error".to_string();
                        }
                    }
                }
                records.push(meta);
            }
            Err(e) => {
                eprintln!("Error processing file {}: {}", arg, e);
            }
        }
    }

    println!("\nProcessed {} file(s). Found GPS in {} file(s).\n", records.len(), gps_count);
    println!("{:=^70}", " EXTRACTED METADATA ");

    for record in &records {
        println!("\n📸 File: {}", record.filename);
        println!("  ├─ Camera:       {} {}", record.make, record.model);
        println!("  ├─ Date Taken:   {}", record.date_time);
        println!(
            "  ├─ Settings:     ISO {} | F/{} | {}s | {}",
            record.iso, record.aperture, record.shutter_speed, record.focal_length
        );

        if let (Some(lat), Some(lon)) = (record.latitude, record.longitude) {
            println!("  ├─ Coordinates:  {:.6}, {:.6}", lat, lon);
            println!("  └─ Address:      {}", record.address);
        } else {
            println!("  └─ Coordinates:  No GPS metadata found.");
        }
    }
}
