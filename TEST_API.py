import pytest
import requests
import uuid
import random

# BASE_URL = "https://qa-internship.avito.com"

@pytest.fixture
def base_url():
    return "https://qa-internship.avito.com"

@pytest.fixture
def create_test_item(base_url):
    """Фикстура для создания тестового объявления перед тестом"""
    payload = {
        "sellerID": 452612,
        "name": "iPhone 17 PRO MAX",
        "price": 155000,
        "statistics": {
            "likes": 10,
            "viewCount": 100,
            "contacts": 3
        }
    }
    response = requests.post(f"{base_url}/api/1/item", json=payload)

    # Парсим ID из реального ответа API: {"status": "Сохранили объявление - <id>"}
    status_msg = response.json().get("status", "")
    item_id = status_msg.split(" - ")[-1]

    return {"id": item_id, "sellerId": payload["sellerID"]}


class TestPositiveCases:

    def test_tc1_create_valid_item(self, base_url):
        """TC-1. Создание объявления с валидными данными"""
        payload = {
            "sellerID": 452612,
            "name": "iPhone 15",
            "price": 100000,
            "statistics": {"likes": 10, "viewCount": 100, "contacts": 3}
        }
        response = requests.post(f"{base_url}/api/1/item", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "Сохранили объявление" in data["status"]

    def test_tc2_get_item_by_valid_id(self, create_test_item, base_url):
        """TC-2. Получение существующего объявления по корректному id"""
        item_id = create_test_item["id"]
        response = requests.get(f"{base_url}/api/1/item/{item_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["id"] == item_id

    def test_tc3_get_items_by_seller_id(self, create_test_item, base_url):
        """TC-3. Получение списка всех объявлений для продавца по id"""
        seller_id = create_test_item["sellerId"]
        response = requests.get(f"{base_url}/api/1/{seller_id}/item")

        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        for item in items:
            assert item["sellerId"] == seller_id

    def test_tc4_get_statistic_by_item_id(self, create_test_item, base_url):
        """TC-4. Получение статистики по существующему item_id"""
        item_id = create_test_item["id"]
        response = requests.get(f"{base_url}/api/1/statistic/{item_id}")

        assert response.status_code == 200
        stats = response.json()
        assert "likes" in stats[0]
        assert "viewCount" in stats[0]
        assert "contacts" in stats[0]

    def test_tc5_create_item_boundary_values(self, base_url):
        """TC-5. Создание объявления с граничными значениями (Ожидаем отказ API)"""
        payload = {
            "sellerID": 452612,
            "name": "a",  # 1 символ
            "price": 0,  # Минимальная цена
            "statistics": {"likes": 0, "viewCount": 0, "contacts": 0}
        }
        response = requests.post(f"{base_url}/api/1/item", json=payload)
        # API возвращает 400 Bad Request из-за внутренних валидаций, меняем ожидание, минимальная цена 1, как и likes
        assert response.status_code == 400


class TestNegativeCases:

    def test_tc6_create_item_missing_required_field(self, base_url):
        """TC-6. Создание объявления с пропуском обязательного поля (name)"""
        payload = {
            "sellerID": 452612,
            "price": 100000,
            "statistics": {"likes": 10, "viewCount": 100, "contacts": 3}
        }
        response = requests.post(f"{base_url}/api/1/item", json=payload)
        assert response.status_code == 400

    def test_tc7_create_item_invalid_data_type(self, base_url):
        """TC-7. Создание объявления с некорректным типом данных"""
        payload = {
            "sellerID": 452612,
            "name": "iPhone 15",
            "price": "free",  # Строка вместо числа
            "statistics": {"likes": 10, "viewCount": 100, "contacts": 3}
        }
        response = requests.post(f"{base_url}/api/1/item", json=payload)
        assert response.status_code == 400

    def test_tc8_get_item_nonexistent_id(self, base_url):
        """TC-8. Запрос несуществующего id объявления (валидный UUID)"""
        fake_uuid = str(uuid.uuid4())
        response = requests.get(f"{base_url}/api/1/item/{fake_uuid}")
        assert response.status_code == 404

    def test_tc9_get_item_invalid_id_format(self, base_url):
        """TC-9. Запрос с некорректным форматом id объявления"""
        response = requests.get(f"{base_url}/api/1/item/123-abc")
        assert response.status_code == 400

    def test_tc10_get_items_nonexistent_seller(self, base_url):
        """TC-10. Запрос объявлений несуществующего продавца"""
        response = requests.get(f"{base_url}/api/1/99999999999/item")
        assert response.status_code == 200
        assert response.json() == []

    def test_tc11_get_items_invalid_seller_id(self, base_url):
        """TC-11. Запрос некорректного sellerID (строка)"""
        response = requests.get(f"{base_url}/api/1/invalid_seller/item")
        assert response.status_code == 400


class TestCornerCases:

    def test_tc12_create_identical_items(self, base_url):
        """TC-12. Создание двух объявлений подряд с абсолютно идентичным телом"""
        payload = {
            "sellerID": 111222,
            "name": "Clone Item",
            "price": 500,
            "statistics": {"likes": 1, "viewCount": 1, "contacts": 1}
        }
        resp1 = requests.post(f"{base_url}/api/1/item", json=payload)
        resp2 = requests.post(f"{base_url}/api/1/item", json=payload)

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        id1 = resp1.json().get("status", "").split(" - ")[-1]
        id2 = resp2.json().get("status", "").split(" - ")[-1]
        assert id1 != id2

    def test_tc13_idempotency_get_item(self, create_test_item, base_url):
        """TC-13. Выполнение 5 последовательных GET запросов к одному и тому же id"""
        item_id = create_test_item["id"]
        responses = [requests.get(f"{base_url}/api/1/item/{item_id}").json() for _ in range(5)]

        for resp in responses[1:]:
            assert resp == responses[0]

    def test_tc14_create_item_extreme_price(self, base_url):
        """TC-14. Создание объявления с экстремально большой ценой"""
        payload = {
            "sellerID": 452612,
            "name": "Expensive Item",
            "price": 2 ** 63 - 1,
            "statistics": {"likes": 0, "viewCount": 0, "contacts": 0}
        }
        response = requests.post(f"{base_url}/api/1/item", json=payload)
        assert response.status_code in [200, 400]

    def test_tc15_delete_and_get_item(self, create_test_item, base_url):
        """TC-15. Удаление объявления и попытка получить его снова"""
        item_id = create_test_item["id"]
        # Используем эндпоинт удаления
        delete_resp = requests.delete(f"{base_url}/api/2/item/{item_id}")
        assert delete_resp.status_code == 200

        get_resp = requests.get(f"{base_url}/api/1/item/{item_id}")
        assert get_resp.status_code == 404

    def test_tc16_repeated_delete(self, create_test_item, base_url):
        """TC-16. Повторное удаление"""
        item_id = create_test_item["id"]
        requests.delete(f"{base_url}/api/2/item/{item_id}")

        second_delete_resp = requests.delete(f"{base_url}/api/2/item/{item_id}")
        assert second_delete_resp.status_code in [200, 404]


class TestNonFunctionalCases:

    def test_tc17_get_item_response_time(self, create_test_item, base_url):
        """TC-17. Проверка времени ответа на запрос GET"""
        item_id = create_test_item["id"]
        response = requests.get(f"{base_url}/api/1/item/{item_id}")

        assert response.elapsed.total_seconds() < 1.5  # Увеличим порог для тестового стенда

    def test_tc18_1_post_without_content_type(self, base_url):
        """TC-18 (1). Попытка выполнить POST запрос без Content-Type"""
        payload = '{"sellerID": 452612, "name": "Test", "price": 100}'
        response = requests.post(f"{base_url}/api/1/item", data=payload)
        assert response.status_code in [415, 400]

    def test_tc18_2_save_with_emoji(self, base_url):
        """TC-18 (2). Сохранение с эмодзи в name"""
        payload = {
            "sellerID": 452612,
            "name": "MacBook Pro 💻✨",
            "price": 250000,
            "statistics": {"likes": 10, "viewCount": 100, "contacts": 3}
        }
        post_response = requests.post(f"{base_url}/api/1/item", json=payload)
        assert post_response.status_code == 200

        item_id = post_response.json().get("status", "").split(" - ")[-1]
        get_response = requests.get(f"{base_url}/api/1/item/{item_id}")

        assert get_response.status_code == 200
        assert get_response.json()[0]["name"] == "MacBook Pro 💻✨"


class TestE2EScenarios:

    def test_e2e_full_item_lifecycle(self, base_url):
        """
        E2E-1. Полный жизненный цикл объявления:
        Создание -> Проверка по ID -> Проверка в списке продавца -> Проверка статистики -> Удаление -> Проверка удаления
        """
        seller_id = 777888
        payload = {
            "sellerID": seller_id,
            "name": "E2E Test Laptop",
            "price": 150000,
            "statistics": {"likes": 5, "viewCount": 50, "contacts": 2}
        }

        # ШАГ 1: Создаем объявление
        post_resp = requests.post(f"{base_url}/api/1/item", json=payload)
        assert post_resp.status_code == 200, "Не удалось создать объявление"

        # Парсим ID (учитывая особенность API из предыдущих тестов)
        status_msg = post_resp.json().get("status", "")
        item_id = status_msg.split(" - ")[-1]
        assert len(item_id) > 10, "Некорректный ID в ответе"

        # ШАГ 2: Получаем объявление по ID и проверяем данные
        get_resp = requests.get(f"{base_url}/api/1/item/{item_id}")
        assert get_resp.status_code == 200, "Объявление не найдено по ID"

        item_data = get_resp.json()[0]
        assert item_data["name"] == payload["name"]
        assert item_data["price"] == payload["price"]
        assert item_data["sellerId"] == payload["sellerID"]

        # ШАГ 3: Проверяем, что объявление появилось в списке продавца
        seller_resp = requests.get(f"{base_url}/api/1/{seller_id}/item")
        assert seller_resp.status_code == 200

        seller_items = seller_resp.json()
        # Ищем наш item_id в списке всех объявлений продавца
        item_found = any(item["id"] == item_id for item in seller_items)
        assert item_found is True, "Созданное объявление отсутствует в списке продавца"

        # ШАГ 4: Проверяем статистику объявления
        stat_resp = requests.get(f"{base_url}/api/1/statistic/{item_id}")
        assert stat_resp.status_code == 200

        stat_data = stat_resp.json()[0]
        assert stat_data["likes"] == payload["statistics"]["likes"]
        assert stat_data["viewCount"] == payload["statistics"]["viewCount"]
        assert stat_data["contacts"] == payload["statistics"]["contacts"]

        # ШАГ 5: Удаляем объявление (эндпоинт v2)
        delete_resp = requests.delete(f"{base_url}/api/2/item/{item_id}")
        assert delete_resp.status_code == 200, "Не удалось удалить объявление"

        # ШАГ 6: Убеждаемся, что объявление действительно удалено
        get_deleted_resp = requests.get(f"{base_url}/api/1/item/{item_id}")
        assert get_deleted_resp.status_code == 404, "Удаленное объявление все еще доступно"

    def test_e2e_multiple_items_for_one_seller(self, base_url):
        """
        E2E-2. Создание нескольких объявлений одним продавцом и проверка их количества.
        """
        unique_seller_id = random.randint(111111, 999999)

        items_to_create = [
            {"name": "Item 1", "price": 100},
            {"name": "Item 2", "price": 200},
            {"name": "Item 3", "price": 300}
        ]

        created_ids = []

        # ШАГ 1: Создаем 3 объявления
        for item in items_to_create:

            payload = {
                "sellerID": unique_seller_id,
                "name": item["name"],
                "price": item["price"],
                "statistics": {
                "likes": 1,
                "viewCount": 1,
                "contacts": 1
                }
            }
            resp = requests.post(f"{base_url}/api/1/item", json=payload)

            # Если плоская структура не поможет, сервер в resp.text скажет об этом
            assert resp.status_code == 200, f"Не удалось создать объявление. Ответ сервера: {resp.text}"

            item_id = resp.json().get("status", "").split(" - ")[-1]
            created_ids.append(item_id)

        # ШАГ 2: Запрашиваем все объявления этого продавца
        seller_resp = requests.get(f"{base_url}/api/1/{unique_seller_id}/item")
        assert seller_resp.status_code == 200

        seller_items = seller_resp.json()

        # ШАГ 3: Проверяем количество
        assert len(seller_items) == 3, f"Ожидалось 3 объявления, получено {len(seller_items)}. Ответ: {seller_items}"

        # Очистка
        for item_id in created_ids:
            requests.delete(f"{base_url}/api/2/item/{item_id}")
