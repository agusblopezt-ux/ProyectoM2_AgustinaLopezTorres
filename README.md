# FleetLogix · Proyecto Integrador M2

**Agustina López Torres · Soy Henry Data Science**

## 1. De qué se trata

FleetLogix es una empresa de transporte y logística que opera **200 vehículos** entre 5 ciudades de Argentina (Buenos Aires, Córdoba, Rosario, Mendoza y San Miguel de Tucumán). El proyecto arma, de punta a punta, la infraestructura de datos de la empresa:

1. **Avance 1:** se generan datos sintéticos coherentes y se cargan en una base PostgreSQL de 6 tablas.
2. **Avance 2:** se responden 12 preguntas de negocio con SQL y se optimizan con índices.
3. **Avance 3:** se construye un Data Warehouse en Snowflake (modelo estrella) con un pipeline ETL en Python.
4. **Avance 4:** se diseña la arquitectura en AWS para recibir los datos de los camiones en tiempo real.

![Arquitectura AWS (Avance 4)](2.%20Scripts/aws_architecture_diagram.png)

## 2. Flujo de los datos

| Paso | Herramienta | Resultado |
|---|---|---|
| Generar datos | Python (Faker, pandas, numpy) | 6 archivos CSV, 506.111 registros |
| Base transaccional | PostgreSQL `fleet_logix_bd` | 6 tablas con claves primarias y foráneas |
| Análisis | SQL + `EXPLAIN ANALYZE` | 12 queries documentadas y 5 índices |
| Data Warehouse | Snowflake `FLEET_DW.ANALYTICAL_CORE` | 1 tabla de hechos, 6 dimensiones y 2 vistas seguras |
| Nube | AWS (API Gateway, Lambda, S3, DynamoDB, RDS, SNS) | Arquitectura y 3 funciones Lambda |

## 3. Estructura de la entrega

**1. Notebooks**

- `Avance_1_DataGeneration.ipynb`: generación de datos y control de calidad.
- `Avance_2_SQLAnalysis.ipynb`: 12 queries, planes de ejecución, índices y comparación de tiempos.
- `Avance_3_DataWarehouse.ipynb`: pipeline ETL de PostgreSQL a Snowflake.
- `Avance_4_CloudArchitecture.ipynb`: arquitectura AWS, pruebas de las Lambdas y análisis del ETA.

**2. Scripts**

| Archivo | Avance | Qué hace |
|---|---|---|
| `01_data_generation.py` | Avance 1 | genera los 6 CSV (versión script del notebook) |
| `02_queries_analysis.sql` | Avance 2 | las 12 queries |
| `03_optimization_indexes.sql` | Avance 2 | los 5 índices |
| `04_dimensional_model.sql` | Avance 3 | tablas y vistas del Data Warehouse en Snowflake |
| `05_etl_pipeline.py` | Avance 3 | pipeline ETL (versión script del notebook) |
| `aws_architecture_diagram.png` | Avance 4 | diagrama de la arquitectura AWS |
| `lambda_functions/` | Avance 4 | las 3 funciones Lambda |

**3. Documentación**

- `README.pdf` (este documento en PDF), `Manual_Consultas_SQL.pdf`, `Arquitectura_Tecnica.pdf`, `Capturas_Snowflake.pdf`, `data_dictionary.xlsx` y `torre_de_control.html`.

## 4. Resultados por avance

### Avance 1: generación de datos

| Tabla | Registros | Detalle |
|---|---|---|
| vehicles | 200 | 4 tipos, con capacidad y combustible coherentes con el tipo |
| drivers | 400 | 351 activos, con fecha de contratación y licencia vigente |
| routes | 50 | entre las 5 ciudades, con distancia, duración y peaje |
| trips | 100.000 | 2 años de operación (oct-2024 a sep-2026), con picos de salida a la mañana y después del mediodía |
| deliveries | 400.461 | entre 2 y 6 entregas por viaje, 4 lo más común |
| maintenance | 5.000 | 6 tipos de mantenimiento, posteriores al viaje |

El notebook corre **15 controles de calidad** antes de cargar, y pasan todos. Entre ellos están la integridad referencial completa, que la llegada sea posterior a la salida, que ningún conductor maneje antes de ser contratado, que nadie haga dos viajes a la vez (con 8 horas de descanso del conductor) y que no haya claves repetidas. Todo queda registrado en `carga_datos.log`.

### Avance 2: análisis SQL y optimización

Se corrieron 12 queries (3 básicas, 5 intermedias y 4 complejas), cada una con el problema de negocio que resuelve. Algunos resultados:

- El **92%** de las entregas se completa, el 5% falla y el 3% queda pendiente.
- Las 50 rutas tienen un uso parejo, de entre 1.921 y 2.059 viajes cada una.
- El porcentaje de éxito de los conductores va del 88,6% al 95,6%.

Con **5 índices**, el tiempo total de las 12 queries bajó de **472,7 ms a 356,0 ms**. Las queries que buscan pocas filas mejoraron más del 90% (la 6 bajó de 57,2 ms a 0,4 ms). Las que resumen tablas enteras casi no cambian, porque tienen que leer todas las filas de todos modos. El detalle está en el `Manual_Consultas_SQL.pdf`.

### Avance 3: Data Warehouse en Snowflake

Modelo estrella con `FACT_DELIVERIES` (una fila por entrega) y 6 dimensiones:

| Tabla | Filas | Clave |
|---|---|---|
| FACT_DELIVERIES | 400.461 | DELIVERY_ID |
| DIM_DATE | 731 | DATE_KEY (AAAAMMDD) |
| DIM_TIME | 24 | TIME_KEY (hora 0 a 23) |
| DIM_VEHICLE | 200 | VEHICLE_ID |
| DIM_DRIVER | 400 | DRIVER_ID |
| DIM_ROUTE | 50 | ROUTE_ID |
| DIM_CUSTOMER | 399.214 | CUSTOMER_KEY |

Métricas de la tabla de hechos: peso del paquete, demora en minutos, entrega a tiempo y firma del cliente. Hay dos **vistas seguras**: `VW_SECURE_OPERATIONS` para operaciones (conductores, vehículos, rutas) y `VW_SECURE_CUSTOMERS` para el área comercial (clientes). El **control histórico** se hace con *Time Travel* de Snowflake. El pipeline controla que todas las claves existan antes de cargar, porque Snowflake no valida las claves foráneas.

### Avance 4: arquitectura en AWS

La app de los conductores manda los datos a **API Gateway**, que ejecuta 3 funciones **Lambda**:

| Ruta | Lambda | Qué hace |
|---|---|---|
| POST /deliveries/complete | verify_delivery | registra que una entrega se completó |
| GET /trips/eta | calculate_eta | calcula la hora estimada de llegada |
| POST /telemetry/location | route_deviation_alert | avisa por SNS si el camión se desvía más de 50 km |

Los eventos crudos se guardan en **S3** por fecha, el estado actual en **DynamoDB** y la base relacional migra a **RDS PostgreSQL**. **EventBridge** corre el ETL del Avance 3 todas las noches.

**Diferencial: torre de control.** Es una página que simula la flota sobre las rutas y viajes reales de la base, con ETA calibrado y alertas de desvío: [abrir la torre de control](https://claude.ai/artifact/XR7Xm2THf1NywneS81YZYZ) (también está en `3. Documentación/torre_de_control.html`). Analizando los viajes se vio que la duración real es, en promedio, 1,1 veces la estimada de la ruta. Con ese ajuste, el error del ETA bajó de 66 a 53 minutos.

## 5. Cómo reproducirlo

1. Instalar Python 3.12, PostgreSQL y las librerías: `pip install faker pandas numpy matplotlib sqlalchemy psycopg2-binary snowflake-connector-python`.
2. Correr `Avance_1_DataGeneration.ipynb` (o `01_data_generation.py`): genera los 6 CSV.
3. Crear la base `fleet_logix_bd` con sus 6 tablas y cargar los CSV en el orden vehicles, drivers, routes, trips, deliveries, maintenance.
4. Correr `Avance_2_SQLAnalysis.ipynb`: ejecuta las queries, crea los índices y compara tiempos.
5. Correr `Avance_3_DataWarehouse.ipynb` (o `05_etl_pipeline.py`) desde su carpeta, así encuentra `04_dimensional_model.sql` en `2. Scripts`: crea el modelo en Snowflake y lo carga.
6. Abrir `Avance_4_CloudArchitecture.ipynb` para ver la arquitectura y probar las Lambdas.

Las contraseñas de PostgreSQL y Snowflake se piden al correr (con `getpass`), y no quedan escritas en el código.

## 6. Tecnologías

Python 3.12 (pandas, numpy, Faker, SQLAlchemy, matplotlib) · PostgreSQL 18 · Snowflake · AWS (API Gateway, Lambda, S3, DynamoDB, RDS, SNS, EventBridge, CloudWatch, Secrets Manager) · Git y GitHub · VS Code con Jupyter.
