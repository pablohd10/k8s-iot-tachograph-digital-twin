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
    """
    Inserta una nueva entrada de telemetría en la base de datos.

    Entrada:
        - params: Diccionario con la información de telemetría. Debe incluir:
            {
                "Tachograph_id": str,
                "Position": {
                    "latitude": float,
                    "longitude": float
                },
                "GPSSpeed": float,
                "Speed": float,
                "Driver": str,
                "Timestamp": "YYYY-MM-DD HH:MM:SS"
            }

    Proceso:
        - Convierte la fecha a timestamp UNIX.
        - Inserta los datos en la tabla `telemetry`.
        - Realiza rollback si hay errores durante la inserción.

    Salida:
        - True si la inserción fue exitosa.
        - False si ocurrió un error.

    Nota:
        Utiliza la función connect_database() para acceder a la base de datos.
    """
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

        # Convertir fecha a timestamp UNIX (float)
        dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        timestamp = dt_obj.timestamp()

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
            timestamp
        )

        cursor.execute(insert_query, values)
        connection.commit()  # Confirmar la transacción

        return True

    except Error as e:
        print(f"[ERROR] Database error: {e}")
        if connection and connection.is_connected():
            connection.rollback()  # Revertir si hubo cambios
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
    """
    Recupera registros de telemetría de un tacógrafo en un intervalo de tiempo determinado.

    Entrada:
        - tachograph_id: Identificador del tacógrafo.
        - init_interval: Fecha de inicio (str) con formato "YYYY-MM-DD HH:MM:SS".
        - end_interval: Fecha de fin (str) con formato "YYYY-MM-DD HH:MM:SS".

    Proceso:
        - Convierte las fechas a timestamps UNIX.
        - Consulta la tabla `telemetry` por registros que coincidan con el tacógrafo
          y estén dentro del rango de tiempo.

    Salida:
        - Lista de diccionarios con los datos de telemetría ordenados por fecha.
        - Lista vacía si no hay resultados o ocurre un error.

    Nota:
        Usa conexión a la base de datos a través de connect_database().
    """
    connection = None
    cursor = None
    try:
        # Convertir fechas a timestamp float
        init_ts = datetime.strptime(init_interval, "%Y-%m-%d %H:%M:%S").timestamp()
        end_ts = datetime.strptime(end_interval, "%Y-%m-%d %H:%M:%S").timestamp()

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
            FROM_UNIXTIME(time_stamp) AS time_stamp
        FROM telemetry
        WHERE tachograph_id = %s
          AND time_stamp BETWEEN %s AND %s
        ORDER BY time_stamp ASC
        """

        cursor.execute(query, (tachograph_id, init_ts, end_ts))
        results = cursor.fetchall()

        return results  # lista de diccionarios

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