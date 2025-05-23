import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime


def connect_database():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DBHOST"),
            user=os.getenv("DBUSER"),
            password=os.getenv("DBPASSWORD"),
            database=os.getenv("DBDATABASE")
        )
        return connection
    except Exception as e:
        print("Error de conexión a la base de datos: ", e)
        return None
    

def register_telemetry_db(params):
    connection = None
    cursor = None

    try:
        # Extraer campos
        tachograph_id = params["Tachograph_id"]
        latitude = params["Position"]["latitude"]
        longitude = params["Position"]["longitude"]
        gps_speed = params["GPSSpeed"]
        speed = params["Speed"]
        driver = params["Driver"]
        timestamp_str = params["Timestamp"]

        # Convertir string a datetime (con o sin microsegundos)
        dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f" if '.' in timestamp_str else "%Y-%m-%d %H:%M:%S")

        print(f"[INFO] Registrando telemetría para {tachograph_id} en fecha: {dt_obj}")

        # Conexión a la base de datos
        connection = connect_database()
        if connection is None:
            return False
        cursor = connection.cursor()

        # Sentencia de inserción
        insert_query = """
            INSERT INTO telemetry (
                tachograph_id, latitude, longitude,
                gps_speed, current_speed,
                current_driver_id, time_stamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        values = (
            tachograph_id,
            latitude,
            longitude,
            gps_speed,
            speed,
            driver,
            dt_obj  # ya es objeto datetime, no timestamp float
        )

        cursor.execute(insert_query, values)
        connection.commit()
        return True

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        if connection and connection.is_connected():
            connection.rollback()
        return False

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        if connection and connection.is_connected():
            connection.rollback()
        return False

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
        
def get_telemetry_db(tachograph_id, init_interval, end_interval):
    connection = None
    cursor = None
    try:
        # Parsear strings a datetime
        init_dt = datetime.strptime(init_interval, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_interval, "%Y-%m-%d %H:%M:%S")

        # Conexión a la base de datos
        connection = connect_database()
        if connection is None:
            return False
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT
            tachograph_id,
            latitude,
            longitude,
            gps_speed,
            current_speed,
            current_driver_id,
            time_stamp
        FROM telemetry
        WHERE tachograph_id = %s
          AND time_stamp BETWEEN %s AND %s
        ORDER BY time_stamp ASC
        """

        print(f"Ejecutando consulta SQL para {tachograph_id} entre {init_dt} y {end_dt}")
        cursor.execute(query, (tachograph_id, init_dt, end_dt))
        results = cursor.fetchall()
        print("Resultado de la consulta:", results)

        return results

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        return []

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return []

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def get_vehicles_last_position():
    """
    Obtiene la última posición conocida (latitud y longitud) de cada vehículo activo.

    Entrada:
        - No recibe parámetros.

    Proceso:
        - Realiza una consulta SQL para obtener, por cada tacógrafo, el registro
          con la marca de tiempo más reciente, asegurando una única fila por vehículo.

    Salida:
        - Si tiene éxito: tupla ("", resultados) donde resultados es una lista de diccionarios con:
            {
                "tachograph_id": str,
                "latitude": float,
                "longitude": float
            }
        - Si hay error: tupla ("<mensaje de error>", [])

    Nota:
        Utiliza connect_database() y retorna errores específicos de MySQL si ocurren.
        Requiere que la tabla `telemetry` tenga una columna `id` autoincremental única.
    """
    try:
        # Conexión a la base de datos
        connection = connect_database()
        if connection is None:
            return "Error: No se pudo conectar a la base de datos", []
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT t1.tachograph_id, t1.latitude, t1.longitude
        FROM telemetry t1
        JOIN (
            SELECT MAX(id) AS max_id
            FROM telemetry
            GROUP BY tachograph_id
        ) t2 ON t1.id = t2.max_id;
        """

        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        connection.close()

        return "", results

    except mysql.connector.Error as err:
        return f"MySQL Error: {str(err)}", []
    except Exception as e:
        return f"General Error: {str(e)}", []