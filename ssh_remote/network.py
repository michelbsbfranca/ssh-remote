"""Verificação de conectividade usada para o indicador online/offline das sessões.

Testamos conexão TCP direta na porta SSH do host em vez de ICMP ping: muitos
switches/firewalls de rede bloqueiam ping mas aceitam conexões SSH normalmente,
o que fazia o indicador mostrar "offline" para hosts perfeitamente acessíveis.
"""
from __future__ import annotations

import socket

CONNECT_TIMEOUT_SECONDS = 2.5


def is_host_online(host: str, port: int = 22) -> bool:
    """Tenta abrir uma conexão TCP com host:port e retorna True se conectou."""
    if not host:
        return False

    try:
        with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SECONDS):
            return True
    except OSError:
        return False
