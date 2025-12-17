"""Geolocation utilities for distance calculations and nearby searches"""

import math
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class Coordinates:
    """Represents a geographic coordinate"""
    latitude: float
    longitude: float

    def __post_init__(self):
        """Validate coordinates"""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Invalid latitude: {self.latitude}. Must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Invalid longitude: {self.longitude}. Must be between -180 and 180")

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {"latitude": self.latitude, "longitude": self.longitude}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "Coordinates":
        """Create from dictionary"""
        return cls(latitude=data["latitude"], longitude=data["longitude"])


class GeoLocationService:
    """Service for geolocation calculations"""

    # Earth's radius in kilometers
    EARTH_RADIUS_KM = 6371.0

    @staticmethod
    def haversine_distance(
        coord1: Coordinates,
        coord2: Coordinates,
        unit: str = "km"
    ) -> float:
        """
        Calculate the great-circle distance between two points on Earth
        using the Haversine formula

        Args:
            coord1: First coordinate
            coord2: Second coordinate
            unit: Distance unit ('km', 'mi', 'm')

        Returns:
            Distance in the specified unit
        """
        # Convert to radians
        lat1_rad = math.radians(coord1.latitude)
        lon1_rad = math.radians(coord1.longitude)
        lat2_rad = math.radians(coord2.latitude)
        lon2_rad = math.radians(coord2.longitude)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Distance in kilometers
        distance_km = GeoLocationService.EARTH_RADIUS_KM * c

        # Convert to requested unit
        if unit == "km":
            return distance_km
        elif unit == "mi":
            return distance_km * 0.621371  # km to miles
        elif unit == "m":
            return distance_km * 1000  # km to meters
        else:
            raise ValueError(f"Invalid unit: {unit}. Must be 'km', 'mi', or 'm'")

    @staticmethod
    def calculate_bounding_box(
        center: Coordinates,
        radius_km: float
    ) -> Dict[str, float]:
        """
        Calculate a bounding box around a center point

        This is useful for efficient database queries - instead of calculating
        distance to every point, we can first filter by bounding box.

        Args:
            center: Center coordinate
            radius_km: Radius in kilometers

        Returns:
            Dictionary with min_lat, max_lat, min_lon, max_lon
        """
        # Approximate degrees per kilometer
        # At the equator: 1 degree latitude ≈ 111 km
        # Longitude varies by latitude
        lat_km = 111.0
        lon_km = 111.0 * math.cos(math.radians(center.latitude))

        # Calculate deltas
        lat_delta = radius_km / lat_km
        lon_delta = radius_km / lon_km

        return {
            "min_lat": center.latitude - lat_delta,
            "max_lat": center.latitude + lat_delta,
            "min_lon": center.longitude - lon_delta,
            "max_lon": center.longitude + lon_delta
        }

    @staticmethod
    def is_within_radius(
        point: Coordinates,
        center: Coordinates,
        radius_km: float
    ) -> bool:
        """
        Check if a point is within a certain radius of a center point

        Args:
            point: Point to check
            center: Center coordinate
            radius_km: Radius in kilometers

        Returns:
            True if point is within radius, False otherwise
        """
        distance = GeoLocationService.haversine_distance(point, center, unit="km")
        return distance <= radius_km

    @staticmethod
    def format_distance(distance_km: float, unit: str = "auto") -> str:
        """
        Format distance for display

        Args:
            distance_km: Distance in kilometers
            unit: Display unit ('auto', 'km', 'mi')

        Returns:
            Formatted distance string
        """
        if unit == "auto":
            # Use km for distances > 1km, otherwise meters
            if distance_km >= 1:
                return f"{distance_km:.1f} km"
            else:
                return f"{distance_km * 1000:.0f} m"
        elif unit == "km":
            return f"{distance_km:.1f} km"
        elif unit == "mi":
            distance_mi = distance_km * 0.621371
            return f"{distance_mi:.1f} mi"
        else:
            raise ValueError(f"Invalid unit: {unit}")

    @staticmethod
    def get_distance_ranges() -> List[Dict[str, Any]]:
        """
        Get predefined distance ranges for filtering

        Returns:
            List of distance range options
        """
        return [
            {"label": "Within 5 km", "value": 5, "description": "Very close by"},
            {"label": "Within 10 km", "value": 10, "description": "Nearby"},
            {"label": "Within 25 km", "value": 25, "description": "In the area"},
            {"label": "Within 50 km", "value": 50, "description": "Same region"},
            {"label": "Within 100 km", "value": 100, "description": "Extended area"},
            {"label": "Any distance", "value": None, "description": "No distance limit"}
        ]

    @staticmethod
    def geocode_city(city: str, country: str) -> Optional[Coordinates]:
        """
        Get coordinates for a city (simplified version)

        In production, this should use a geocoding service like:
        - Google Maps Geocoding API
        - Mapbox Geocoding API
        - OpenStreetMap Nominatim

        Args:
            city: City name
            country: Country name

        Returns:
            Coordinates if found, None otherwise
        """
        # This is a simplified implementation with common cities
        # In production, use a proper geocoding service

        city_coords = {
            # Major cities in Africa
            ("lagos", "nigeria"): Coordinates(6.5244, 3.3792),
            ("nairobi", "kenya"): Coordinates(-1.2864, 36.8172),
            ("johannesburg", "south africa"): Coordinates(-26.2041, 28.0473),
            ("cairo", "egypt"): Coordinates(30.0444, 31.2357),
            ("accra", "ghana"): Coordinates(5.6037, -0.1870),
            ("cape town", "south africa"): Coordinates(-33.9249, 18.4241),
            ("dar es salaam", "tanzania"): Coordinates(-6.7924, 39.2083),
            ("addis ababa", "ethiopia"): Coordinates(9.0320, 38.7469),
            ("kampala", "uganda"): Coordinates(0.3476, 32.5825),
            ("kigali", "rwanda"): Coordinates(-1.9706, 30.1044),

            # Add more cities as needed
        }

        key = (city.lower(), country.lower())
        return city_coords.get(key)

    @staticmethod
    def get_nearby_points(
        points: List[Tuple[Any, Coordinates]],
        center: Coordinates,
        radius_km: float,
        sort: bool = True,
        limit: Optional[int] = None
    ) -> List[Tuple[Any, Coordinates, float]]:
        """
        Filter points within radius and optionally sort by distance

        Args:
            points: List of (data, coordinates) tuples
            center: Center coordinate
            radius_km: Radius in kilometers
            sort: Whether to sort by distance
            limit: Maximum number of results

        Returns:
            List of (data, coordinates, distance_km) tuples
        """
        results = []

        for data, coord in points:
            distance = GeoLocationService.haversine_distance(coord, center, unit="km")

            if distance <= radius_km:
                results.append((data, coord, distance))

        if sort:
            results.sort(key=lambda x: x[2])  # Sort by distance

        if limit:
            results = results[:limit]

        return results


# Convenience functions
def calculate_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    unit: str = "km"
) -> float:
    """
    Calculate distance between two coordinate pairs

    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate
        unit: Distance unit

    Returns:
        Distance in specified unit
    """
    coord1 = Coordinates(lat1, lon1)
    coord2 = Coordinates(lat2, lon2)
    return GeoLocationService.haversine_distance(coord1, coord2, unit)


def get_bounding_box(
    latitude: float,
    longitude: float,
    radius_km: float
) -> Dict[str, float]:
    """Get bounding box around a point"""
    center = Coordinates(latitude, longitude)
    return GeoLocationService.calculate_bounding_box(center, radius_km)


# Example usage and testing
if __name__ == "__main__":
    # Example: Distance between Lagos and Nairobi
    lagos = Coordinates(6.5244, 3.3792)
    nairobi = Coordinates(-1.2864, 36.8172)

    distance_km = GeoLocationService.haversine_distance(lagos, nairobi)
    print(f"Distance from Lagos to Nairobi: {distance_km:.1f} km")

    # Example: Bounding box for 50km radius
    bbox = GeoLocationService.calculate_bounding_box(lagos, 50)
    print(f"Bounding box (50km): {bbox}")

    # Example: Check if point is within radius
    nearby_point = Coordinates(6.6, 3.4)
    is_nearby = GeoLocationService.is_within_radius(nearby_point, lagos, 50)
    print(f"Is point nearby Lagos (50km)? {is_nearby}")
