-- FleetLogix - Avance 2: índices de optimización (PostgreSQL, base fleet_logix_bd)

-- Q6, Q4 y Q12: ordenar y filtrar viajes por fecha de salida (índice básico de la consigna)
CREATE INDEX IF NOT EXISTS idx_trips_departure ON trips(departure_datetime);

-- Q4 y Q9: unir viajes con conductores
CREATE INDEX IF NOT EXISTS idx_trips_driver_departure ON trips(driver_id, departure_datetime);

-- Q3 y Q5: mantenimientos de cada vehículo
CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle_date ON maintenance(vehicle_id, maintenance_date);

-- Q4 y Q9: unir entregas con viajes
CREATE INDEX IF NOT EXISTS idx_deliveries_trip ON deliveries(trip_id);

-- Q3: filtrar vehículos activos (índice básico de la consigna)
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status);

-- Actualizar estadísticas para que PostgreSQL use los índices
ANALYZE;

-- Para medir una query antes y después:  EXPLAIN ANALYZE <query>;
