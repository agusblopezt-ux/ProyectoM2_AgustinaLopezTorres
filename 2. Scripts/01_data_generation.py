# FleetLogix - Avance 1: generación de datos sintéticos (exportado de Avance_1_DataGeneration.ipynb)
# Requiere: pip install faker pandas numpy matplotlib
# Genera los 6 CSV y carga_datos.log en la carpeta desde donde se corre.

import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from faker import Faker
import logging

fake = Faker('es_ES')
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Log de carga: cada paso queda registrado en pantalla y en el archivo carga_datos.log
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s',
                    handlers=[logging.FileHandler('carga_datos.log', mode='w', encoding='utf-8'),
                              logging.StreamHandler()], force=True)
log = logging.getLogger('fleetlogix')
log.info('Inicio de la generación de datos')


# ======================================================================
# Tabla vehicles
# ======================================================================

# Reglas de negocio para cada tipo de vehículo
vehicle_configs = [
    {'type': 'Camión Grande',  'min_cap': 8000.0, 'max_cap': 15000.0, 'fuels': ['Diesel']},
    {'type': 'Camión Mediano', 'min_cap': 3500.0, 'max_cap': 7999.0,  'fuels': ['Diesel', 'Gasolina']},
    {'type': 'Van',            'min_cap': 800.0,  'max_cap': 3499.0,  'fuels': ['Diesel', 'Gasolina', 'Eléctrico']},
    {'type': 'Motocicleta',    'min_cap': 50.0,   'max_cap': 250.0,   'fuels': ['Gasolina', 'Eléctrico']},
]

vehicles = []
used_plates = set()

# Función para asegurar que las patentes sean únicas
def generate_unique_plate():
    # Genera una patente al azar y se asegura de que no se repita
    while True:
        plate = fake.bothify(text='??###??').upper()   # letras (?) y números (#) al azar
        if plate not in used_plates:
            used_plates.add(plate)
            return plate

# Bucle para generar exactamente los 200 registros pedidos
for i in range(1, 201):
    config = random.choice(vehicle_configs)                                   # tipo de vehículo al azar
    capacity_kg = round(random.uniform(config['min_cap'], config['max_cap']), 2)  # capacidad según el tipo
    fuel_type = random.choice(config['fuels'])                                # combustible según el tipo
    acquisition_date = fake.date_between(start_date=datetime(2020, 1, 1), end_date=datetime(2024, 9, 30))
    status = np.random.choice(['active', 'maintenance', 'inactive'], p=[0.85, 0.10, 0.05])

    vehicles.append({
        'vehicle_id': i,
        'license_plate': generate_unique_plate(),
        'vehicle_type': config['type'],
        'capacity_kg': capacity_kg,
        'fuel_type': fuel_type,
        'acquisition_date': acquisition_date.strftime('%Y-%m-%d'),
        'status': status,
    })

# Convertir a DataFrame y guardar en CSV
df_vehicles = pd.DataFrame(vehicles)
df_vehicles.to_csv('vehicles.csv', index=False)
log.info(f'vehicles: {len(df_vehicles)} registros generados')
print(df_vehicles.head())


# ======================================================================
# Tabla Drivers
# ======================================================================

drivers = []
used_employee_codes = set()
used_license_numbers = set()

start_hire_date = datetime(2021, 1, 1)
end_hire_date = datetime(2026, 6, 1)

# Bucle para generar exactamente los 400 registros de conductores
for i in range(1, 401):
    # Código de empleado único
    while True:
        employee_code = f'EMP-{random.randint(1000, 9999)}'
        if employee_code not in used_employee_codes:
            used_employee_codes.add(employee_code)
            break

    # Número de licencia único
    while True:
        license_number = f'LIC-{random.randint(10000000, 99999999)}'
        if license_number not in used_license_numbers:
            used_license_numbers.add(license_number)
            break

    hire_date = start_hire_date + timedelta(days=random.randint(0, (end_hire_date - start_hire_date).days))
    # Licencia vigente: vence entre octubre 2026 y 2030 (siempre después de la contratación)
    license_expiry = datetime(2026, 10, 1) + timedelta(days=random.randint(0, 1460))

    drivers.append({
        'driver_id': i,
        'employee_code': employee_code,
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'license_number': license_number,
        'license_expiry': license_expiry.strftime('%Y-%m-%d'),
        'phone': f'+54911{random.randint(10000000, 99999999)}',
        'hire_date': hire_date.strftime('%Y-%m-%d'),
        'status': np.random.choice(['active', 'inactive'], p=[0.90, 0.10]),
    })

# Convertir a DataFrame y guardar en CSV
df_drivers = pd.DataFrame(drivers)
df_drivers.to_csv('drivers.csv', index=False)
log.info(f'drivers: {len(df_drivers)} registros generados')
print(df_drivers.head())


# ======================================================================
# Tabla Routes
# ======================================================================

random.seed(42)
np.random.seed(42)

cities = ['Buenos Aires', 'Córdoba', 'Rosario', 'Mendoza', 'San Miguel de Tucumán']

# Distancia (km), duración (h) y peaje base aproximados entre cada par de ciudades
city_distances = {
    ('Buenos Aires', 'Córdoba'): (700, 8.5, 4500),
    ('Buenos Aires', 'Rosario'): (300, 3.5, 2000),
    ('Buenos Aires', 'Mendoza'): (1050, 13.0, 6500),
    ('Buenos Aires', 'San Miguel de Tucumán'): (1250, 15.0, 7500),
    ('Córdoba', 'Rosario'): (400, 4.5, 2500),
    ('Córdoba', 'Mendoza'): (600, 7.5, 3500),
    ('Córdoba', 'San Miguel de Tucumán'): (550, 7.0, 3000),
    ('Rosario', 'Mendoza'): (850, 10.0, 5000),
    ('Rosario', 'San Miguel de Tucumán'): (950, 11.5, 5500),
    ('Mendoza', 'San Miguel de Tucumán'): (980, 12.0, 6000),
}

routes = []
route_id = 1

while route_id <= 50:                       # repetimos las 20 combinaciones hasta llegar a 50
    for c1 in cities:
        for c2 in cities:
            if c1 != c2 and route_id <= 50:  # origen y destino distintos
                pair = (c1, c2) if (c1, c2) in city_distances else (c2, c1)
                base_dist, base_dur, base_toll = city_distances[pair]
                routes.append({
                    'route_id': route_id,
                    'route_code': f'RTE-{100 + route_id}',
                    'origin_city': c1,
                    'destination_city': c2,
                    'distance_km': round(base_dist * random.uniform(0.95, 1.05), 2),
                    'estimated_duration_hours': round(base_dur * random.uniform(0.95, 1.05), 2),
                    'toll_cost': round(base_toll * random.uniform(0.90, 1.10), 2),
                })
                route_id += 1

# Convertir a DataFrame y guardar en CSV
df_routes = pd.DataFrame(routes)
df_routes.to_csv('routes.csv', index=False)
log.info(f'routes: {len(df_routes)} registros generados')
print(df_routes.head())


# ======================================================================
# Tabla Trips
# ======================================================================

def get_hourly_distribution():
    # Peso de cada hora del día (0 a 23): picos a la mañana y después del mediodía
    weights = [
        0.01, 0.01, 0.01, 0.01, 0.02, 0.04,  # 00-05
        0.09, 0.12, 0.11, 0.08, 0.06, 0.05,  # 06-11
        0.04, 0.07, 0.08, 0.06, 0.05, 0.04,  # 12-17
        0.03, 0.02, 0.02, 0.01, 0.01, 0.01,  # 18-23
    ]
    return np.array(weights) / sum(weights)   # que sumen 1 para usarlas como probabilidades


def generate_trips(n_trips=100000):
    random.seed(42)
    np.random.seed(42)

    # Datos de las tablas maestras
    vehicle_ids = df_vehicles[df_vehicles['status'] != 'inactive']['vehicle_id'].values
    route_dict = df_routes.set_index('route_id')[['estimated_duration_hours', 'distance_km']].to_dict('index')
    v_cap_dict = df_vehicles.set_index('vehicle_id')['capacity_kg'].to_dict()

    # Conductores activos ordenados por fecha de contratación
    drv = df_drivers[df_drivers['status'] == 'active'].copy()
    drv['hire_date'] = pd.to_datetime(drv['hire_date'])
    drv = drv.sort_values('hire_date')
    driver_ids = drv['driver_id'].values
    driver_hire = drv['hire_date'].values

    # 1. Sortear las salidas y ordenarlas de la más vieja a la más nueva
    start_trips = datetime(2024, 10, 1)
    end_trips = datetime(2026, 9, 30)
    total_days = (end_trips - start_trips).days
    random_days = np.random.randint(0, total_days, size=n_trips)
    selected_hours = np.random.choice(np.arange(24), size=n_trips, p=get_hourly_distribution())
    selected_minutes = np.random.randint(0, 60, size=n_trips)
    selected_r_ids = np.random.choice(list(route_dict.keys()), size=n_trips)
    departures = sorted(start_trips + timedelta(days=int(d), hours=int(h), minutes=int(m))
                        for d, h, m in zip(random_days, selected_hours, selected_minutes))

    # Hora a la que queda libre cada vehículo y cada conductor (al principio, todos libres)
    vehicle_free = np.full(len(vehicle_ids), np.datetime64(start_trips))
    driver_free = np.full(len(driver_ids), np.datetime64(start_trips))

    trips = []
    for i, dep_dt in enumerate(departures):
        dep = np.datetime64(dep_dt)

        # 2. Vehículo libre a la hora de salida
        free_v = np.flatnonzero(vehicle_free <= dep)
        # Conductor libre y ya contratado (los contratados son los primeros 'hired' de la lista)
        hired = np.searchsorted(driver_hire, dep, side='right')
        free_d = np.flatnonzero(driver_free[:hired] <= dep)
        if len(free_v) == 0 or len(free_d) == 0:
            continue                                   # si no hay nadie libre, ese viaje no se hace
        v_pos = random.choice(free_v)
        d_pos = random.choice(free_d)

        # 3. Llegada = salida + duración estimada x factor de demoras
        r_info = route_dict[selected_r_ids[i]]
        actual_dur = r_info['estimated_duration_hours'] * random.uniform(0.9, 1.3)
        arr_dt = dep_dt + timedelta(hours=actual_dur)

        # El vehículo queda ocupado hasta que vuelve; el conductor, hasta que vuelve + 8 h de descanso
        vehicle_free[v_pos] = np.datetime64(arr_dt)
        driver_free[d_pos] = np.datetime64(arr_dt + timedelta(hours=8))

        # 4. Peso y combustible
        v_cap = v_cap_dict[vehicle_ids[v_pos]]
        trips.append({
            'trip_id': len(trips) + 1,
            'vehicle_id': int(vehicle_ids[v_pos]),
            'driver_id': int(driver_ids[d_pos]),
            'route_id': int(selected_r_ids[i]),
            'departure_datetime': dep_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'arrival_datetime': arr_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'fuel_consumed_liters': round((r_info['distance_km'] / 100.0) * random.uniform(12, 32), 2),
            'total_weight_kg': round(v_cap * random.uniform(0.3, 0.95), 2),
            'status': 'completed',
        })
    return pd.DataFrame(trips)


log.info('Generando trips...')
df_trips = generate_trips()
df_trips.to_csv('trips.csv', index=False)
log.info(f'trips: {len(df_trips)} registros generados')
print(df_trips.head())

# Distribución de salidas por hora: se ven los picos de get_hourly_distribution()
pd.to_datetime(df_trips['departure_datetime']).dt.hour.value_counts().sort_index().plot(
    kind='bar', figsize=(10, 3), title='Viajes por hora de salida', xlabel='Hora', ylabel='Viajes');


# ======================================================================
# Tabla Deliveries
# ======================================================================

random.seed(42)
np.random.seed(42)

deliveries = []
delivery_id = 1
log.info('Generando deliveries...')

trip_records = df_trips[['trip_id', 'arrival_datetime', 'total_weight_kg']].to_dict('records')

for trip in trip_records:
    arr_dt = datetime.strptime(trip['arrival_datetime'], '%Y-%m-%d %H:%M:%S')

    # Cantidad de entregas del viaje: entre 2 y 6, con 4 como la más probable
    num_deliveries = np.random.choice([2, 3, 4, 5, 6], p=[0.10, 0.20, 0.40, 0.20, 0.10])

    # Repartir el peso del viaje entre sus entregas
    delivery_weights = np.random.dirichlet(np.ones(num_deliveries)) * trip['total_weight_kg']

    for j in range(num_deliveries):
        sched_dt = arr_dt + timedelta(hours=random.uniform(0.5, 12.0))         # programada después de llegar
        del_dt = sched_dt + timedelta(hours=random.uniform(-0.5, 3.0))         # a veces un poco antes o después
        if del_dt < arr_dt:                                                    # nunca antes de que llegue el camión
            del_dt = arr_dt + timedelta(minutes=random.randint(10, 180))

        status = np.random.choice(['delivered', 'failed', 'pending'], p=[0.92, 0.05, 0.03])

        deliveries.append({
            'delivery_id': delivery_id,
            'trip_id': trip['trip_id'],
            'tracking_number': f'TRK-{delivery_id:08d}{fake.bothify(text="??").upper()}',  # único por construcción
            'customer_name': fake.name(),
            'delivery_address': fake.street_address(),
            'package_weight_kg': round(delivery_weights[j], 2),
            'scheduled_datetime': sched_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'delivered_datetime': del_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'delivery_status': status,
            'recipient_signature': fake.name() if status == 'delivered' else 'N/A',
        })
        delivery_id += 1

df_deliveries = pd.DataFrame(deliveries)
df_deliveries.to_csv('deliveries.csv', index=False)
log.info(f'deliveries: {len(df_deliveries)} registros generados')
print(df_deliveries.head())


# ======================================================================
# Tabla Maintenance
# ======================================================================

random.seed(42)
np.random.seed(42)

maint_types = ['Cambio de aceite', 'Revisión de frenos', 'Cambio de llantas',
               'Mantenimiento general', 'Revisión de motor', 'Alineación y balanceo']
cost_ranges = {   # costo en pesos según el tipo de trabajo
    'Cambio de aceite': (40000, 90000),
    'Revisión de frenos': (60000, 150000),
    'Cambio de llantas': (150000, 400000),
    'Mantenimiento general': (100000, 250000),
    'Revisión de motor': (200000, 600000),
    'Alineación y balanceo': (30000, 70000),
}
last_names = ['Gómez', 'Pérez', 'Rodríguez', 'Fernández', 'López', 'Martínez', 'González', 'García']

sampled_trips = df_trips.sample(n=5000, random_state=42).sort_values('departure_datetime')

maintenance_records = []
log.info('Generando maintenance...')
for idx, (_, trip) in enumerate(sampled_trips.iterrows(), start=1):
    arr_dt = datetime.strptime(trip['arrival_datetime'], '%Y-%m-%d %H:%M:%S')
    maint_type = random.choice(maint_types)
    maintenance_records.append({
        'maintenance_id': idx,
        'vehicle_id': int(trip['vehicle_id']),
        'trip_id': int(trip['trip_id']),
        'maintenance_date': (arr_dt + timedelta(hours=random.randint(2, 48))).strftime('%Y-%m-%d %H:%M:%S'),
        'maintenance_type': maint_type,
        'cost': round(random.uniform(*cost_ranges[maint_type]), 2),
        'workshop_name': f'Taller Mecánico {random.choice(last_names)}',
        'description': f'Realizado {maint_type.lower()} preventivo/correctivo tras operación de ruta.',
    })

df_maint = pd.DataFrame(maintenance_records)
df_maint.to_csv('maintenance.csv', index=False)
log.info(f'maintenance: {len(df_maint)} registros generados')
print(df_maint.head())


# ======================================================================
# Relaciones y constraints del modelo
# ======================================================================


# ======================================================================
# Control de calidad
# ======================================================================

def control(nombre, condicion):
    # Registra el resultado de un control en el log
    if condicion:
        log.info(f'OK    | {nombre}')
    else:
        log.error(f'ERROR | {nombre}')
    return condicion

dep = pd.to_datetime(df_trips['departure_datetime'])
arr = pd.to_datetime(df_trips['arrival_datetime'])
hire = df_trips.merge(df_drivers[['driver_id', 'hire_date']], on='driver_id')['hire_date'].pipe(pd.to_datetime)
def sin_superposicion(columna, horas_descanso):
    # Ordena los viajes de cada conductor (o vehículo) y compara cada salida con la llegada del viaje anterior
    t = df_trips.sort_values([columna, 'departure_datetime'])
    llegada_anterior = pd.to_datetime(t.groupby(columna)['arrival_datetime'].shift())
    libre_desde = llegada_anterior + pd.Timedelta(hours=horas_descanso)
    return (pd.to_datetime(t['departure_datetime']) >= libre_desde).where(llegada_anterior.notna(), True).all()

maint_vs_trip = df_maint.merge(df_trips[['trip_id', 'vehicle_id', 'arrival_datetime']], on='trip_id', suffixes=('', '_trip'))

resultados = [
    # Integridad referencial: toda clave foránea existe en su tabla padre
    control('trips.vehicle_id existe en vehicles', df_trips['vehicle_id'].isin(df_vehicles['vehicle_id']).all()),
    control('trips.driver_id existe en drivers', df_trips['driver_id'].isin(df_drivers['driver_id']).all()),
    control('trips.route_id existe en routes', df_trips['route_id'].isin(df_routes['route_id']).all()),
    control('deliveries.trip_id existe en trips', df_deliveries['trip_id'].isin(df_trips['trip_id']).all()),
    control('maintenance.trip_id existe en trips', df_maint['trip_id'].isin(df_trips['trip_id']).all()),
    control('maintenance.vehicle_id es el vehículo del viaje', (maint_vs_trip['vehicle_id'] == maint_vs_trip['vehicle_id_trip']).all()),
    # Consistencia temporal
    control('arrival_datetime > departure_datetime en todos los viajes', (arr > dep).all()),
    control('ningún conductor maneja antes de ser contratado', (dep.values >= hire.values).all()),
    control('ningún conductor hace dos viajes a la vez (8 h de descanso)', sin_superposicion('driver_id', 8)),
    control('ningún vehículo hace dos viajes a la vez', sin_superposicion('vehicle_id', 0)),
    control('el mantenimiento es posterior a la llegada del viaje',
            (pd.to_datetime(maint_vs_trip['maintenance_date']) > pd.to_datetime(maint_vs_trip['arrival_datetime'])).all()),
    # Claves únicas
    control('license_plate sin repetidos', df_vehicles['license_plate'].is_unique),
    control('employee_code y license_number sin repetidos', df_drivers['employee_code'].is_unique and df_drivers['license_number'].is_unique),
    control('tracking_number sin repetidos', df_deliveries['tracking_number'].is_unique),
    # Cantidades
    control('entre 2 y 6 entregas por viaje', df_deliveries.groupby('trip_id').size().between(2, 6).all()),
]

total = sum(len(df) for df in [df_vehicles, df_drivers, df_routes, df_trips, df_deliveries, df_maint])
log.info(f'Total de registros generados: {total:,}'.replace(',', '.'))
log.info(f'Controles OK: {sum(resultados)} de {len(resultados)}')


# ======================================================================
# Conclusiones
# ======================================================================
