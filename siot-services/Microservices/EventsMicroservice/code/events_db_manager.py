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

def register_event_db(data):
    """
    Inserta un nuevo evento en la base de datos.

    Parámetros:
        data (dict): Diccionario con la información del evento.

    Devuelve:
        str: Cadena vacía si tuvo éxito, o mensaje de error si falló.
    """
    try:
        tachograph_id = data["Tachograph_id"]
        latitude = data["Position"]["latitude"]
        longitude = data["Position"]["longitude"]
        warning = data["Warning"]
        timestamp_str = data["Timestamp"]

        # Convertir fecha a timestamp UNIX (float)
        dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        timestamp = dt_obj.timestamp()

        conn = connect_database()
        if conn is None:
            return "Database connection failed"
        
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO events (tachograph_id, latitude, longitude, warning, time_stamp)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (tachograph_id, latitude, longitude, warning, timestamp)
        cursor.execute(insert_query, values)
        conn.commit()

        cursor.close()
        conn.close()
        return ""

    except mysql.connector.Error as err:
        return f"MySQL Error: {str(err)}"
    except Exception as e:
        return f"General Error: {str(e)}"

def get_events_db(tachograph_id, init_interval, end_interval):
    """
    Recupera registros de eventos de un tacógrafo en un intervalo de tiempo determinado.

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
            warning,
            FROM_UNIXTIME(time_stamp) AS time_stamp
        FROM events
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