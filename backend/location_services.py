import requests
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union

# Configure logging
logger = logging.getLogger(__name__)

class LocationServices:
    """
    Service for location-based features including weather forecasts and traffic conditions.
    Uses Open-Meteo API for weather and OpenRouteService/OSRM for routing.
    """
    
    def __init__(self):
        """Initialize location services with API keys and base URLs."""
        # API keys - use environment variables in production
        self.weather_api_url = "https://api.open-meteo.com/v1/forecast"
        self.geocoding_api_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.routing_api_url = "https://api.openrouteservice.org/v2/directions/driving-car"
        self.routing_api_key = os.environ.get("OPENROUTE_API_KEY", "YOUR_DEFAULT_KEY")
        
        # Cache for geocoded locations and weather data
        self.location_cache = {}
        self.weather_cache = {}
        self.traffic_cache = {}
        
        logger.info("Location Services initialized")
    
    def geocode_location(self, location_query: str) -> Optional[Dict[str, Any]]:
        """
        Convert a location string to coordinates using Open-Meteo Geocoding API.
        
        Args:
            location_query: The location to geocode (e.g., "New York City")
            
        Returns:
            Dict with location name, coordinates, and info or None if not found
        """
        try:
            # Check cache first
            if location_query in self.location_cache:
                logger.debug(f"Using cached coordinates for {location_query}")
                return self.location_cache[location_query]
            
            logger.info(f"Geocoding location: {location_query}")
            
            # Make API request to geocoding service
            params = {
                "name": location_query,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            
            response = requests.get(self.geocoding_api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data or 'results' not in data or len(data['results']) == 0:
                logger.warning(f"No geocoding results for: {location_query}")
                return None
                
            # Extract relevant information
            result = data['results'][0]
            location_data = {
                'name': result.get('name', location_query),
                'latitude': result.get('latitude'),
                'longitude': result.get('longitude'),
                'country': result.get('country', ''),
                'state': result.get('admin1', ''),
                'city': result.get('admin2', ''),
                'timezone': result.get('timezone', 'UTC')
            }
            
            # Cache the result
            self.location_cache[location_query] = location_data
            
            logger.info(f"Successfully geocoded {location_query}")
            return location_data
            
        except requests.RequestException as e:
            logger.error(f"Geocoding API error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
            return None
    
    def get_weather_forecast(self, location: Union[str, Dict], days: int = 5) -> Optional[Dict]:
        """
        Get weather forecast for a location.
        
        Args:
            location: Location string or dict with latitude/longitude
            days: Number of days to forecast (max 7)
            
        Returns:
            Dict with weather forecast data or None if unavailable
        """
        try:
            # Limit days to valid range
            days = min(max(1, days), 7)
            
            # Get coordinates from location
            coords = None
            if isinstance(location, str):
                location_data = self.geocode_location(location)
                if not location_data:
                    return None
                coords = (location_data['latitude'], location_data['longitude'])
                location_key = location
            else:
                # If location is already a dict with coordinates
                coords = (location.get('latitude'), location.get('longitude'))
                location_key = f"{coords[0]},{coords[1]}"
            
            # Check cache for recent forecast (less than 3 hours old)
            current_time = datetime.now()
            if location_key in self.weather_cache:
                cached = self.weather_cache[location_key]
                cache_age = current_time - cached['timestamp']
                if cache_age.total_seconds() < 10800:  # 3 hours
                    logger.debug(f"Using cached weather for {location_key}")
                    return cached['data']
            
            logger.info(f"Fetching weather forecast for {location_key}")
            
            # Build weather API request
            params = {
                "latitude": coords[0],
                "longitude": coords[1],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "current_weather": True,
                "timezone": "auto",
                "forecast_days": days
            }
            
            response = requests.get(self.weather_api_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Format the response
            daily = data.get('daily', {})
            current = data.get('current_weather', {})
            
            forecast = {
                'location': location_key,
                'current': {
                    'temperature': current.get('temperature'),
                    'weathercode': current.get('weathercode'),
                    'time': current.get('time'),
                    'description': self._get_weather_description(current.get('weathercode')),
                    'icon': self._get_weather_icon(current.get('weathercode'))
                },
                'daily': []
            }
            
            # Process daily forecasts
            times = daily.get('time', [])
            for i in range(len(times)):
                day_forecast = {
                    'date': times[i],
                    'max_temp': daily.get('temperature_2m_max', [])[i] if i < len(daily.get('temperature_2m_max', [])) else None,
                    'min_temp': daily.get('temperature_2m_min', [])[i] if i < len(daily.get('temperature_2m_min', [])) else None,
                    'precipitation': daily.get('precipitation_sum', [])[i] if i < len(daily.get('precipitation_sum', [])) else None,
                    'weathercode': daily.get('weathercode', [])[i] if i < len(daily.get('weathercode', [])) else None
                }
                
                # Add human-readable description and icon
                day_forecast['description'] = self._get_weather_description(day_forecast['weathercode'])
                day_forecast['icon'] = self._get_weather_icon(day_forecast['weathercode'])
                
                forecast['daily'].append(day_forecast)
            
            # Cache the result
            self.weather_cache[location_key] = {
                'timestamp': current_time,
                'data': forecast
            }
            
            logger.info(f"Successfully fetched weather for {location_key}")
            return forecast
            
        except requests.RequestException as e:
            logger.error(f"Weather API error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Weather forecast error: {str(e)}")
            return None
    
    def get_traffic_estimate(self, origin: str, destination: str) -> Optional[Dict]:
        """
        Get traffic and route information between two locations.
        
        Args:
            origin: Starting location (address or place name)
            destination: Ending location (address or place name)
            
        Returns:
            Dict with route, duration, distance, and traffic info or None if unavailable
        """
        try:
            # Create cache key
            cache_key = f"{origin}|{destination}"
            
            # Check cache for recent estimate (less than 30 minutes old)
            current_time = datetime.now()
            if cache_key in self.traffic_cache:
                cached = self.traffic_cache[cache_key]
                cache_age = current_time - cached['timestamp']
                if cache_age.total_seconds() < 1800:  # 30 minutes
                    logger.debug(f"Using cached traffic for {cache_key}")
                    return cached['data']
            
            logger.info(f"Fetching traffic estimate from {origin} to {destination}")
            
            # Geocode origin and destination
            origin_loc = self.geocode_location(origin)
            destination_loc = self.geocode_location(destination)
            
            if not origin_loc or not destination_loc:
                logger.warning(f"Could not geocode locations: {origin} or {destination}")
                return None
            
            # Format coordinates for API (longitude, latitude order for GeoJSON)
            coordinates = [
                [origin_loc['longitude'], origin_loc['latitude']],
                [destination_loc['longitude'], destination_loc['latitude']]
            ]
            
            # Make API request to routing service
            headers = {
                'Accept': 'application/json',
                'Authorization': self.routing_api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'coordinates': coordinates,
                'instructions': True,
                'units': 'miles',
                'language': 'en'
            }
            
            # Fall back to simulated data if no API key is provided
            if self.routing_api_key == "YOUR_DEFAULT_KEY":
                logger.warning("Using simulated traffic data (no API key)")
                route_data = self._generate_simulated_route(origin_loc, destination_loc)
            else:
                response = requests.post(
                    self.routing_api_url, 
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                route_data = self._process_route_response(response.json(), origin_loc, destination_loc)
            
            # Cache the result
            self.traffic_cache[cache_key] = {
                'timestamp': current_time,
                'data': route_data
            }
            
            logger.info(f"Successfully fetched traffic for {cache_key}")
            return route_data
            
        except requests.RequestException as e:
            logger.error(f"Routing API error: {str(e)}")
            return self._generate_simulated_route(
                self.geocode_location(origin) if isinstance(origin, str) else origin,
                self.geocode_location(destination) if isinstance(destination, str) else destination
            )
        except Exception as e:
            logger.error(f"Traffic estimate error: {str(e)}")
            return None
    
    def _process_route_response(self, response_data, origin_loc, destination_loc):
        """Process routing API response into usable format."""
        try:
            # Extract route from response
            routes = response_data.get('routes', [])
            if not routes:
                return None
                
            route = routes[0]
            
            # Extract summary information
            summary = route.get('summary', {})
            distance = summary.get('distance', 0)  # in meters
            duration = summary.get('duration', 0)  # in seconds
            
            # Convert units
            distance_miles = round(distance / 1609.34, 2)
            duration_minutes = round(duration / 60, 0)
            
            # Extract steps if available
            steps = []
            for segment in route.get('segments', []):
                for step in segment.get('steps', []):
                    steps.append({
                        'instruction': step.get('instruction', ''),
                        'distance': round(step.get('distance', 0) / 1609.34, 2),  # miles
                        'duration': round(step.get('duration', 0) / 60, 1),  # minutes
                    })
            
            # Calculate traffic conditions (simplified)
            traffic_level = "moderate"
            if duration_minutes < 10:
                traffic_level = "light"
            elif duration_minutes > 30:
                traffic_level = "heavy"
                
            return {
                'origin': origin_loc['name'],
                'destination': destination_loc['name'],
                'distance': distance_miles,
                'duration': duration_minutes,
                'traffic_level': traffic_level,
                'steps': steps,
                'coordinates': route.get('geometry')
            }
            
        except Exception as e:
            logger.error(f"Error processing route response: {str(e)}")
            return None
    
    def _generate_simulated_route(self, origin_loc, destination_loc):
        """Generate simulated route data for testing or when API is unavailable."""
        if not origin_loc or not destination_loc:
            return None
            
        # Calculate approximate distance using simplified formula
        lat1, lon1 = origin_loc['latitude'], origin_loc['longitude']
        lat2, lon2 = destination_loc['latitude'], destination_loc['longitude']
        
        # Very simplified distance calculation (not accurate for long distances)
        distance = ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) ** 0.5 * 69.0  # rough miles
        distance = round(distance, 2)
        
        # Simulate duration based on distance
        # Assume average speed of 30mph with some randomness
        import random
        duration = distance / 30.0 * 60  # minutes
        duration = round(duration * random.uniform(0.8, 1.2), 0)  # add some variability
        
        # Determine traffic level
        traffic_level = "moderate"
        if duration < 15:
            traffic_level = "light"
        elif duration > 45:
            traffic_level = "heavy"
            
        return {
            'origin': origin_loc['name'],
            'destination': destination_loc['name'],
            'distance': distance,
            'duration': duration,
            'traffic_level': traffic_level,
            'steps': [
                {
                    'instruction': f"Head from {origin_loc['name']} to {destination_loc['name']}",
                    'distance': distance,
                    'duration': duration
                }
            ],
            'coordinates': None,
            'simulated': True
        }
    
    def _get_weather_description(self, code: Optional[int]) -> str:
        """Convert WMO weather code to human-readable description."""
        if code is None:
            return "Unknown"
            
        # WMO Weather codes: https://www.nodc.noaa.gov/archive/arc0021/0002199/1.1/data/0-data/HTML/WMO-CODE/WMO4677.HTM
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        
        return weather_codes.get(code, "Unknown")
    
    def _get_weather_icon(self, code: Optional[int]) -> str:
        """Convert WMO weather code to icon name (for frontend use)."""
        if code is None:
            return "question"
            
        # Map weather codes to icon names
        if code == 0:
            return "sun"
        elif code in (1, 2):
            return "partly-cloudy"
        elif code == 3:
            return "cloud"
        elif code in (45, 48):
            return "fog"
        elif code in (51, 53, 55, 56, 57):
            return "drizzle"
        elif code in (61, 63, 65, 66, 67, 80, 81, 82):
            return "rain"
        elif code in (71, 73, 75, 77, 85, 86):
            return "snow"
        elif code in (95, 96, 99):
            return "thunderstorm"
        else:
            return "question" 