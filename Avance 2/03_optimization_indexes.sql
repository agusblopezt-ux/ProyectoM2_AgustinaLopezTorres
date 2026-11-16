-- FleetLogix - Avance 2: índices de optimización (PostgreSQL, base fleet_logix_bd)

-- Q6, Q12 y Q4: ordenar y filtrar viajes por fecha de salida
CREATE INDEX IF NOT EXISTS idx_trips_departure ON trips(departure_datetime);

-- Q10: viajes de un conductor ordenados por fecha
CREATE INDEX IF NOT EXISTS idx_trips_driver_departure ON trips(driver_id, departure_datetime);

-- Q11 y Q3: mantenimientos de un vehículo ordenados por fecha
CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle_date ON maintenance(vehicle_id, maintenance_date);

-- Q7: contar entregas por estado
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(delivery_status);

-- Q4 y Q9: unir entregas con viajes
CREATE INDEX IF NOT EXISTS idx_deliveries_trip ON deliveries(trip_id);

-- Actualizar estadísticas para que PostgreSQL use los índices
ANALYZE;

-- Para medir una query antes y después:  EXPLAIN ANALYZE <query>;
