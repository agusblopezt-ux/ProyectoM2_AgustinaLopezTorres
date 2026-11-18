# Lambda 3: enviar una alerta si el camión se desvía de su ruta
# Se ejecuta cuando la app hace POST /telemetry/location (cada 5 minutos)

import json                                   # para leer y escribir JSON
import math                                   # para calcular distancias
from datetime import datetime                 # para saber la fecha y hora actual
import boto3                                  # librería de Python para usar servicios de AWS

s3 = boto3.client("s3")                       # conexión a S3 (histórico)
sns = boto3.client("sns")                     # conexión a SNS (envío de alertas)
TOPICO_ALERTAS = "arn:aws:sns:us-east-1:123456789012:fleetlogix-route-alerts"   # a dónde se mandan
UMBRAL_KM = 50                                # más de 50 km fuera de la ruta = desvío

CIUDADES = {              # coordenadas (latitud, longitud) de las 5 ciudades de la tabla routes
    "Buenos Aires": (-34.6037, -58.3816),
    "Córdoba": (-31.4201, -64.1888),
    "Rosario": (-32.9442, -60.6505),
    "Mendoza": (-32.8895, -68.8458),
    "San Miguel de Tucumán": (-26.8083, -65.2176),
}


def a_km(lat, lon):
    """Pasa latitud y longitud a kilómetros (aproximación que sirve dentro de Argentina)."""
    return lon * 111.32 * math.cos(math.radians(-32)), lat * 110.57


def distancia_a_ruta_km(lat, lon, origen, destino):
    """Distancia en km entre el camión y la línea recta origen -> destino."""
    px, py = a_km(lat, lon)                                           # el camión
    ax, ay = a_km(*CIUDADES[origen])                                  # la ciudad de origen
    bx, by = a_km(*CIUDADES[destino])                                 # la ciudad de destino
    dx, dy = bx - ax, by - ay                                         # dirección de la ruta
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)       # punto más cercano (0 = origen, 1 = destino)
    t = max(0, min(1, t))                                             # que no se salga del tramo
    cx, cy = ax + t * dx, ay + t * dy                                 # coordenadas de ese punto
    return math.hypot(px - cx, py - cy)                               # distancia camión -> ruta


def lambda_handler(event, context):
    gps = json.loads(event["body"])                                   # el JSON que mandó la app
    ahora = datetime.utcnow()                                         # fecha y hora actual (UTC)

    # 1. Guardar la posición en S3, en una carpeta por fecha
    ruta = f"raw/telemetry/year={ahora:%Y}/month={ahora:%m}/day={ahora:%d}/trip_{gps['trip_id']}_{ahora:%H%M%S}.json"
    s3.put_object(Bucket="fleetlogix-datalake", Key=ruta, Body=json.dumps(gps))

    # 2. Calcular el desvío
    desvio = distancia_a_ruta_km(gps["lat"], gps["lon"], gps["origin_city"], gps["destination_city"])

    # 3. Si se pasa del umbral, mandar alerta por SNS (llega por email al centro de control)
    if desvio > UMBRAL_KM:
        sns.publish(
            TopicArn=TOPICO_ALERTAS,
            Subject=f"Desvío en viaje {gps['trip_id']}",
            Message=f"El vehículo {gps['vehicle_id']} está a {desvio:.0f} km de su ruta.",
        )

    # 4. Responderle a la app
    return {"statusCode": 200, "body": json.dumps({"desvio_km": round(desvio, 1), "alerta": desvio > UMBRAL_KM})}
