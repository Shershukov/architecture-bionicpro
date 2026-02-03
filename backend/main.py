from fastapi import FastAPI, HTTPException, Query, Depends, Request
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import clickhouse_connect
import psycopg2
from security import auth_dependency

app = FastAPI(title="Prosthetics Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CRM_DB_CONFIG = {
    'host': 'crm_db',
    'port': 5432,
    'database': 'crm_db',
    'user': 'crm_user',
    'password': 'crm_password'
}

def get_user_id_by_email(email: str) -> int:
    """Получает user_id из CRM по keycloak_sub"""
    try:
        conn = psycopg2.connect(**CRM_DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if not result:
            raise HTTPException(status_code=404, detail="User not found in CRM")
        return result[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CRM DB error: {str(e)}")

client = clickhouse_connect.get_client(
    host='clickhouse',
    port=8123,
    username='clickhouse_user',
    password='clickhouse_secure_789',
    database='prosthetics_analytics'
)

class UserReport(BaseModel):
    user_id: int
    full_name: str
    city: str
    total_steps: int
    avg_battery_level: float
    min_battery_level: int
    latest_firmware: str
    model_name: str
    status: str
    last_recorded_at: str

@app.get("/reports", response_model=List[UserReport])
async def get_user_report(
        user_id: Optional[int] = Query(None, description="ID пользователя"),
        token_payload: dict = auth_dependency
):
    try:
        user_email = token_payload.get("email")
        print(f"{user_email}")
        target_user_id = get_user_id_by_email(user_email)
        print(f"{target_user_id}")

        # 🔒 Проверка безопасности: пользователь может запрашивать ТОЛЬКО свой отчёт
        if user_id is not None and user_id != target_user_id:
            raise HTTPException(
                status_code=403,
                detail="Доступ запрещен"
            )

        query = f"""
        SELECT 
            user_id,
            any(full_name) AS full_name,
            any(city) AS city,
            sum(total_steps) AS total_steps,
            avg(avg_battery_level) AS avg_battery_level,
            min(min_battery_level) AS min_battery_level,
            any(latest_firmware) AS latest_firmware,
            any(model_name) AS model_name,
            any(status) AS status,
            max(last_recorded_at) AS last_recorded_at
        FROM prosthetics_analytics.mv_user_daily_stats
        WHERE user_id = {target_user_id}
        GROUP BY user_id
        """

        result = client.query(query)

        if not result.result_rows:
            raise HTTPException(
                status_code=404,
                detail=f"Report for user {target_user_id} not found"
            )

        reports = []
        for row in result.result_rows:
            reports.append({
                "user_id": row[0],
                "full_name": row[1],
                "city": row[2],
                "total_steps": row[3],
                "avg_battery_level": float(row[4]),
                "min_battery_level": int(row[5]),
                "latest_firmware": row[6],
                "model_name": row[7],
                "status": row[8],
                "last_recorded_at": row[9].isoformat() if row[9] else None
            })

        return reports

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")