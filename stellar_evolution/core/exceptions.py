"""
Custom Exceptions for Stellar Evolution Engine & MESA Parser
============================================================
"""

class StellarEvolutionError(Exception):
    """Base exception for all stellar evolution errors."""
    pass


class MesaParseError(StellarEvolutionError):
    """Raised when parsing MESA ASCII data files fails."""
    pass


class MesaFormatError(MesaParseError):
    """Raised when MESA data structure or header format is malformed."""
    pass


class PhysicsConsistencyError(StellarEvolutionError):
    """Raised when physical consistency checks or conservation laws are violated."""
    pass


class ValidationError(StellarEvolutionError):
    """Raised when input model parameters or abundance vectors fail validation."""
    pass
