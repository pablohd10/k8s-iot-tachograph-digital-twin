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
    try:
        tachograph_id = data["Tachograph_id"]
        latitude = data["Position"]["latitude"]
        longitude = data["Position"]["longitude"]
        warning = data["Warning"]
        timestamp_str = data["Timestamp"]

        # Parsear string a datetime con microsegundos si es necesario
        dt_obj = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f" if '.' in timestamp_str else "%Y-%m-%d %H:%M:%S")

        print(f"[INFO] Registrando evento para {tachograph_id} en fecha: {dt_obj}")

        conn = connect_database()
        if conn is None:
            return "Database connection failed"
        
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO events (tachograph_id, latitude, longitude, warning, time_stamp)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (tachograph_id, latitude, longitude, warning, dt_obj)
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
    connection = None
    cursor = None
    try:
        # Parsear fechas a objetos datetime
        init_dt = datetime.strptime(init_interval, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_interval, "%Y-%m-%d %H:%M:%S")

        print(f"[INFO] Consultando eventos para el tacógrafo {tachograph_id}")
        print(f"[INFO] Rango de fechas: {init_dt} → {end_dt}")

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
            time_stamp
        FROM events
        WHERE tachograph_id = %s
          AND time_stamp BETWEEN %s AND %s
        ORDER BY time_stamp ASC
        """
        cursor.execute(query, (tachograph_id, init_dt, end_dt))
        results = cursor.fetchall()
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