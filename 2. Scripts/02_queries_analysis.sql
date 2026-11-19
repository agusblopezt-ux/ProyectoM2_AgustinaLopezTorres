-- FleetLogix - Avance 2: 12 queries de análisis (PostgreSQL, base fleet_logix_bd)
-- Seleccionadas para el análisis de rendimiento (8): las 3 básicas (1, 2, 3), la 4 y la 5, la 6 (de 6, 7 u 8), la 9 y la 12 (de 10, 11 o 12)

-- Query 1 (básica) [SELECCIONADA]: Cantidad de conductores activos
-- Problema de negocio: Saber cuántos conductores están disponibles para asignarles viajes.
SELECT status AS estado_conductor, COUNT(*) AS total_conductores
FROM drivers
WHERE status = 'active'
GROUP BY status;

-- Query 2 (básica) [SELECCIONADA]: Rutas con kilometraje mayor al promedio
-- Problema de negocio: Identificar las rutas largas, que son las que más combustible, peajes y horas de manejo consumen.
SELECT route_code,
       origin_city || ' -> ' || destination_city AS trayecto,
       distance_km
FROM routes
WHERE distance_km > (SELECT AVG(distance_km) FROM routes)
ORDER BY distance_km DESC;

-- Query 3 (básica) [SELECCIONADA]: Vehículos activos con su última fecha de mantenimiento
-- Problema de negocio: Ver cuándo se le hizo el último mantenimiento a cada vehículo activo, para planificar el próximo.
SELECT v.vehicle_id, v.license_plate, v.vehicle_type,
       MAX(m.maintenance_date) AS ultima_fecha_mantenimiento
FROM vehicles v
LEFT JOIN maintenance m ON v.vehicle_id = m.vehicle_id
WHERE v.status = 'active'
GROUP BY v.vehicle_id, v.license_plate, v.vehicle_type
ORDER BY ultima_fecha_mantenimiento DESC;

-- Query 4 (intermedia) [SELECCIONADA]: Promedio de entregas por conductor en los últimos 6 meses
-- Problema de negocio: Medir la carga de trabajo reciente de cada conductor.
SELECT d.driver_id,
       d.first_name || ' ' || d.last_name AS conductor,
       COUNT(DISTINCT t.trip_id) AS viajes,
       COUNT(del.delivery_id) AS entregas,
       ROUND(COUNT(del.delivery_id)::NUMERIC / COUNT(DISTINCT t.trip_id), 2) AS promedio_entregas_por_viaje
FROM drivers d
JOIN trips t ON d.driver_id = t.driver_id
JOIN deliveries del ON t.trip_id = del.trip_id
WHERE t.departure_datetime >= (SELECT MAX(departure_datetime) FROM trips) - INTERVAL '6 months'
GROUP BY d.driver_id, d.first_name, d.last_name
ORDER BY entregas DESC;

-- Query 5 (intermedia) [SELECCIONADA]: Vehículos con más de 30 mantenimientos
-- Problema de negocio: Detectar los vehículos que pasan más veces por el taller, candidatos a revisión o reemplazo.
SELECT v.vehicle_id, v.license_plate,
       COUNT(m.maintenance_id) AS total_mantenimientos
FROM vehicles v
JOIN maintenance m ON v.vehicle_id = m.vehicle_id
GROUP BY v.vehicle_id, v.license_plate
HAVING COUNT(m.maintenance_id) > 30
ORDER BY total_mantenimientos DESC;

-- Query 6 (intermedia) [SELECCIONADA]: Detalle de viajes con ruta, vehículo y conductor
-- Problema de negocio: Tener en una sola tabla la información completa de cada viaje, uniendo 4 tablas.
SELECT t.trip_id,
       v.license_plate AS vehiculo,
       d.first_name || ' ' || d.last_name AS conductor,
       r.route_code, r.origin_city, r.destination_city,
       t.departure_datetime
FROM trips t
JOIN vehicles v ON t.vehicle_id = v.vehicle_id
JOIN drivers d ON t.driver_id = d.driver_id
JOIN routes r ON t.route_id = r.route_id
ORDER BY t.departure_datetime DESC
LIMIT 100;

-- Query 7 (intermedia): Cantidad de entregas según su estado
-- Problema de negocio: Medir el nivel de servicio: cuántas entregas se completan, fallan o quedan pendientes.
SELECT delivery_status AS estado_entrega, COUNT(*) AS cantidad
FROM deliveries
GROUP BY delivery_status
ORDER BY cantidad DESC;

-- Query 8 (intermedia): Rutas más usadas
-- Problema de negocio: Saber qué rutas concentran más viajes para priorizar recursos en ellas.
SELECT r.route_code,
       r.origin_city || ' -> ' || r.destination_city AS trayecto,
       COUNT(t.trip_id) AS total_viajes
FROM routes r
JOIN trips t ON r.route_id = t.route_id
GROUP BY r.route_code, r.origin_city, r.destination_city
ORDER BY total_viajes DESC;

-- Query 9 (compleja) [SELECCIONADA]: Ranking de eficiencia de conductores
-- Problema de negocio: Comparar a los conductores por su porcentaje de entregas exitosas.
WITH conductor_entregas AS (
    SELECT d.driver_id,
           d.first_name || ' ' || d.last_name AS conductor,
           COUNT(del.delivery_id) AS total_entregas,
           SUM(CASE WHEN del.delivery_status = 'delivered' THEN 1 ELSE 0 END) AS entregas_exitosas
    FROM drivers d
    JOIN trips t ON d.driver_id = t.driver_id
    JOIN deliveries del ON t.trip_id = del.trip_id
    GROUP BY d.driver_id, d.first_name, d.last_name
)
SELECT conductor, total_entregas, entregas_exitosas,
       ROUND(entregas_exitosas::NUMERIC / total_entregas * 100, 2) AS porcentaje_exito,
       RANK() OVER (ORDER BY entregas_exitosas::NUMERIC / total_entregas DESC) AS ranking_eficiencia
FROM conductor_entregas
ORDER BY ranking_eficiencia;

-- Query 10 (compleja): Tiempo de descanso entre viajes de un conductor
-- Problema de negocio: Controlar que los conductores descansen entre un viaje y el siguiente.
SELECT driver_id, trip_id, departure_datetime,
       LAG(arrival_datetime) OVER (PARTITION BY driver_id ORDER BY departure_datetime) AS llegada_viaje_anterior,
       departure_datetime - LAG(arrival_datetime) OVER (PARTITION BY driver_id ORDER BY departure_datetime) AS tiempo_descanso
FROM trips
WHERE driver_id = 25
ORDER BY departure_datetime;

-- Query 11 (compleja): Costo acumulado de mantenimiento de un vehículo
-- Problema de negocio: Ver cómo crece en el tiempo lo que se gasta en mantener un vehículo.
SELECT v.vehicle_id, v.license_plate, m.maintenance_date, m.cost,
       SUM(m.cost) OVER (PARTITION BY v.vehicle_id ORDER BY m.maintenance_date) AS costo_acumulado
FROM vehicles v
JOIN maintenance m ON v.vehicle_id = m.vehicle_id
WHERE v.vehicle_id = 10
ORDER BY m.maintenance_date;

-- Query 12 (compleja) [SELECCIONADA]: Vehículos sin viajes en el último mes
-- Problema de negocio: Detectar vehículos parados, que generan costo sin producir.
SELECT vehicle_id, license_plate, vehicle_type, status
FROM vehicles
WHERE vehicle_id NOT IN (
    SELECT DISTINCT vehicle_id
    FROM trips
    WHERE departure_datetime >= (SELECT MAX(departure_datetime) FROM trips) - INTERVAL '1 month'
);
