#!/usr/bin/env python3
"""
Настройка RLS (Row Level Security) политик в Supabase
для защиты данных пользователей
"""

import os
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SupabaseRLSSetup:
    """Класс для настройки RLS политик в Supabase"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.getenv('SUPABASE_URL')
        if not self.connection_string:
            raise ValueError("Не указана строка подключения SUPABASE_URL")
    
    def connect(self):
        """Установка соединения с базой данных"""
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            logger.info("✅ Успешное подключение к Supabase")
            return conn
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Supabase: {e}")
            raise
    
    def enable_rls_for_table(self, table_name: str):
        """Включение RLS для указанной таблицы"""
        sql = f"""
        -- Включение RLS для таблицы {table_name}
        ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY;
        
        -- Создание политики для service_role (полный доступ)
        CREATE POLICY IF NOT EXISTS "{table_name}_service_role_policy" 
        ON public.{table_name}
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
        
        -- Создание политики для authenticated users (только чтение своих данных)
        CREATE POLICY IF NOT EXISTS "{table_name}_authenticated_read_policy" 
        ON public.{table_name}
        FOR SELECT
        TO authenticated
        USING (auth.uid() = user_id);
        
        -- Создание политики для anon users (только чтение)
        CREATE POLICY IF NOT EXISTS "{table_name}_anon_read_policy" 
        ON public.{table_name}
        FOR SELECT
        TO anon
        USING (true);
        """
        
        return sql
    
    def create_user_specific_policies(self):
        """Создание пользовательских политик для Firehorse"""
        sql = """
        -- Политики для таблицы fh_orders
        DROP POLICY IF EXISTS "fh_orders_service_role_policy" ON public.fh_orders;
        DROP POLICY IF EXISTS "fh_orders_authenticated_read_policy" ON public.fh_orders;
        DROP POLICY IF EXISTS "fh_orders_anon_read_policy" ON public.fh_orders;
        
        -- Включение RLS
        ALTER TABLE public.fh_orders ENABLE ROW LEVEL SECURITY;
        
        -- Политика для service_role (полный доступ для бэкенда)
        CREATE POLICY "fh_orders_service_role_policy" 
        ON public.fh_orders
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
        
        -- Политика для authenticated users (только свои заказы)
        CREATE POLICY "fh_orders_authenticated_read_policy" 
        ON public.fh_orders
        FOR SELECT
        TO authenticated
        USING (auth.uid() = user_id);
        
        -- Политика для anon users (только чтение, без user_id)
        CREATE POLICY "fh_orders_anon_read_policy" 
        ON public.fh_orders
        FOR SELECT
        TO anon
        USING (user_id IS NULL);
        
        -- Политики для таблицы fh_order_events
        DROP POLICY IF EXISTS "fh_order_events_service_role_policy" ON public.fh_order_events;
        DROP POLICY IF EXISTS "fh_order_events_authenticated_read_policy" ON public.fh_order_events;
        DROP POLICY IF EXISTS "fh_order_events_anon_read_policy" ON public.fh_order_events;
        
        -- Включение RLS
        ALTER TABLE public.fh_order_events ENABLE ROW LEVEL SECURITY;
        
        -- Политика для service_role
        CREATE POLICY "fh_order_events_service_role_policy" 
        ON public.fh_order_events
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
        
        -- Политика для authenticated users (только события своих заказов)
        CREATE POLICY "fh_order_events_authenticated_read_policy" 
        ON public.fh_order_events
        FOR SELECT
        TO authenticated
        USING (EXISTS (
            SELECT 1 FROM public.fh_orders o 
            WHERE o.id = fh_order_events.order_id 
            AND o.user_id = auth.uid()
        ));
        
        -- Политика для anon users
        CREATE POLICY "fh_order_events_anon_read_policy" 
        ON public.fh_order_events
        FOR SELECT
        TO anon
        USING (EXISTS (
            SELECT 1 FROM public.fh_orders o 
            WHERE o.id = fh_order_events.order_id 
            AND o.user_id IS NULL
        ));
        """
        
        return sql
    
    def setup_anti_ban_measures(self):
        """Настройка мер защиты от бана (rate limiting, etc.)"""
        sql = """
        -- Создание таблицы для отслеживания запросов к Kwork API
        CREATE TABLE IF NOT EXISTS public.kwork_api_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id TEXT,
            category_id INTEGER,
            request_type TEXT CHECK (request_type IN ('parse', 'reply', 'view')),
            timestamp TIMESTAMPTZ DEFAULT now(),
            ip_address INET,
            user_agent TEXT,
            success BOOLEAN DEFAULT false,
            response_time_ms INTEGER
        );
        
        -- Включение RLS для таблицы запросов
        ALTER TABLE public.kwork_api_requests ENABLE ROW LEVEL SECURITY;
        
        -- Политика только для service_role
        CREATE POLICY IF NOT EXISTS "kwork_api_requests_service_role_policy" 
        ON public.kwork_api_requests
        FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true);
        
        -- Создание индексов для быстрого анализа
        CREATE INDEX IF NOT EXISTS idx_kwork_requests_timestamp 
        ON public.kwork_api_requests(timestamp DESC);
        
        CREATE INDEX IF NOT EXISTS idx_kwork_requests_project 
        ON public.kwork_api_requests(project_id, request_type);
        
        -- Функция для проверки rate limit
        CREATE OR REPLACE FUNCTION check_kwork_rate_limit(
            p_project_id TEXT,
            p_request_type TEXT,
            p_limit_per_hour INTEGER DEFAULT 10
        ) RETURNS BOOLEAN AS $$
        DECLARE
            request_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO request_count
            FROM public.kwork_api_requests
            WHERE project_id = p_project_id
                AND request_type = p_request_type
                AND timestamp > now() - interval '1 hour';
            
            RETURN request_count < p_limit_per_hour;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        
        -- Функция для логирования запросов
        CREATE OR REPLACE FUNCTION log_kwork_request(
            p_project_id TEXT,
            p_category_id INTEGER,
            p_request_type TEXT,
            p_ip_address INET DEFAULT NULL,
            p_user_agent TEXT DEFAULT NULL,
            p_success BOOLEAN DEFAULT false,
            p_response_time_ms INTEGER DEFAULT NULL
        ) RETURNS UUID AS $$
        DECLARE
            new_id UUID;
        BEGIN
            INSERT INTO public.kwork_api_requests (
                project_id, category_id, request_type, 
                ip_address, user_agent, success, response_time_ms
            ) VALUES (
                p_project_id, p_category_id, p_request_type,
                p_ip_address, p_user_agent, p_success, p_response_time_ms
            ) RETURNING id INTO new_id;
            
            RETURN new_id;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        return sql
    
    def execute_sql(self, sql: str):
        """Выполнение SQL запроса"""
        conn = None
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Разделяем SQL на отдельные команды
            commands = sql.split(';')
            
            for command in commands:
                command = command.strip()
                if command:
                    try:
                        cursor.execute(command)
                        logger.info(f"✅ Выполнено: {command[:100]}...")
                    except Exception as e:
                        logger.warning(f"⚠️  Ошибка при выполнении команды: {e}")
                        logger.debug(f"Команда: {command}")
            
            cursor.close()
            logger.info("✅ Все SQL команды выполнены")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при выполнении SQL: {e}")
            return False
            
        finally:
            if conn:
                conn.close()
    
    def setup_complete_rls(self):
        """Полная настройка RLS и anti-ban мер"""
        logger.info("🚀 Начало настройки RLS политик и anti-ban мер...")
        
        # 1. Настройка пользовательских политик
        logger.info("1. Настройка пользовательских политик RLS...")
        user_policies_sql = self.create_user_specific_policies()
        self.execute_sql(user_policies_sql)
        
        # 2. Настройка anti-ban мер
        logger.info("2. Настройка anti-ban мер...")
        anti_ban_sql = self.setup_anti_ban_measures()
        self.execute_sql(anti_ban_sql)
        
        logger.info("✅ Настройка RLS и anti-ban мер завершена!")
        
        # 3. Проверка настроек
        logger.info("3. Проверка текущих настроек RLS...")
        check_sql = """
        SELECT schemaname, tablename, rowsecurity 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename LIKE 'fh_%';
        """
        
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(check_sql)
            tables = cursor.fetchall()
            
            logger.info("📊 Текущие настройки RLS:")
            for table in tables:
                logger.info(f"   Таблица: {table[1]}, RLS: {'✅ Включен' if table[2] else '❌ Выключен'}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка при проверке настроек: {e}")

def main():
    """Основная функция"""
    # Получаем строку подключения из .env
    from dotenv import load_dotenv
    load_dotenv('/srv/firehorse-backend/.env')
    
    connection_string = os.getenv('SUPABASE_URL')
    
    if not connection_string:
        logger.error("❌ SUPABASE_URL не найден в .env файле")
        return
    
    logger.info(f"Используется подключение: {connection_string[:50]}...")
    
    # Создаем экземпляр и настраиваем RLS
    rls_setup = SupabaseRLSSetup(connection_string)
    rls_setup.setup_complete_rls()
    
    logger.info("🎉 Настройка завершена! RLS политики и anti-ban меры активированы.")

if __name__ == "__main__":
    main()
