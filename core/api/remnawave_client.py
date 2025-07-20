import os
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from remnawave_api import RemnawaveSDK
from remnawave_api.models import (
    TelegramUserResponseDto,
    UpdateUserRequestDto,
    UserResponseDto,
    UserActiveInboundsDto,
    UserLastConnectedNodeDto,
    HWIDUserResponseDtoList,
    HWIDDeleteRequest,
    HWIDUserResponseDto
)
from remnawave_api.exceptions import (
    ApiError,
    NotFoundError,
    BadRequestError,
    ForbiddenError,
    UnauthorizedError,
    ConflictError,
    ServerError
)
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class RemnawaveService:
    def __init__(self, base_url: str, token: str):
        """
        Инициализация клиента Remnawave API
        :param base_url: Базовый URL API
        :param token: Токен авторизации
        """
        self.client = RemnawaveSDK(base_url=base_url, token=token)
    
    async def _transform_user_response(self, user: UserResponseDto) -> Dict[str, Any]:
        """Преобразование объекта UserResponseDto в словарь"""
        # Вспомогательная функция для безопасного форматирования даты
        def format_date(date_field):
            if date_field:
                try:
                    return date_field.strftime("%Y-%m-%d %H:%M:%S")
                except AttributeError:
                    return str(date_field)
            return "N/A"
        
        # Вспомогательная функция для безопасного извлечения значений
        def get_value(field):
            if field is None:
                return None
            try:
                return field.value
            except AttributeError:
                return field
        
        # Обрабатываем статус
        status = get_value(user.status) if user.status else "unknown"
        
        # Обрабатываем last_connected_node
        last_connected_node = "N/A"
        if user.last_connected_node:
            try:
                # Пробуем разные варианты имен атрибутов
                if hasattr(user.last_connected_node, 'node_name'):
                    last_connected_node = user.last_connected_node.node_name
                elif hasattr(user.last_connected_node, 'nodeName'):
                    last_connected_node = user.last_connected_node.nodeName
                else:
                    last_connected_node = str(user.last_connected_node)
            except Exception:
                last_connected_node = str(user.last_connected_node)
        
        # Обрабатываем активные инбаунды
        inbounds = ["N/A"]
        if user.active_user_inbounds:
            try:
                inbounds = []
                for inbound in user.active_user_inbounds:
                    # Пробуем разные варианты имен атрибутов
                    tag = inbound.tag if hasattr(inbound, 'tag') else (
                        inbound.nodeName if hasattr(inbound, 'nodeName') else "Unknown"
                    )
                    type_ = inbound.type if hasattr(inbound, 'type') else (
                        inbound.nodeType if hasattr(inbound, 'nodeType') else "Unknown"
                    )
                    inbounds.append(f"{tag} ({type_})")
            except Exception:
                inbounds = [str(inbound) for inbound in user.active_user_inbounds]
        
        # Обрабатываем happ.crypto_link
        happ_crypto_link = "N/A"
        if user.happ:
            try:
                # Пробуем разные варианты имен атрибутов
                if hasattr(user.happ, 'crypto_link'):
                    happ_crypto_link = user.happ.crypto_link
                elif hasattr(user.happ, 'cryptoLink'):
                    happ_crypto_link = user.happ.cryptoLink
                else:
                    happ_crypto_link = str(user.happ)
            except Exception:
                pass
        
        # Логируем атрибуты объекта для отладки
        logger.debug(f"Атрибуты объекта UserResponseDto: {vars(user)}")
        
        # Формируем результат строго по модели с учетом обязательности полей
        return {
            # Обязательные поля (без Optional)
            "uuid": str(user.uuid),
            "subscription_uuid": str(user.subscription_uuid),
            "short_uuid": user.short_uuid,
            "username": user.username,
            "used_traffic_bytes": user.used_traffic_bytes,
            "lifetime_used_traffic_bytes": user.lifetime_used_traffic_bytes,
            "trojan_password": user.trojan_password,
            "vless_uuid": str(user.vless_uuid),
            "ss_password": user.ss_password,
            "subscription_url": user.subscription_url,
            "created_at": format_date(user.created_at),
            "updated_at": format_date(user.updated_at),
            
            # Опциональные поля (с Optional в модели)
            "status": status,
            "data_limit": user.traffic_limit_bytes / (1024 ** 3) if user.traffic_limit_bytes else 0,
            "traffic_limit_strategy": get_value(user.traffic_limit_strategy) if user.traffic_limit_strategy else "N/A",
            "expire": format_date(user.expire_at) if user.expire_at else "N/A",
            "last_connected_node": last_connected_node,
            "sub_last_opened_at": format_date(user.sub_last_opened_at) if user.sub_last_opened_at else "N/A",
            "inbounds": inbounds,
            "sub_last_user_agent": user.sub_last_user_agent or "N/A",
            "online_at": format_date(user.online_at) if user.online_at else "N/A",
            "sub_revoked_at": format_date(user.sub_revoked_at) if user.sub_revoked_at else "N/A",
            "last_traffic_reset_at": format_date(user.last_traffic_reset_at) if user.last_traffic_reset_at else "N/A",
            "description": user.description or "N/A",
            "telegram_id": user.telegram_id or "N/A",
            "email": user.email or "N/A",
            "hwid_device_limit": user.hwidDeviceLimit or "N/A",
            "last_triggered_threshold": getattr(user, 'last_triggered_threshold', 0),
            "happ_crypto_link": happ_crypto_link,
            "first_connected_at": format_date(getattr(user, 'first_connected', None)) if getattr(user, 'first_connected', None) else "N/A"
        }
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> List[Dict[str, Any]]:
        """
        Получение информации о подписках пользователя по Telegram ID
        :param telegram_id: Идентификатор пользователя в Telegram
        :return: Список подписок или список с ошибкой
        """
        try:
            if not telegram_id:
                logger.error("Пустой Telegram ID")
                return [{"error": "Не указан Telegram ID"}]

            logger.debug(f"Запрос подписок для Telegram ID {telegram_id}")
            
            # Делаем запрос к API
            response: TelegramUserResponseDto = await self.client.users.get_users_by_telegram_id(str(telegram_id))
            
            if not response.response:
                logger.info(f"Подписки для Telegram ID {telegram_id} не найдены")
                return []

            # Преобразуем ответ API
            subscriptions = [await self._transform_user_response(user) for user in response.response]
            
            logger.info(f"Успешно получено {len(subscriptions)} подписок для {telegram_id}")
            return subscriptions

        except NotFoundError:
            logger.warning(f"Пользователь {telegram_id} не найден")
            return [{"error": "Пользователь не найден"}]
        except BadRequestError as e:
            logger.error(f"Ошибка запроса для {telegram_id}: {str(e)}")
            return [{"error": "Некорректный запрос"}]
        except ForbiddenError:
            logger.error(f"Доступ запрещен для {telegram_id}")
            return [{"error": "Доступ запрещен"}]
        except UnauthorizedError:
            logger.error("Невалидный API токен")
            return [{"error": "Ошибка авторизации API"}]
        except ServerError as e:
            logger.error(f"Ошибка сервера: {str(e)}")
            return [{"error": "Внутренняя ошибка сервера"}]
        except ApiError as e:
            logger.error(f"Ошибка API: {str(e)}")
            return [{"error": f"Ошибка API: {str(e)}"}]
        except Exception as e:
            logger.critical(f"Неизвестная ошибка: {str(e)}", exc_info=True)
            return [{"error": "Неизвестная ошибка"}]

    async def get_subscription_by_uuid(self, subscription_uuid: str) -> Dict[str, Any]:
        """
        Получение информации о подписке по UUID
        :param subscription_uuid: UUID подписки
        :return: Словарь с данными подписки или ошибкой
        """
        try:
            if not subscription_uuid:
                logger.error("Пустой UUID подписки")
                return {"error": "Не указан UUID подписки"}

            logger.debug(f"Запрос подписки по UUID: {subscription_uuid}")
            
            # Делаем запрос к API
            response: UserResponseDto = await self.client.users.get_user_by_uuid(subscription_uuid)
            
            # Преобразуем ответ API
            subscription = await self._transform_user_response(response)
            
            logger.info(f"Успешно получена подписка {subscription_uuid}")
            return subscription

        except NotFoundError:
            logger.warning(f"Подписка {subscription_uuid} не найдена")
            return {"error": "Подписка не найдена"}
        except BadRequestError as e:
            logger.error(f"Ошибка запроса для UUID {subscription_uuid}: {str(e)}")
            return {"error": "Некорректный запрос"}
        except ForbiddenError:
            logger.error(f"Доступ запрещен для UUID {subscription_uuid}")
            return {"error": "Доступ запрещен"}
        except UnauthorizedError:
            logger.error("Невалидный API токен")
            return {"error": "Ошибка авторизации API"}
        except ServerError as e:
            logger.error(f"Ошибка сервера: {str(e)}")
            return {"error": "Внутренняя ошибка сервера"}
        except ApiError as e:
            logger.error(f"Ошибка API: {str(e)}")
            return {"error": f"Ошибка API: {str(e)}"}
        except Exception as e:
            logger.critical(f"Неизвестная ошибка: {str(e)}", exc_info=True)
            return {"error": "Неизвестная ошибка"}

    async def update_user(self, user_uuid: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновление данных пользователя по UUID
        :param user_uuid: UUID пользователя
        :param update_data: Словарь с данными для обновления
        :return: Обновленные данные пользователя или словарь с ошибкой
        """
        try:
            if not user_uuid:
                logger.error("Пустой UUID пользователя")
                return {"error": "Не указан UUID пользователя"}

            if not update_data:
                logger.error("Пустые данные для обновления")
                return {"error": "Не указаны данные для обновления"}

            logger.debug(f"Обновление пользователя с UUID {user_uuid}: {update_data}")

            # Формируем DTO для запроса на обновление
            update_request = UpdateUserRequestDto(
                uuid=user_uuid,
                **update_data
            )

            # Делаем запрос к API
            response: UserResponseDto = await self.client.users.update_user(user_uuid, update_request)

            # Преобразуем ответ API
            updated_user = await self._transform_user_response(response)
            
            logger.info(f"Успешно обновлен пользователь с UUID {user_uuid}")
            return updated_user

        except NotFoundError:
            logger.warning(f"Пользователь с UUID {user_uuid} не найден")
            return {"error": "Пользователь не найден"}
        except BadRequestError as e:
            logger.error(f"Ошибка запроса для UUID {user_uuid}: {str(e)}")
            return {"error": "Некорректный запрос"}
        except ForbiddenError:
            logger.error(f"Доступ запрещен для UUID {user_uuid}")
            return {"error": "Доступ запрещен"}
        except UnauthorizedError:
            logger.error("Невалидный API токен")
            return {"error": "Ошибка авторизации API"}
        except ConflictError:
            logger.error(f"Конфликт при обновлении пользователя с UUID {user_uuid}")
            return {"error": "Конфликт данных"}
        except ServerError as e:
            logger.error(f"Ошибка сервера: {str(e)}")
            return {"error": "Внутренняя ошибка сервера"}
        except ApiError as e:
            logger.error(f"Ошибка API: {str(e)}")
            return {"error": f"Ошибка API: {str(e)}"}
        except Exception as e:
            logger.critical(f"Неизвестная ошибка: {str(e)}", exc_info=True)
            return {"error": "Неизвестная ошибка"}

    async def update_user_by_telegram_id(self, telegram_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновление данных пользователя по Telegram ID
        :param telegram_id: Идентификатор пользователя в Telegram
        :param update_data: Словарь с данными для обновления
        :return: Обновленные данные пользователя или словарь с ошибкой
        """
        try:
            # Шаг 1: Получаем UUID по Telegram ID
            subscriptions = await self.get_user_by_telegram_id(telegram_id)
            
            # Проверяем, есть ли подписки
            if not subscriptions or "error" in subscriptions[0]:
                error_msg = subscriptions[0].get("error", "Пользователь или подписки не найдены")
                logger.warning(f"Подписки для Telegram ID {telegram_id} не найдены: {error_msg}")
                return {"error": error_msg}

            # Берем UUID первой подписки
            user_uuid = subscriptions[0]["uuid"]
            logger.debug(f"Найден UUID {user_uuid} для Telegram ID {telegram_id}")

            # Шаг 2: Обновляем данные пользователя
            result = await self.update_user(user_uuid, update_data)
            return result

        except Exception as e:
            logger.critical(f"Неизвестная ошибка при обновлении по Telegram ID {telegram_id}: {str(e)}", exc_info=True)
            return {"error": "Неизвестная ошибка"}

    async def get_connected_devices(self, user_uuid: str) -> List[Dict]:
        """
        Получение списка подключённых устройств для подписки.
        
        Args:
            user_uuid: UUID подписки.
        
        Returns:
            List[Dict]: Список устройств или пустой список при ошибке.
        """
        try:
            logger.debug(f"Запрос устройств для подписки {user_uuid}")
            response: HWIDUserResponseDtoList = await self.client.hwid.get_hwid_user(user_uuid)
            devices = [
                {
                    "hwid": device.hwid,
                    "user_uuid": str(device.user_uuid),
                    "platform": device.platform,
                    "os_version": device.os_version,
                    "device_model": device.device_model,
                    "user_agent": device.user_agent,
                    "created_at": device.created_at,
                    "updated_at": device.updated_at
                }
                for device in response.devices
            ]
            logger.debug(f"Получено {len(devices)} устройств для подписки {user_uuid}")
            return devices
        except NotFoundError:
            logger.warning(f"Устройства для подписки {user_uuid} не найдены")
            return []
        except BadRequestError as e:
            logger.error(f"Ошибка запроса для {user_uuid}: {str(e)}")
            return []
        except ForbiddenError:
            logger.error(f"Доступ запрещен для {user_uuid}")
            return []
        except UnauthorizedError:
            logger.error("Невалидный API токен")
            return []
        except ServerError as e:
            logger.error(f"Ошибка сервера: {str(e)}")
            return []
        except ApiError as e:
            logger.error(f"Ошибка API: {str(e)}")
            return []
        except Exception as e:
            logger.critical(f"Неизвестная ошибка при получении устройств для {user_uuid}: {str(e)}", exc_info=True)
            return []

    async def remove_device(self, user_uuid: str, hwid: str) -> bool:
        """
        Удаление устройства из подписки.
        
        Args:
            user_uuid: UUID подписки.
            hwid: Идентификатор устройства (HWID).
        
        Returns:
            bool: True при успешном удалении, False при ошибке.
        """
        try:
            logger.debug(f"Удаление устройства {hwid} для подписки {user_uuid}")
            body = HWIDDeleteRequest(hwid=hwid, userUuid=UUID(user_uuid))
            response: HWIDUserResponseDtoList = await self.client.hwid.delete_hwid_to_user(body)
            logger.info(f"Устройство {hwid} удалено для подписки {user_uuid}")
            return True
        except NotFoundError:
            logger.warning(f"Устройство {hwid} для подписки {user_uuid} не найдено")
            return False
        except BadRequestError as e:
            logger.error(f"Ошибка запроса для удаления устройства {hwid}: {str(e)}")
            return False
        except ForbiddenError:
            logger.error(f"Доступ запрещен для удаления устройства {hwid}")
            return False
        except UnauthorizedError:
            logger.error("Невалидный API токен")
            return False
        except ServerError as e:
            logger.error(f"Ошибка сервера: {str(e)}")
            return False
        except ApiError as e:
            logger.error(f"Ошибка API: {str(e)}")
            return False
        except Exception as e:
            logger.critical(f"Неизвестная ошибка при удалении устройства {hwid} для {user_uuid}: {str(e)}", exc_info=True)
            return False

# Инициализация сервиса с параметрами из переменных окружения
remnawave_service = RemnawaveService(
    base_url=os.getenv("REMNAWAVE_BASE_URL", "https://api.remnawave.com"),
    token=os.getenv("REMNAWAVE_TOKEN", "your_api_token_here")
)
