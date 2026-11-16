-- ==============================================================================
-- PROYECTO INTEGRADOR: FLEETLOGIX - AVANCE 2: ANÁLISIS Y OPTIMIZACIÓN SQL
-- ==============================================================================


-- ==============================================================================
-- 1. QUERIES BÁSICAS (3 queries)
-- ==============================================================================

-- 1. Cantidad de empleados (conductores) activos
SELECT 
    status AS estado_conductor,
    COUNT(*) AS total_conductores
FROM drivers
WHERE status = 'active'
GROUP BY status;

-- 2. Rutas con un kilometraje superior al promedio
SELECT 
    route_code,
    origin_city || ' -> ' || destination_city AS trayecto,
    distance_km
FROM routes
WHERE distance_km > (SELECT AVG(distance_km) FROM routes);

-- 3. Listar vehículos activos con su última fecha de mantenimiento
SELECT 
    v.vehicle_id,
    v.plate,
    v.model,
    MAX(m.maintenance_date) AS ultima_fecha_mantenimiento
FROM vehicles v
LEFT JOIN maintenance m ON v.vehicle_id = m.vehicle_id
WHERE v.status = 'active'
GROUP BY v.vehicle_id, v.plate, v.model;


-- ==============================================================================
-- 2. QUERIES INTERMEDIAS (5 queries)
-- ==============================================================================

-- 4. Promedio de entregas por conductor en los últimos 6 meses
SELECT 
    d.driver_id,
    d.first_name || ' ' || d.last_name AS nombre_conductor,
    COUNT(del.delivery_id) AS total_entregas
FROM drivers d
JOIN trips t ON d.driver_id = t.driver_id
JOIN deliveries del ON t.trip_id = del.trip_id
WHERE del.delivery_date >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY d.driver_id, d.first_name, d.last_name;

-- 5. Vehículos que superan las 50 reparaciones o mantenimientos registrados
SELECT 
    v.vehicle_id,
    v.plate,
    COUNT(m.maintenance_id) AS total_mantenimientos
FROM vehicles v
JOIN maintenance m ON v.vehicle_id = m.vehicle_id
GROUP BY v.vehicle_id, v.plate
HAVING COUNT(m.maintenance_id) > 50;

-- 6. Detalle completo de viajes con información de ruta y vehículo
SELECT 
    t.trip_id,
    v.plate AS vehiculo,
    d.first_name || ' ' || d.last_name AS conductor,
    r.route_code,
    r.origin_city,
    r.destination_city,
    t.start_time
FROM trips t
JOIN vehicles v ON t.vehicle_id = v.vehicle_id
JOIN drivers d ON t.driver_id = d.driver_id
JOIN routes r ON t.route_id = r.route_id;

-- 7. Conteo de entregas según su estado actual
SELECT 
    status AS estado_entrega,
    COUNT(*) AS cantidad
FROM deliveries
GROUP BY status;

-- 8. Rutas más utilizadas ordenadas por cantidad de viajes realizados
SELECT 
    r.route_code,
    r.origin_city || ' -> ' || r.destination_city AS trayecto,
    COUNT(t.trip_id) AS total_viajes
FROM routes r
JOIN trips t ON r.route_id = t.route_id
GROUP BY r.route_code, r.origin_city, r.destination_city
ORDER BY total_viajes DESC;


-- ==============================================================================
-- 3. QUERIES COMPLEJAS (4 queries)
-- ==============================================================================

-- 9. Ranking de eficiencia de conductores basado en entregas exitosas
WITH ConductorEntregas AS (
    SELECT 
        d.driver_id,
        d.first_name || ' ' || d.last_name AS conductor,
        COUNT(del.delivery_id) AS total_entregas,
        SUM(CASE WHEN del.status = 'delivered' THEN 1 ELSE 0 END) AS entregas_exitosas
    FROM drivers d
    JOIN trips t ON d.driver_id = t.driver_id
    JOIN deliveries del ON t.trip_id = del.trip_id
    GROUP BY d.driver_id, d.first_name, d.last_name
)
SELECT 
    conductor,
    total_entregas,
    entregas_exitosas,
    ROUND((entregas_exitosas::NUMERIC / NULLIF(total_entregas, 0)) * 100, 2) AS porcentaje_exito,
    RANK() OVER (ORDER BY (entregas_exitosas::NUMERIC / NULLIF(total_entregas, 0)) DESC) as ranking_eficiencia
FROM ConductorEntregas;

-- 10. Análisis secuencial de tiempo entre viajes consecutivos por conductor (LAG)
SELECT 
    driver_id,
    trip_id,
    start_time,
    LAG(start_time, 1) OVER (PARTITION BY driver_id ORDER BY start_time) AS viaje_anterior,
    start_time - LAG(start_time, 1) OVER (PARTITION BY driver_id ORDER BY start_time) AS tiempo_descanso
FROM trips;

-- 11. Costo acumulado de mantenimiento por vehículo utilizando Window Functions
SELECT 
    v.vehicle_id,
    v.plate,
    m.maintenance_date,
    m.cost,
    SUM(m.cost) OVER (PARTITION BY v.vehicle_id ORDER BY m.maintenance_date) AS costo_acumulado
FROM vehicles v
JOIN maintenance m ON v.vehicle_id = m.vehicle_id;

-- 12. Identificación de vehículos que no han realizado viajes en el último mes
SELECT 
    vehicle_id,
    plate,
    model
FROM vehicles
WHERE vehicle_id NOT IN (
    SELECT DISTINCT vehicle_id 
    FROM trips 
    WHERE start_time >= CURRENT_DATE - INTERVAL '1 month'
);