from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.operators.python import PythonOperator
import pandas as pd
import io
import json

import clickhouse_connect

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def extract_from_postgres(source_conn_id: str, query: str, output_key: str, **context):
    hook = PostgresHook(postgres_conn_id=source_conn_id)
    df = hook.get_pandas_df(query)
    s3_hook = S3Hook(aws_conn_id='minio_s3')
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, compression='snappy')
    buffer.seek(0)
    execution_date = context['ds_nodash']
    s3_key = f"landing/{output_key}/{execution_date}/{context['task_instance'].try_number}.parquet"
    s3_hook.load_file_obj(
        file_obj=buffer,
        key=s3_key,
        bucket_name='landing-zone',
        replace=True
    )
    context['ti'].xcom_push(key='s3_path', value=s3_key)
    context['ti'].xcom_push(key='row_count', value=len(df))

    return f"Извлечено {len(df)} строк в {s3_key}"

def transform_and_load_telemetry(**context):
    s3_hook = S3Hook(aws_conn_id='minio_s3')
    s3_key = context['ti'].xcom_pull(task_ids='extract_telemetry', key='s3_path')
    obj = s3_hook.get_key(s3_key, bucket_name='landing-zone')
    buffer = io.BytesIO(obj.get()['Body'].read())
    df = pd.read_parquet(buffer)
    df['recorded_at'] = pd.to_datetime(df['recorded_at'], utc=True)
    client = clickhouse_connect.get_client(
        host='clickhouse',
        port=8123,
        username='clickhouse_user',
        password='clickhouse_secure_789',
        database='prosthetics_analytics'
    )
    columns = [
        'serial_number', 'recorded_at', 'emg_value', 'emg_muscle_group',
        'esp32_temperature', 'esp32_uptime_seconds', 'esp32_signal_strength',
        'battery_level', 'battery_voltage', 'battery_current',
        'step_count', 'gait_phase', 'firmware_version'
    ]

    data = df[columns].values.tolist()
    client.insert(
        table='fact_telemetry',
        data=data,
        column_names=columns
    )
    client.close()
    return f"Загружено {len(df)} записей телеметрии в ClickHouse"

def transform_and_load_users_orders(**context):
    s3_hook = S3Hook(aws_conn_id='minio_s3')
    s3_key = context['ti'].xcom_pull(task_ids='extract_users_orders', key='s3_path')
    obj = s3_hook.get_key(s3_key, bucket_name='landing-zone')
    buffer = io.BytesIO(obj.get()['Body'].read())
    df = pd.read_parquet(buffer)
    df['order_date'] = pd.to_datetime(df['order_date'])
    df['birth_date'] = pd.to_datetime(df['birth_date'])
    df['age_at_order'] = (df['order_date'].dt.year - df['birth_date'].dt.year)
    df = df.replace({pd.NaT: None})

    client = clickhouse_connect.get_client(
        host='clickhouse',
        port=8123,
        username='clickhouse_user',
        password='clickhouse_secure_789',
        database='prosthetics_analytics'
    )
    columns = [
        'user_id', 'full_name', 'birth_date', 'city',
        'prosthesis_serial', 'model_name', 'model_price',
        'order_date', 'status', 'delivered_at'
    ]
    data = df[columns].values.tolist()
    client.insert(
        table='dim_users_orders',
        data=data,
        column_names=columns
    )
    client.close()
    return f"Загружено {len(df)} записей пользователей в витрину"

with DAG(
        'prosthetics_etl',
        default_args=default_args,
        description='ETL пайплайн для системы протезов',
        schedule_interval='@hourly',
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=['prosthetics', 'telemetry', 'etl'],
) as dag:

    extract_users_orders = PythonOperator(
        task_id='extract_users_orders',
        python_callable=extract_from_postgres,
        op_kwargs={
            'source_conn_id': 'crm_db',
            'query': """
                SELECT 
                    u.id AS user_id,
                    u.full_name,
                    u.birth_date,
                    u.city,
                    up.serial_number AS prosthesis_serial,
                    pm.model_name,
                    pm.price AS model_price,
                    up.order_date,
                    up.status::text AS status,
                    up.delivered_at
                FROM users u
                JOIN user_prostheses up ON u.id = up.user_id
                JOIN prosthesis_models pm ON up.prosthesis_model_id = pm.id
                WHERE up.order_date >= CURRENT_DATE - INTERVAL '30 days'
            """,
            'output_key': 'users_orders'
        },
    )

    extract_telemetry = PythonOperator(
        task_id='extract_telemetry',
        python_callable=extract_from_postgres,
        op_kwargs={
            'source_conn_id': 'telemetrics_db',
            'query': """
                SELECT 
                    serial_number,
                    recorded_at,
                    emg_value,
                    emg_muscle_group,
                    esp32_temperature,
                    esp32_uptime_seconds,
                    esp32_signal_strength,
                    battery_level,
                    battery_voltage,
                    battery_current,
                    step_count,
                    gait_phase,
                    firmware_version
                FROM prosthesis_telemetry
                WHERE recorded_at >= NOW() - INTERVAL '60 days'
            """,
            'output_key': 'telemetry'
        },
    )

    load_telemetry = PythonOperator(
        task_id='load_telemetry_to_clickhouse',
        python_callable=transform_and_load_telemetry,
    )

    load_users_orders = PythonOperator(
        task_id='load_users_orders_to_clickhouse',
        python_callable=transform_and_load_users_orders,
    )

    [extract_users_orders, extract_telemetry] >> load_users_orders
    extract_telemetry >> load_telemetry