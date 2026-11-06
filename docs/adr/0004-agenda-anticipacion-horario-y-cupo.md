# La agenda se valida con anticipación, horario y cupo diario

Una pastelería artesanal no produce al instante, pero el sistema aceptaba cualquier fecha. La
decisión es que todo pedido respete un horario de atención (09:00–18:59 en
`America/Santiago`), un cupo de 6 pedidos no cancelados por día y, para la tienda web, 48 horas
de anticipación; el mostrador puede saltarse la anticipación pero no el horario ni el cupo. El
conteo del cupo usa un rango de fecha local en vez de `fecha_entrega__date`, porque esa
conversión aplica UTC y desplaza el día en Santiago. Se descartó calcular el cupo en el
template porque debía valerse igual en checkout, API y panel.
