# Constitución — Dulce Arte

Principios innegociables. Toda spec, plan y tarea debe cumplirlos.

1. **Stack único**: Django 5.2 + DRF + PostgreSQL. Frontend con templates y JS nativo, sin frameworks ni bundler.
2. **La spec manda**: nada se implementa si no está en la spec activa. Si falta una decisión, se detiene y se pregunta.
3. **Modelo en 3FN**: sin datos repetidos entre tablas; las relaciones muchos-a-muchos viven en tablas intermedias.
4. **Lógica en el modelo**: las reglas de negocio (Kanban, BOM, despacho) se implementan una vez en `models.py` y las vistas solo orquestan.
5. **Integridad de datos**: el stock se descuenta una sola vez y de forma atómica; ninguna entrega se confirma sin firma o comprobante.
6. **Idioma y evidencia**: código en inglés técnico estándar, interfaz y documentación en español; todo apoyo de IA queda registrado en `prompts_ia.md`.
7. **API administrativa**: la API REST es una integración exclusiva del rol administrador. El personal operativo y los clientes usan las páginas HTML; ninguna pantalla interna depende de `fetch` a `/api/`.
8. **Agenda y entrega reales**: todo pedido respeta horario, cupo diario y anticipación; producción no arranca sin pago confirmado y ninguna entrega se cierra sin evidencia o sin quién retira.
