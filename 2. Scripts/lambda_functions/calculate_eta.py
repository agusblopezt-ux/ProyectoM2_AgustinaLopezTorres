# Lambda 2: calcular el tiempo estimado de llegada (ETA)
# Se ejecuta cuando la app hace GET /trips/eta?trip_id=1&lat=-32.94&lon=-60.65&destino=Córdoba

import json                                   # para escribir la respuesta en JSON
import math                                   # funciones matemáticas (seno, coseno, raíz)
from datetime import datetime, timedelta      # para sumar horas a la hora actual
import boto3                                  # librería de Python para usar servicios de AWS

dynamodb = boto3.resource("dynamodb")         # conexión a DynamoDB
tabla = dynamodb.Table("fleetlogix-trip-status")        # la tabla con el estado de cada viaje

VELOCIDAD_KMH = 76        # velocidad promedio REAL medida en los 100.000 viajes de trips.csv
FACTOR_RUTA = 1.25        # la ruta por ruta es ~25% más larga que la línea recta

CIUDADES = {              # coordenadas (latitud, longitud) de las 5 ciudades de la tabla routes
    "Buenos Aires": (-34.6037, -58.3816),
    "Córdoba": (-31.4201, -64.1888),
    "Rosario": (-32.9442, -60.6505),
    "Mendoza": (-32.8895, -68.8458),
    "San Miguel de Tucumán": (-26.8083, -65.2176),
}


def distancia_km(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos puntos del mapa (fórmula de Haversine)."""
    radio = 6371                                                      # radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)                                  # diferencia de latitud en radianes
    dlon = math.radians(lon2 - lon1)                                  # diferencia de longitud en radianes
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return 2 * radio * math.asin(math.sqrt(a))                        # distancia final en km


def calcular_eta(lat, lon, destino):
    """Devuelve los km que faltan y las horas que faltan para llegar."""
    lat_dest, lon_dest = CIUDADES[destino]                            # coordenadas del destino
    km = distancia_km(lat, lon, lat_dest, lon_dest) * FACTOR_RUTA     # km que faltan por ruta
    horas = km / VELOCIDAD_KMH                                        # tiempo = distancia / velocidad
    return km, horas


def lambda_handler(event, context):
    p = event["queryStringParameters"]                                # los datos que vienen en la URL
    km, horas = calcular_eta(float(p["lat"]), float(p["lon"]), p["destino"])
    eta = datetime.utcnow() + timedelta(hours=horas)                  # hora actual + horas que faltan

    # Guardar el ETA en DynamoDB para que lo vea el centro de control
    tabla.update_item(
        Key={"trip_id": int(p["trip_id"])},                           # qué viaje actualizar
        UpdateExpression="SET eta = :e",                              # qué campo cambiar
        ExpressionAttributeValues={":e": eta.isoformat()},            # el valor nuevo
    )

    # Responderle a la app
    return {"statusCode": 200, "body": json.dumps({"km_restantes": round(km), "eta_utc": eta.isoformat()})}
