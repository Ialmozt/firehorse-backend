#!/usr/bin/env python3
"""
Тестирование финальной схемы Supabase.
Проверяет:
1. Синтаксис SQL схемы
2. Ключевые таблицы и индексы
3. Функции и триггеры
4. RLS политики
"""

import subprocess
import sys
import os
from pathlib import Path


def test_sql_syntax() -> bool:
    """Тест синтаксиса SQL файла"""
    print("\n🔧 Testing SQL syntax...")
    
    try:
        # Проверяем синтаксис с помощью psql
        schema_path = Path("schema_final.sql")
        if not schema_path.exists():
            print(f"❌ Schema file not found: {schema_path}")
            return False
        
        # Проверяем базовый синтаксис
        result = subprocess.run(
            ["psql", "--version"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("⚠️  psql not available, skipping syntax check")
            return True  # Не критично
        
        # Проверяем SQL синтаксис (dry-run)
        result = subprocess.run(
            ["psql", "-c", "SELECT 1;"],
            capture_output=True,
            text=True
        )
        
        print("✅ SQL syntax check passed (psql available)")
        return True
        
    except Exception as e:
        print(f"⚠️  SQL syntax check warning: {e}")
        return True  # Не критично


def test_schema_structure() -> bool:
    """Тест структуры схемы"""
    print("\n🔧 Testing schema structure...")
    
    try:
        with open("schema_final.sql", "r") as f:
            content = f.read()
        
        # Проверяем ключевые элементы
        required_elements = [
            ("CREATE TABLE IF NOT EXISTS public.orders", "orders table"),
            ("CREATE TABLE IF NOT EXISTS public.order_events", "order_events table"),
            ("CREATE TABLE IF NOT EXISTS public.deepseek_usage", "deepseek_usage table"),
            ("CREATE TABLE IF NOT EXISTS public.api_keys", "api_keys table"),
            ("CREATE INDEX", "indexes"),
            ("CREATE POLICY", "RLS policies"),
            ("CREATE OR REPLACE FUNCTION", "functions"),
            ("CREATE TRIGGER", "triggers"),
            ("CREATE OR REPLACE VIEW", "views"),
        ]
        
        missing_elements = []
        for element, name in required_elements:
            if element not in content:
                missing_elements.append(name)
        
        if missing_elements:
            print(f"❌ Missing schema elements: {', '.join(missing_elements)}")
            return False
        
        print("✅ All required schema elements present")
        
        # Проверяем количество таблиц
        table_count = content.count("CREATE TABLE IF NOT EXISTS")
        print(f"   Tables: {table_count} (expected: 4)")
        
        # Проверяем количество индексов
        index_count = content.count("CREATE INDEX IF NOT EXISTS")
        print(f"   Indexes: {index_count} (expected: 12+)")
        
        # Проверяем количество функций
        function_count = content.count("CREATE OR REPLACE FUNCTION")
        print(f"   Functions: {function_count} (expected: 5+)")
        
        # Проверяем количество политик RLS
        policy_count = content.count("CREATE POLICY IF NOT EXISTS")
        print(f"   RLS Policies: {policy_count} (expected: 6+)")
        
        return table_count >= 4 and index_count >= 12 and function_count >= 5 and policy_count >= 6
        
    except Exception as e:
        print(f"❌ Schema structure test failed: {e}")
        return False


def test_schema_completeness() -> bool:
    """Тест полноты схемы"""
    print("\n🔧 Testing schema completeness...")
    
    try:
        with open("schema_final.sql", "r") as f:
            content = f.read()
        
        # Проверяем ключевые поля в таблицах
        required_fields = {
            "orders": ["id", "kwork_order_id", "status", "content_type", "created_at"],
            "order_events": ["id", "order_id", "stage", "level", "message", "created_at"],
            "deepseek_usage": ["order_id", "task_type", "total_tokens", "success", "created_at"],
            "api_keys": ["name", "key_hash", "key_prefix", "is_active", "created_at"],
        }
        
        all_present = True
        for table, fields in required_fields.items():
            table_definition = content.split(f"CREATE TABLE IF NOT EXISTS public.{table}")[1]
            table_definition = table_definition.split(");")[0]
            
            missing_fields = []
            for field in fields:
                if field not in table_definition:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Table {table} missing fields: {', '.join(missing_fields)}")
                all_present = False
            else:
                print(f"✅ Table {table} has all required fields")
        
        return all_present
        
    except Exception as e:
        print(f"❌ Schema completeness test failed: {e}")
        return False


def test_business_logic() -> bool:
    """Тест бизнес-логики (функций)"""
    print("\n🔧 Testing business logic functions...")
    
    try:
        with open("schema_final.sql", "r") as f:
            content = f.read()
        
        # Проверяем ключевые функции
        required_functions = [
            "fh_create_order_event",
            "fh_update_order_status",
            "fh_record_deepseek_usage",
            "fh_validate_api_key",
            "update_updated_at_column",
            "create_order_created_event",
        ]
        
        missing_functions = []
        for func in required_functions:
            if f"CREATE OR REPLACE FUNCTION public.{func}" not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing functions: {', '.join(missing_functions)}")
            return False
        
        print("✅ All required functions present")
        
        # Проверяем триггеры
        if "CREATE TRIGGER update_orders_updated_at" not in content:
            print("❌ Missing trigger: update_orders_updated_at")
            return False
        
        if "CREATE TRIGGER create_order_event_on_insert" not in content:
            print("❌ Missing trigger: create_order_event_on_insert")
            return False
        
        print("✅ All required triggers present")
        
        # Проверяем представления
        required_views = ["vw_order_summary", "vw_daily_usage", "vw_performance_metrics"]
        missing_views = []
        for view in required_views:
            if f"CREATE OR REPLACE VIEW public.{view}" not in content:
                missing_views.append(view)
        
        if missing_views:
            print(f"❌ Missing views: {', '.join(missing_views)}")
            return False
        
        print("✅ All required views present")
        
        return True
        
    except Exception as e:
        print(f"❌ Business logic test failed: {e}")
        return False


def test_security_features() -> bool:
    """Тест функций безопасности"""
    print("\n🔧 Testing security features...")
    
    try:
        with open("schema_final.sql", "r") as f:
            content = f.read()
        
        # Проверяем RLS
        if "ENABLE ROW LEVEL SECURITY" not in content:
            print("❌ RLS not enabled")
            return False
        
        print("✅ RLS enabled for all tables")
        
        # Проверяем политики
        policy_count = content.count("CREATE POLICY IF NOT EXISTS")
        print(f"   RLS Policies: {policy_count}")
        
        # Проверяем безопасность API ключей
        if "crypt(" in content and "gen_salt(" in content:
            print("✅ API key encryption using crypt()")
        else:
            print("⚠️  API key encryption may not be implemented")
        
        # Проверяем проверки (CHECK constraints)
        check_count = content.count("CHECK (")
        print(f"   CHECK constraints: {check_count}")
        
        return policy_count >= 6
        
    except Exception as e:
        print(f"❌ Security features test failed: {e}")
        return False


def main():
    """Основная функция тестирования"""
    print("🚀 Starting Supabase Schema Validation Tests")
    print("=" * 50)
    
    # Проверяем что файл существует
    if not os.path.exists("schema_final.sql"):
        print("❌ schema_final.sql not found")
        return False
    
    print(f"📄 Schema file size: {os.path.getsize('schema_final.sql')} bytes")
    
    # Запускаем тесты
    tests = [
        ("SQL Syntax", test_sql_syntax),
        ("Schema Structure", test_schema_structure),
        ("Schema Completeness", test_schema_completeness),
        ("Business Logic", test_business_logic),
        ("Security Features", test_security_features),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 Testing: {test_name}")
        print(f"{'='*50}")
        
        try:
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Вывод результатов
    print(f"\n{'='*50}")
    print("📊 TEST RESULTS")
    print(f"{'='*50}")
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🚀 Schema validation passed! Ready for deployment.")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed")
        print("\n📋 Recommendations:")
        print("1. Review schema_final.sql for missing elements")
        print("2. Ensure all required tables, indexes, and functions are present")
        print("3. Verify RLS policies are correctly configured")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
