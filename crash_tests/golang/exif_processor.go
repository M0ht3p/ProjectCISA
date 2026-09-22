package main

import (
	"fmt"
	"log"
	"os"

	"github.com/rwcarlsen/goexif/exif"
	"github.com/rwcarlsen/goexif/tiff"
)

type PhotoMetadata struct {
	Filename     string
	Make         string
	Model        string
	DateTime     string
	ISO          string
	FocalLength  string
	Aperture     string
	ShutterSpeed string
	Latitude     *float64
	Longitude    *float64
}

func evalRational(rat *tiff.Rational) float64 {
	if rat.Denom == 0 {
		return 0
	}
	return float64(rat.Num) / float64(rat.Denom)
}

func parseGPSCoordinate(latTag, refTag *exif.Tag) (*float64, error) {
	ratSlice, err := latTag.RatSlice()
	if err != nil || len(ratSlice) < 3 {
		return nil, fmt.Errorf("invalid GPS coordinate format")
	}

	d := evalRational(ratSlice[0])
	m := evalRational(ratSlice[1])
	s := evalRational(ratSlice[2])

	deg := d + (m / 60.0) + (s / 3600.0)

	ref, err := refTag.StringVal()
	if err == nil && (ref == "S" || ref == "W") {
		deg = -deg
	}

	return &deg, nil
}

func ExtractExifData(filePath string) (*PhotoMetadata, error) {
	file, err := os.Open(filePath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	x, err := exif.Decode(file)
	if err != nil {
		return &PhotoMetadata{Filename: filePath}, nil
	}

	meta := &PhotoMetadata{Filename: filePath}

	if tag, err := x.Get(exif.Make); err == nil {
		if val, err := tag.StringVal(); err == nil {
			meta.Make = val
		}
	}
	if tag, err := x.Get(exif.Model); err == nil {
		if val, err := tag.StringVal(); err == nil {
			meta.Model = val
		}
	}
	if tag, err := x.Get(exif.DateTimeOriginal); err == nil {
		if val, err := tag.StringVal(); err == nil {
			meta.DateTime = val
		}
	}
	if tag, err := x.Get(exif.ISOSpeedRatings); err == nil {
		if val, err := tag.Int(0); err == nil {
			meta.ISO = fmt.Sprintf("%d", val)
		}
	}
	if tag, err := x.Get(exif.FocalLength); err == nil {
		if rat, err := tag.Rat(0); err == nil {
			meta.FocalLength = fmt.Sprintf("%.2fmm", evalRational(rat))
		}
	}
	if tag, err := x.Get(exif.FNumber); err == nil {
		if rat, err := tag.Rat(0); err == nil {
			meta.Aperture = fmt.Sprintf("F/%.1f", evalRational(rat))
		}
	}
	if tag, err := x.Get(exif.ExposureTime); err == nil {
		if rat, err := tag.Rat(0); err == nil {
			meta.ShutterSpeed = fmt.Sprintf("1/%.0f", 1/evalRational(rat))
		}
	}
	latTag, latErr := x.Get(exif.GPSLatitude)
	latRefTag, latRefErr := x.Get(exif.GPSLatitudeRef)
	lonTag, lonErr := x.Get(exif.GPSLongitude)
	lonRefTag, lonRefErr := x.Get(exif.GPSLongitudeRef)

	if latErr == nil && latRefErr == nil {
		if lat, err := parseGPSCoordinate(latTag, latRefTag); err == nil {
			meta.Latitude = lat
		}
	}

	if lonErr == nil && lonRefErr == nil {
		if lon, err := parseGPSCoordinate(lonTag, lonRefTag); err == nil {
			meta.Longitude = lon
		}
	}

	return meta, nil
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run main.go <path_to_image.jpg>")
		return
	}

	filePath := os.Args[1]
	meta, err := ExtractExifData(filePath)
	if err != nil {
		log.Fatalf("Failed to extract EXIF: %v", err)
	}

	fmt.Printf("--- Metadata for %s ---\n", meta.Filename)
	fmt.Printf("Camera:       %s %s\n", meta.Make, meta.Model)
	fmt.Printf("Date Taken:   %s\n", meta.DateTime)
	fmt.Printf("Settings:     ISO %s | %s | %s | %s\n", meta.ISO, meta.Aperture, meta.ShutterSpeed, meta.FocalLength)
	
	if meta.Latitude != nil && meta.Longitude != nil {
		fmt.Printf("Coordinates:  %.6f, %.6f\n", *meta.Latitude, *meta.Longitude)
	} else {
		fmt.Println("Coordinates:  No GPS metadata found.")
	}
}
