"""Limites que ficam em volta do modelo: o canário e o teto de mensagens por visitante."""

import time
from collections import defaultdict, deque

MAX_MESSAGE_LENGTH = 2000


class CanaryGuard:
    """Filtra o texto que sai em pedaços.

    Segura o fim de cada pedaço, para o canário nunca sair cortado ao meio.
    """

    def __init__(self, canary):
        self.canary = canary
        self.leaked = False
        self.held = ""

    def filter(self, piece):
        if self.leaked:
            return ""
        text = self.held + piece
        if self.canary in text:
            self.leaked = True
            self.held = ""
            return ""
        keep = len(self.canary) - 1  # o suficiente para guardar um canário pela metade
        if len(text) <= keep:
            self.held = text
            return ""
        self.held = text[-keep:]
        return text[:-keep]

    def finish(self):
        rest, self.held = self.held, ""
        return "" if self.leaked else rest


class RateLimit:
    """Cada mensagem custa dinheiro na API: sem teto, um robô esvazia o seu saldo."""

    def __init__(self, max_messages, window_seconds, clock=time.monotonic):
        self.max_messages = max_messages
        self.window = window_seconds
        self.clock = clock
        self.recent = defaultdict(deque)

    def allow(self, visitor):
        now = self.clock()
        recent = self.recent[visitor]
        while recent and now - recent[0] > self.window:
            recent.popleft()
        if len(recent) >= self.max_messages:
            return False
        recent.append(now)
        return True
