# FleetLogix - Avance 3: pipeline ETL PostgreSQL -> Snowflake (exportado de Avance_3_DataWarehouse.ipynb)
# Requiere: pip install sqlalchemy psycopg2-binary snowflake-connector-python pandas
# Se corre desde la carpeta donde está 04_dimensional_model.sql

import getpass
import pandas as pd
from sqlalchemy import create_engine
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas


# ======================================================================
# 1. EXTRACCIÓN DESDE POSTGRESQL
# ======================================================================

clave_pg = getpass.getpass('Contraseña de PostgreSQL: ')
pg_url = f"postgresql+psycopg2://postgres:{clave_pg}@localhost:5432/fleet_logix_bd"
engine = create_engine(pg_url)

df_vehicles = pd.read_sql("SELECT * FROM vehicles", engine)
df_drivers = pd.read_sql("SELECT * FROM drivers", engine)
df_routes = pd.read_sql("SELECT * FROM routes", engine)
df_trips = pd.read_sql("SELECT trip_id, vehicle_id, driver_id, route_id FROM trips", engine)
df_deliveries = pd.read_sql("SELECT * FROM deliveries", engine)

print(f"✔️ Extracción exitosa: {len(df_deliveries)} entregas y {len(df_trips)} viajes leídos.")


# ======================================================================
# 2. TRANSFORMACIÓN
# ======================================================================

# --- Dimensiones de vehículos, conductores y rutas ---

dim_vehicle = df_vehicles.copy()
dim_route = df_routes.copy()

dim_driver = df_drivers.copy()
dim_driver['full_name'] = dim_driver['first_name'] + ' ' + dim_driver['last_name']
dim_driver = dim_driver[['driver_id', 'employee_code', 'full_name', 'license_number',
                         'license_expiry', 'hire_date', 'status']]

# --- Tabla de hechos: cada entrega con su vehículo, conductor y ruta ---

fact = df_deliveries.merge(df_trips, on='trip_id', how='left')
fact = fact.merge(df_routes[['route_id', 'destination_city']], on='route_id', how='left')

# --- Dimensión de clientes ---

dim_customer = fact[['customer_name', 'destination_city']].drop_duplicates('customer_name').reset_index(drop=True)
dim_customer['customer_key'] = dim_customer.index + 1          # 1, 2, 3, ...
dim_customer = dim_customer.rename(columns={'destination_city': 'city'})
dim_customer = dim_customer[['customer_key', 'customer_name', 'city']]

# Le pongo a cada entrega el número de su cliente
fact = fact.merge(dim_customer[['customer_name', 'customer_key']], on='customer_name', how='left')
print(f"{len(dim_customer)} clientes distintos")

# --- Dimensiones de fecha y horario ---

fact['scheduled_datetime'] = pd.to_datetime(fact['scheduled_datetime'])
fact['delivered_datetime'] = pd.to_datetime(fact['delivered_datetime'])

# Claves de fecha (AAAAMMDD) y de hora (0 a 23) de cada entrega, según cuándo estaba programada
fact['date_key'] = fact['scheduled_datetime'].dt.strftime('%Y%m%d').astype(int)
fact['time_key'] = fact['scheduled_datetime'].dt.hour

dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

fechas = pd.date_range(fact['scheduled_datetime'].min().normalize(), fact['scheduled_datetime'].max().normalize())
dim_date = pd.DataFrame({'full_date': fechas})
dim_date['date_key'] = dim_date['full_date'].dt.strftime('%Y%m%d').astype(int)
dim_date['day_of_week'] = dim_date['full_date'].dt.dayofweek + 1            # 1 = lunes
dim_date['day_name'] = dim_date['full_date'].dt.dayofweek.map(lambda d: dias[d])
dim_date['is_weekend'] = dim_date['day_of_week'] >= 6
dim_date['week_of_year'] = dim_date['full_date'].dt.isocalendar().week.astype(int)
dim_date['month'] = dim_date['full_date'].dt.month
dim_date['month_name'] = dim_date['month'].map(lambda m: meses[m - 1])
dim_date['quarter'] = dim_date['full_date'].dt.quarter
dim_date['year'] = dim_date['full_date'].dt.year
dim_date['full_date'] = dim_date['full_date'].dt.date                       # fecha sin hora
dim_date = dim_date[['date_key', 'full_date', 'day_of_week', 'day_name', 'is_weekend',
                     'week_of_year', 'month', 'month_name', 'quarter', 'year']]


def franja(hora):
    # Franja del día según la hora
    if hora < 6:
        return 'Madrugada'
    elif hora < 12:
        return 'Mañana'
    elif hora < 19:
        return 'Tarde'
    else:
        return 'Noche'


dim_time = pd.DataFrame({'time_key': range(24)})
dim_time['hour_label'] = dim_time['time_key'].map(lambda h: f'{h:02d}:00')
dim_time['time_of_day'] = dim_time['time_key'].map(franja)

print(f"{len(dim_date)} días y {len(dim_time)} horas")

# --- Métricas de cada entrega ---

fact['delay_minutes'] = ((fact['delivered_datetime'] - fact['scheduled_datetime']).dt.total_seconds() / 60).round().astype(int)
fact['is_on_time'] = (fact['delivery_status'] == 'delivered') & (fact['delay_minutes'] <= 30)
fact['is_signed'] = fact['recipient_signature'].astype(bool)

fact = fact[['delivery_id', 'date_key', 'time_key', 'vehicle_id', 'driver_id', 'route_id', 'customer_key',
             'trip_id', 'tracking_number', 'delivery_status', 'scheduled_datetime', 'delivered_datetime',
             'package_weight_kg', 'delay_minutes', 'is_on_time', 'is_signed']]
print(fact.head())

# --- Control de calidad antes de cargar ---

controles = {
    'una fila por entrega': len(fact) == len(df_deliveries),
    'sin claves vacías': fact[['date_key', 'time_key', 'vehicle_id', 'driver_id', 'route_id', 'customer_key']].notna().all().all(),
    'date_key existe en DIM_DATE': fact['date_key'].isin(dim_date['date_key']).all(),
    'vehicle_id existe en DIM_VEHICLE': fact['vehicle_id'].isin(dim_vehicle['vehicle_id']).all(),
    'driver_id existe en DIM_DRIVER': fact['driver_id'].isin(dim_driver['driver_id']).all(),
    'route_id existe en DIM_ROUTE': fact['route_id'].isin(dim_route['route_id']).all(),
    'customer_key existe en DIM_CUSTOMER': fact['customer_key'].isin(dim_customer['customer_key']).all(),
}
for nombre, ok in controles.items():
    print(('✔️ ' if ok else '❌ ') + nombre)

# Snowflake guarda los nombres en MAYÚSCULAS. Las fechas con hora se pasan como texto para que se carguen bien.
for col in ['scheduled_datetime', 'delivered_datetime']:
    fact[col] = fact[col].dt.strftime('%Y-%m-%d %H:%M:%S')

tablas = {'DIM_DATE': dim_date, 'DIM_TIME': dim_time, 'DIM_VEHICLE': dim_vehicle, 'DIM_DRIVER': dim_driver,
          'DIM_ROUTE': dim_route, 'DIM_CUSTOMER': dim_customer, 'FACT_DELIVERIES': fact}
for df in tablas.values():
    df.columns = [col.upper() for col in df.columns]


# ======================================================================
# 3. CARGA EN SNOWFLAKE
# ======================================================================

print("☁️ Conectando a Snowflake para la carga masiva...")
ctx = snowflake.connector.connect(
    user='etl_user',
    password=getpass.getpass('Contraseña de Snowflake: '),
    account='nzuyhke-oc72550',
    warehouse='FLEET_WH',
    database='FLEET_DW',
    schema='ANALYTICAL_CORE'
)

try:
    # Crear las tablas y las vistas (borra las anteriores y las vuelve a crear vacías)
    with open('04_dimensional_model.sql', encoding='utf-8') as archivo:
        ctx.execute_string(archivo.read())
    print("✔️ Tablas y vistas creadas.")

    print("📤 Subiendo dimensiones y tabla de hechos...", flush=True)
    for nombre, df in tablas.items():
        write_pandas(ctx, df, nombre, auto_create_table=False, overwrite=True, quote_identifiers=False)
        print(f"✔️ {nombre} cargada: {len(df)} filas.")

    # Verificación: las vistas seguras unen los hechos con las dimensiones
    cur = ctx.cursor()
    for vista in ['VW_SECURE_OPERATIONS', 'VW_SECURE_CUSTOMERS']:
        cur.execute(f'SELECT COUNT(*) FROM {vista}')
        print(f"🔎 {vista}: {cur.fetchone()[0]} filas")

    print("🎉 ¡Pipeline ETL completo ejecutado de punta a punta con éxito!")

except Exception as e:
    print(f"❌ Error durante la carga a Snowflake: {e}")

finally:
    ctx.close()
