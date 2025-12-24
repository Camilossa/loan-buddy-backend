# Historias de usuario (Loan Buddy Backend)

## Préstamos (Loan)
1) Como gestor, quiero crear un préstamo registrando deudor, monto, tasa, cuotas y fechas, para comenzar a cobrarlo.
   - Criterios: campos requeridos; cuota mensual calculada; estado inicial `active`; saldo = principal.
2) Como gestor, quiero consultar el listado de préstamos, para ver estado, saldo y próximo pago.
   - Criterios: paginación futura; filtros por estado/búsqueda; orden por próximo pago.
3) Como gestor, quiero ver el detalle de un préstamo, para revisar cronograma y pagos asociados.
   - Criterios: muestra datos completos y lista de pagos ordenados desc.
4) Como gestor, quiero actualizar datos del préstamo (tasa, fechas, contacto), para reflejar cambios de contrato.
   - Criterios: recalcula cuota si cambian monto/tasa/cuotas; actualiza `updatedAt`.
5) Como gestor, quiero eliminar un préstamo, para depurar registros demo.
   - Criterios: borra pagos asociados; 404 si no existe; confirma con 204.

## Pagos (Payment)
6) Como gestor, quiero registrar un pago sobre un préstamo, para reducir el saldo y llevar control de cuotas.
   - Criterios: calcula interés del periodo y capital; incrementa `paidInstallments`; ajusta `remainingBalance`; cambia estado a `paid` si saldo = 0; avanza `nextPaymentDate` si sigue activo.
7) Como gestor, quiero listar pagos (global o por préstamo), para auditar recaudación.
   - Criterios: orden descendente por fecha; parámetro `limit` para recientes; 404 si el préstamo no existe cuando se consultan pagos de un préstamo.

## Métricas / Dashboard
8) Como gestor, quiero ver un resumen (totalLoans, activeLoans, totalLent, totalReceived, pendingAmount, overdueLoans, upcomingPayments), para monitorear salud de la cartera.
   - Criterios: computado a partir de préstamos/pagos; sólo pagos `completed` cuentan para received.
9) Como gestor, quiero ver próximos pagos (<= 7 días), para priorizar cobro.
   - Criterios: solo préstamos no pagados; orden por días restantes.
10) Como gestor, quiero ver préstamos vencidos, para gestionar mora.
    - Criterios: estado `overdue` cuando `nextPaymentDate` < hoy y no está pagado.

## Salud del servicio
11) Como desarrollador/ops, quiero un healthcheck simple, para monitorear disponibilidad.
    - Criterios: responde 200 con `{status:"ok"}`.
