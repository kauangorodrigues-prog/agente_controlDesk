from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from .logging_setup import get_logger

if TYPE_CHECKING:
    from .alerts import GestorAlertas


class CircuitBreaker:
    """Após N falhas consecutivas, abre o circuito por X minutos e alerta."""

    def __init__(self, max_falhas: int, pausa_min: int, nome: str) -> None:
        self.max_falhas = max_falhas
        self.pausa_min = pausa_min
        self.nome = nome
        self._falhas = 0
        self._aberto_ate: Optional[datetime] = None
        self._log = get_logger(f"cb.{nome}")

    @property
    def aberto(self) -> bool:
        if self._aberto_ate is None:
            return False
        if datetime.now() < self._aberto_ate:
            return True
        self._aberto_ate = None
        self._falhas = 0
        self._log.info(f"Circuito {self.nome} fechado (timeout expirado).")
        return False

    def registrar_sucesso(self) -> None:
        self._falhas = 0

    def registrar_falha(self, alertas: "Optional[GestorAlertas]" = None) -> None:
        self._falhas += 1
        self._log.warning(f"Falha {self._falhas}/{self.max_falhas} em {self.nome}")
        if self._falhas >= self.max_falhas:
            self._aberto_ate = datetime.now() + timedelta(minutes=self.pausa_min)
            msg = (
                f"⚡ CIRCUIT BREAKER — {self.nome}\n"
                f"{self._falhas} falhas consecutivas.\n"
                f"Retentativa em {self.pausa_min} min."
            )
            self._log.error(msg)
            if alertas:
                alertas.enviar_teams(msg, nivel="CRITICO", chave=f"circuit_breaker_{self.nome}", forcar=True)
