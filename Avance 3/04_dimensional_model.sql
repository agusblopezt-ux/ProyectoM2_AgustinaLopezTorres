-- =============================================================================
-- FleetLogix - Avance 3: Data Warehouse en Snowflake (modelo estrella)
-- Base FLEET_DW, esquema ANALYTICAL_CORE
--
-- Tabla de hechos: FACT_DELIVERIES (una fila por entrega)
-- Dimensiones:     DIM_DATE, DIM_TIME, DIM_VEHICLE, DIM_DRIVER, DIM_ROUTE, DIM_CUSTOMER
--
-- Cada fila de hechos tiene una clave por dimensión, así se puede responder
-- "cuántas entregas hizo tal conductor, con tal vehículo, en tal ruta, tal mes".
-- Las tablas las llena el notebook Avance_3_DataWarehouse.ipynb (pipeline ETL).
-- =============================================================================

USE DATABASE FLEET_DW;
USE SCHEMA ANALYTICAL_CORE;

-- Primero se borra la tabla de hechos, porque apunta a las dimensiones que se van a recrear
DROP TABLE IF EXISTS FACT_DELIVERIES;

-- -----------------------------------------------------------------------------
-- DIMENSIONES
-- -----------------------------------------------------------------------------

-- Fecha: una fila por día. DATE_KEY tiene formato AAAAMMDD (ej. 20261027)
CREATE OR REPLACE TABLE DIM_DATE (
    DATE_KEY      NUMBER(8,0)  NOT NULL PRIMARY KEY,
    FULL_DATE     DATE,
    DAY_OF_WEEK   NUMBER(1,0),     -- 1 = lunes ... 7 = domingo
    DAY_NAME      VARCHAR(20),
    IS_WEEKEND    BOOLEAN,
    WEEK_OF_YEAR  NUMBER(2,0),
    MONTH         NUMBER(2,0),
    MONTH_NAME    VARCHAR(20),
    QUARTER       NUMBER(1,0),
    YEAR          NUMBER(4,0)
);

-- Horario: una fila por hora del día (0 a 23)
CREATE OR REPLACE TABLE DIM_TIME (
    TIME_KEY      NUMBER(2,0)  NOT NULL PRIMARY KEY,   -- la hora: 0 a 23
    HOUR_LABEL    VARCHAR(5),                          -- ej. '08:00'
    TIME_OF_DAY   VARCHAR(20)                          -- Madrugada / Mañana / Tarde / Noche
);

CREATE OR REPLACE TABLE DIM_VEHICLE (
    VEHICLE_ID        NUMBER(38,0) NOT NULL PRIMARY KEY,
    LICENSE_PLATE     VARCHAR(20),
    VEHICLE_TYPE      VARCHAR(50),
    CAPACITY_KG       FLOAT,
    FUEL_TYPE         VARCHAR(20),
    ACQUISITION_DATE  DATE,
    STATUS            VARCHAR(20)
);

CREATE OR REPLACE TABLE DIM_DRIVER (
    DRIVER_ID       NUMBER(38,0) NOT NULL PRIMARY KEY,
    EMPLOYEE_CODE   VARCHAR(20),
    FULL_NAME       VARCHAR(200),
    LICENSE_NUMBER  VARCHAR(30),
    LICENSE_EXPIRY  DATE,
    HIRE_DATE       DATE,
    STATUS          VARCHAR(20)
);

CREATE OR REPLACE TABLE DIM_ROUTE (
    ROUTE_ID                  NUMBER(38,0) NOT NULL PRIMARY KEY,
    ROUTE_CODE                VARCHAR(20),
    ORIGIN_CITY               VARCHAR(100),
    DESTINATION_CITY          VARCHAR(100),
    DISTANCE_KM               FLOAT,
    ESTIMATED_DURATION_HOURS  FLOAT,
    TOLL_COST                 FLOAT
);

-- Cliente: una fila por cliente. La ciudad es la de destino de la ruta donde se le entregó
CREATE OR REPLACE TABLE DIM_CUSTOMER (
    CUSTOMER_KEY   NUMBER(38,0) NOT NULL PRIMARY KEY,
    CUSTOMER_NAME  VARCHAR(150),
    CITY           VARCHAR(100)
);

-- -----------------------------------------------------------------------------
-- TABLA DE HECHOS
-- -----------------------------------------------------------------------------

CREATE OR REPLACE TABLE FACT_DELIVERIES (
    DELIVERY_ID          NUMBER(38,0) NOT NULL PRIMARY KEY,
    -- Claves hacia las dimensiones
    DATE_KEY             NUMBER(8,0)  REFERENCES DIM_DATE(DATE_KEY),
    TIME_KEY             NUMBER(2,0)  REFERENCES DIM_TIME(TIME_KEY),
    VEHICLE_ID           NUMBER(38,0) REFERENCES DIM_VEHICLE(VEHICLE_ID),
    DRIVER_ID            NUMBER(38,0) REFERENCES DIM_DRIVER(DRIVER_ID),
    ROUTE_ID             NUMBER(38,0) REFERENCES DIM_ROUTE(ROUTE_ID),
    CUSTOMER_KEY         NUMBER(38,0) REFERENCES DIM_CUSTOMER(CUSTOMER_KEY),
    -- Datos de la entrega
    TRIP_ID              NUMBER(38,0),
    TRACKING_NUMBER      VARCHAR(30),
    DELIVERY_STATUS      VARCHAR(20),
    SCHEDULED_DATETIME   TIMESTAMP_NTZ,
    DELIVERED_DATETIME   TIMESTAMP_NTZ,
    -- Métricas
    PACKAGE_WEIGHT_KG    FLOAT,
    DELAY_MINUTES        NUMBER(10,0),  -- entregada - programada (negativo = antes de hora)
    IS_ON_TIME           BOOLEAN,       -- entregada con 30 minutos de tolerancia
    IS_SIGNED            BOOLEAN        -- el destinatario firmó
);
-- Nota: en Snowflake las PRIMARY KEY y REFERENCES documentan el modelo pero no se validan.
-- La integridad la garantiza el pipeline ETL (lo controla antes de cargar).

-- -----------------------------------------------------------------------------
-- CONTROL HISTÓRICO: Time Travel
-- Snowflake guarda las versiones anteriores de la tabla de hechos durante 1 día
-- (máximo en la edición estándar). Ejemplo para ver cómo estaba hace 1 hora:
--   SELECT COUNT(*) FROM FACT_DELIVERIES AT (OFFSET => -3600)
-- -----------------------------------------------------------------------------
ALTER TABLE FACT_DELIVERIES SET DATA_RETENTION_TIME_IN_DAYS = 1;

-- -----------------------------------------------------------------------------
-- VISTAS SEGURAS
-- Una vista segura (SECURE VIEW) no deja ver su código SQL a quien la consulta,
-- y se usa para mostrar solo las columnas que cada área necesita.
-- -----------------------------------------------------------------------------

-- Para el área de operaciones: entregas con conductor, vehículo y ruta (sin datos de clientes)
CREATE OR REPLACE SECURE VIEW VW_SECURE_OPERATIONS AS
SELECT
    f.DELIVERY_ID,
    d.FULL_DATE,
    t.TIME_OF_DAY,
    dr.FULL_NAME      AS DRIVER_NAME,
    v.LICENSE_PLATE,
    v.VEHICLE_TYPE,
    r.ROUTE_CODE,
    r.ORIGIN_CITY,
    r.DESTINATION_CITY,
    r.DISTANCE_KM,
    f.DELIVERY_STATUS,
    f.DELAY_MINUTES,
    f.IS_ON_TIME
FROM FACT_DELIVERIES f
JOIN DIM_DATE d     ON f.DATE_KEY = d.DATE_KEY
JOIN DIM_TIME t     ON f.TIME_KEY = t.TIME_KEY
JOIN DIM_DRIVER dr  ON f.DRIVER_ID = dr.DRIVER_ID
JOIN DIM_VEHICLE v  ON f.VEHICLE_ID = v.VEHICLE_ID
JOIN DIM_ROUTE r    ON f.ROUTE_ID = r.ROUTE_ID;

-- Para el área comercial: entregas por cliente (sin datos de conductores)
CREATE OR REPLACE SECURE VIEW VW_SECURE_CUSTOMERS AS
SELECT
    f.DELIVERY_ID,
    d.FULL_DATE,
    c.CUSTOMER_NAME,
    c.CITY,
    f.PACKAGE_WEIGHT_KG,
    f.DELIVERY_STATUS,
    f.IS_ON_TIME,
    f.IS_SIGNED
FROM FACT_DELIVERIES f
JOIN DIM_DATE d     ON f.DATE_KEY = d.DATE_KEY
JOIN DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY;

-- La vista vieja de ventas se borra: usaba montos (revenue) que FleetLogix no registra
DROP VIEW IF EXISTS VW_SECURE_SALES;
