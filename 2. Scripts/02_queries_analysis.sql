-- FleetLogix - Avance 2: 8 de las 12 queries de análisis (PostgreSQL, base fleet_logix_bd)
-- Selección: las 3 básicas (1, 2, 3), la 4 y la 5, la 6 (de 6, 7 u 8), la 9 y la 12 (de 10, 11 o 12)

-- Query 1 (básica): Cantidad de conductores activos
-- Problema de negocio: Saber cuántos conductores están disponibles para asignarles viajes.
SELECT status AS estado_conductor, COUNT(*) AS total_conductores
FROM drivers
WHERE status = 'active'
GROUP BY status;

-- Query 2 (básica): Rutas con kilometraje mayor al promedio
-- Problema de negocio: Identificar las rutas largas, que son las que más combustible, peajes y horas de manejo consumen.
SELECT route_code,
       origin_city || ' -> ' || destination_city AS trayecto,
       distance_km
FROM routes
WHERE distance_km > (SELECT AVG(distance_km) FROM routes)
ORDER BY distance_km DESC;

-- Query 3 (básica): Vehículos activos con su última fecha de mantenimiento
-- Problema de negocio: Ver cuándo se le hizo el último mantenimiento a cada vehículo activo, para planificar el próximo.
SELECT v.vehicle_id, v.license_plate, v.vehicle_type,
       MAX(m.maintenance_date) AS ultima_fecha_mantenimiento
FROM vehicles v
LEFT JOIN maintenance m ON v.vehicle_id = m.vehicle_id
WHERE v.status = 'active'
GROUP BY v.vehicle_id, v.license_plate, v.vehicle_type
ORDER BY ultima_fecha_mantenimiento DESC;

-- Query 4 (intermedia): Promedio de entregas por conductor en los últimos 6 meses
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

-- Query 5 (intermedia): Vehículos con más de 30 mantenimientos
-- Problema de negocio: Detectar los vehículos que pasan más veces por el taller, candidatos a revisión o reemplazo.
SELECT v.vehicle_id, v.license_plate,
       COUNT(m.maintenance_id) AS total_mantenimientos
FROM vehicles v
JOIN maintenance m ON v.vehicle_id = m.vehicle_id
GROUP BY v.vehicle_id, v.license_plate
HAVING COUNT(m.maintenance_id) > 30
ORDER BY total_mantenimientos DESC;

-- Query 6 (intermedia): Detalle de viajes con ruta, vehículo y conductor
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

-- Query 9 (compleja): Ranking de eficiencia de conductores
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

-- Query 12 (compleja): Vehículos sin viajes en el último mes
-- Problema de negocio: Detectar vehículos parados, que generan costo sin producir.
SELECT vehicle_id, license_plate, vehicle_type, status
FROM vehicles
WHERE vehicle_id NOT IN (
    SELECT DISTINCT vehicle_id
    FROM trips
    WHERE departure_datetime >= (SELECT MAX(departure_datetime) FROM trips) - INTERVAL '1 month'
);
