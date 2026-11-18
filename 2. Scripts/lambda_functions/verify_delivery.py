# Lambda 1: verificar si una entrega se completó
# Se ejecuta cuando la app hace POST /deliveries/complete

import json                                   # para leer y escribir JSON
from datetime import datetime                 # para saber la fecha y hora actual
import boto3                                  # librería de Python para usar servicios de AWS

s3 = boto3.client("s3")                       # conexión a S3 (donde guardamos el histórico)
dynamodb = boto3.resource("dynamodb")         # conexión a DynamoDB (estado actual)
tabla = dynamodb.Table("fleetlogix-delivery-status")   # la tabla con el estado de cada entrega


def entrega_completada(entrega):
    """Regla de negocio: devuelve True si la entrega se completó."""
    estado_ok = entrega.get("delivery_status") == "delivered"         # el estado tiene que ser 'delivered'
    firma = entrega.get("recipient_signature") or ""                  # firma del que recibió (vacía si no hay)
    firma_ok = firma.strip() not in ("", "N/A")                       # tiene que haber una firma real
    fecha_ok = bool(entrega.get("delivered_datetime"))                # tiene que tener fecha de entrega
    return estado_ok and firma_ok and fecha_ok                        # las tres cosas a la vez


def lambda_handler(event, context):
    entrega = json.loads(event["body"])                               # el JSON que mandó la app
    completada = entrega_completada(entrega)                          # aplicamos la regla
    ahora = datetime.utcnow()                                         # fecha y hora actual (UTC)

    # 1. Guardar el evento en S3, en una carpeta por fecha
    ruta = f"raw/deliveries/year={ahora:%Y}/month={ahora:%m}/day={ahora:%d}/delivery_{entrega['delivery_id']}.json"
    s3.put_object(Bucket="fleetlogix-datalake", Key=ruta, Body=json.dumps(entrega))

    # 2. Guardar el estado actual en DynamoDB (si ya existía, se reemplaza)
    tabla.put_item(Item={
        "delivery_id": entrega["delivery_id"],                        # clave de la tabla
        "delivery_status": entrega["delivery_status"],                # estado que mandó la app
        "completada": completada,                                     # resultado de la regla
        "updated_at": ahora.isoformat(),                              # cuándo se actualizó
    })

    # 3. Responderle a la app
    return {"statusCode": 200, "body": json.dumps({"delivery_id": entrega["delivery_id"], "completada": completada})}
