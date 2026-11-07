"""Compatibilidade para imports antigos das views de tickets.

Os controles comerciais ficam em ``views.botoes.TicketButtons`` e os controles
específicos de suporte ficam em ``views.botoes.SupportTicketButtons``.
"""

from views.botoes import SupportTicketButtons, TicketButtons

__all__ = ["TicketButtons", "SupportTicketButtons"]
