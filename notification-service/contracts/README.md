# События TaskFlow v1

Публикуются как UTF-8 JSON в topic exchange `taskflow.events`. Routing key равен
`event_type`. Укажите UUID события и корреляции также в AMQP `message_id` и
`correlation_id`. При повторной публикации тело события остаётся тем же.

Обязательность и типы полей описаны в [JSON Schema](events-v1.schema.json).
Дополнительные ключи отклоняются. `occurred_at` должен иметь нулевой UTC offset.
Схема использует `format` для базовой проверки даты, UUID и email. Consumer
дополнительно проверяет UTC и совместимость email с правилами TaskFlow.

В `examples/` есть валидные образцы каждого типа и невалидные образцы для DLQ.
При изменении полей обновите схему через `python scripts/export_schema.py`.
